"""
app/routes/github_auth.py
--------------------------
FastAPI router for GitHub OAuth authentication and account linking.

Endpoints:
    GET  /auth/github/login      → Redirects to GitHub OAuth consent screen (or returns authorize_url)
    GET  /auth/github/callback   → Handles OAuth redirect, validates state, saves encrypted token
    POST /auth/github/callback   → API endpoint for SPAs completing the OAuth exchange
    GET  /auth/github/status     → Checks if the authenticated user has an active GitHub connection
    POST /auth/github/disconnect → Revokes remote grant and deletes stored token
"""

import logging
import urllib.parse
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from pydantic import BaseModel

from app.auth import github_oauth
from app.auth.dependencies import get_current_user
from app.core.config import settings
from app.db import token_store

logger = logging.getLogger("uvicorn")

router = APIRouter(prefix="/auth/github", tags=["github-auth"])


@router.get("/login")
async def github_login(
    request: Request,
    redirect: bool = Query(
        default=True,
        description="Whether to return a 307 redirect directly to GitHub or a JSON payload with authorize_url",
    ),
    redirect_uri: Optional[str] = Query(
        default=None,
        description="Optional custom callback redirect URI for OAuth",
    ),
    return_to: Optional[str] = Query(
        default=None,
        description="Optional frontend destination URL to return to after authorization",
    ),
    token: Optional[str] = Query(
        default=None,
        description="Optional Clerk JWT passed as query param for direct browser navigation",
    ),
    current_user: dict = Depends(get_current_user),
):
    """
    Generate GitHub OAuth consent-screen URL with user-bound CSRF state.
    Requires authenticated Clerk user (provided via Bearer header or ?token= query param).
    """
    user_id = current_user["sub"]

    effective_redirect_uri = redirect_uri
    if not effective_redirect_uri:
        configured = getattr(settings, "GITHUB_OAUTH_REDIRECT_URI", None) or getattr(settings, "GITHUB_REDIRECT_URI", None)
        proto = request.headers.get("x-forwarded-proto", request.url.scheme)
        host = request.headers.get("x-forwarded-host") or request.url.netloc
        dynamic_cb = f"{proto}://{host}/auth/github/callback"

        def _is_invalid_or_placeholder(uri: Optional[str]) -> bool:
            if not uri:
                return True
            lower = uri.lower()
            return any(
                p in lower
                for p in ("your-backend", "localhost", "127.0.0.1", "example.com", "placeholder", "<", ">")
            )

        if configured and not _is_invalid_or_placeholder(configured):
            effective_redirect_uri = configured
        elif host and ("onrender.com" in host or "render" in host):
            effective_redirect_uri = dynamic_cb
        elif configured and "your-backend" not in configured.lower():
            effective_redirect_uri = configured
        elif host:
            effective_redirect_uri = dynamic_cb
        else:
            effective_redirect_uri = "https://study-guide-generator-1r0f.onrender.com/auth/github/callback"

        # Final safety check: never return a your-backend placeholder
        if effective_redirect_uri and "your-backend" in effective_redirect_uri.lower():
            effective_redirect_uri = "https://study-guide-generator-1r0f.onrender.com/auth/github/callback"

    authorize_url = github_oauth.generate_github_auth_url(
        user_id,
        redirect_uri=effective_redirect_uri,
        return_to=return_to,
    )

    if redirect:
        return RedirectResponse(
            url=authorize_url,
            status_code=status.HTTP_307_TEMPORARY_REDIRECT,
        )
    return {"authorize_url": authorize_url}


@router.get("/callback")
async def github_callback_get(
    code: Optional[str] = Query(default=None, description="Authorization code returned by GitHub"),
    state: Optional[str] = Query(default=None, description="Signed state token returned by GitHub"),
    error: Optional[str] = Query(default=None, description="Error code returned by GitHub"),
    error_description: Optional[str] = Query(default=None, description="Error description returned by GitHub"),
    request: Request = None,
):
    """
    Handle GitHub OAuth redirect callback in the browser.
    Validates state token, exchanges code for access token, encrypts token into MongoDB,
    and returns an interactive HTML confirmation that closes popups or redirects to frontend.
    Does NOT require get_current_user because the user is redirected directly by GitHub's servers.
    """
    frontend_base = (settings.FRONTEND_URL or "http://localhost:5173").rstrip("/")

    # 1. Handle user cancellation or GitHub errors
    if error or not code or not state:
        err_msg = error_description or error or "Missing authorization code or state parameter."
        logger.warning(f"[GitHubAuth] OAuth callback error: {err_msg}")
        target_error_url = f"{frontend_base}/settings?github=error&reason={urllib.parse.quote(err_msg)}"

        if request and "application/json" in request.headers.get("accept", ""):
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"connected": False, "error": err_msg},
            )

        err_html = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta http-equiv="refresh" content="2;url={target_error_url}">
            <title>GitHub Connection Failed</title>
            <style>
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
                    display: flex; align-items: center; justify-content: center;
                    height: 100vh; margin: 0; background-color: #0f172a; color: #f8fafc;
                }}
                .card {{
                    background: #1e293b; padding: 2.5rem; border-radius: 12px;
                    box-shadow: 0 10px 25px rgba(0,0,0,0.5); text-align: center;
                    max-width: 440px; border: 1px solid #ef4444;
                }}
                h2 {{ color: #f87171; margin-top: 0; }}
                p {{ color: #94a3b8; font-size: 15px; line-height: 1.5; }}
                a {{ color: #38bdf8; text-decoration: none; font-weight: 600; }}
            </style>
        </head>
        <body>
            <div class="card">
                <h2>Connection Incomplete</h2>
                <p>{err_msg}</p>
                <p>Redirecting back to your workspace...</p>
                <p><a href="{target_error_url}">Click here if not redirected automatically</a></p>
                <script>
                    if (window.opener) {{
                        window.opener.postMessage({{ type: 'GITHUB_AUTH_ERROR', error: '{err_msg}' }}, '*');
                        setTimeout(() => window.close(), 1500);
                    }} else {{
                        setTimeout(() => window.location.replace("{target_error_url}"), 1000);
                    }}
                </script>
            </div>
        </body>
        </html>
        """
        return HTMLResponse(content=err_html, status_code=status.HTTP_200_OK)

    # 2. Validate signed state (extracts user_id, return_to, and redirect_uri securely bound to state JWT)
    return_to = None
    state_redirect_uri = None
    try:
        payload = github_oauth.decode_state_payload(state)
        user_id = payload["sub"]
        return_to = payload.get("return_to")
        state_redirect_uri = payload.get("redirect_uri")
    except Exception as exc:
        logger.error(f"[GitHubAuth] Invalid state token: {exc}")
        target_error_url = f"{frontend_base}/settings?github=error&reason=Invalid+or+expired+state+token"
        return HTMLResponse(
            content=f"""
            <script>
                if (window.opener) {{
                    window.opener.postMessage({{ type: 'GITHUB_AUTH_ERROR', error: 'Invalid or expired state token' }}, '*');
                    window.close();
                }} else {{
                    window.location.replace("{target_error_url}");
                }}
            </script>
            """,
            status_code=status.HTTP_200_OK,
        )

    # 3. Exchange code for access token and scopes
    try:
        access_token, scopes = github_oauth.exchange_code_for_token(code, redirect_uri=state_redirect_uri)
        github_login = github_oauth.fetch_github_login(access_token)
    except Exception as exc:
        safe_msg = getattr(exc, "detail", "Token exchange failed")
        logger.error(f"[GitHubAuth] Token exchange failed: {safe_msg}")
        target_error_url = f"{frontend_base}/settings?github=error&reason={urllib.parse.quote(str(safe_msg))}"
        return HTMLResponse(
            content=f"""
            <script>
                if (window.opener) {{
                    window.opener.postMessage({{ type: 'GITHUB_AUTH_ERROR', error: '{safe_msg}' }}, '*');
                    window.close();
                }} else {{
                    window.location.replace("{target_error_url}");
                }}
            </script>
            """,
            status_code=status.HTTP_200_OK,
        )

    # 4. Encrypt and store token in MongoDB
    try:
        await token_store.save_user_token(
            user_id=user_id,
            token=access_token,
            github_login=github_login,
            scopes=scopes,
        )
        logger.info(f"[GitHubAuth] Stored encrypted GitHub token for {user_id} (@{github_login})")
    except Exception as exc:
        logger.error(f"[GitHubAuth] Failed to store encrypted token for user {user_id}: {exc}")
        target_error_url = f"{frontend_base}/settings?github=error&reason=Token+storage+failed"
        return HTMLResponse(
            content=f"""
            <script>
                if (window.opener) {{
                    window.opener.postMessage({{ type: 'GITHUB_AUTH_ERROR', error: 'Token storage failed' }}, '*');
                    window.close();
                }} else {{
                    window.location.replace("{target_error_url}");
                }}
            </script>
            """,
            status_code=status.HTTP_200_OK,
        )

    # If client accepts JSON or requests json format, return JSON
    if request and "application/json" in request.headers.get("accept", ""):
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "connected": True,
                "github_login": github_login,
                "user_id": user_id,
            },
        )

    if return_to:
        sep = "&" if "?" in return_to else "?"
        target_success_url = f"{return_to}{sep}github=connected&login={urllib.parse.quote(github_login)}"
    else:
        target_success_url = f"{frontend_base}/settings?github=connected&login={urllib.parse.quote(github_login)}"

    # Return clean success HTML confirmation
    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta http-equiv="refresh" content="2;url={target_success_url}">
        <title>GitHub Connected</title>
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
                display: flex;
                align-items: center;
                justify-content: center;
                height: 100vh;
                margin: 0;
                background-color: #0f172a;
                color: #f8fafc;
            }}
            .card {{
                background: #1e293b;
                padding: 2.5rem;
                border-radius: 12px;
                box-shadow: 0 10px 25px rgba(0,0,0,0.5);
                text-align: center;
                max-width: 420px;
                border: 1px solid #334155;
            }}
            h2 {{ color: #38bdf8; margin-top: 0; }}
            p {{ color: #94a3b8; font-size: 15px; line-height: 1.5; }}
            .badge {{
                display: inline-block;
                background: #0284c7;
                color: #ffffff;
                padding: 4px 12px;
                border-radius: 9999px;
                font-weight: bold;
                margin: 10px 0;
            }}
            a {{ color: #38bdf8; text-decoration: none; font-weight: 600; }}
        </style>
    </head>
    <body>
        <div class="card">
            <h2>Account Connected!</h2>
            <div class="badge">@{github_login}</div>
            <p>Your GitHub account has been successfully linked to your study workspace.</p>
            <p>Returning to your workspace...</p>
            <p><a href="{target_success_url}">Click here if not redirected automatically</a></p>
            <script>
                if (window.opener) {{
                    window.opener.postMessage({{ type: 'GITHUB_AUTH_SUCCESS', login: '{github_login}' }}, '*');
                    setTimeout(() => window.close(), 1200);
                }} else {{
                    setTimeout(() => window.location.replace("{target_success_url}"), 1000);
                }}
            </script>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content, status_code=status.HTTP_200_OK)


@router.get("/status")
async def github_status(current_user: dict = Depends(get_current_user)):
    """
    Check whether the authenticated user has an active, working GitHub connection.
    Verifies token validity on GitHub; if revoked, self-heals by purging the token.
    """
    user_id = current_user["sub"]
    github_login = await token_store.get_github_login(user_id)
    if not github_login:
        return {"connected": False, "github_login": None}

    access_token = await token_store.get_decrypted_token(user_id)
    is_active = github_oauth.is_token_active(access_token) if access_token else False

    if is_active is False:
        # Token is definitively dead or revoked — self-heal MongoDB record
        logger.warning(f"[GitHubAuth] Purging expired/revoked token for user {user_id}")
        await token_store.delete_token(user_id)
        return {"connected": False, "github_login": None}

    return {"connected": True, "github_login": github_login}


@router.post("/disconnect")
async def github_disconnect(current_user: dict = Depends(get_current_user)):
    """
    Disconnect GitHub account for the authenticated user:
    1. Revokes OAuth grant / token on GitHub's servers.
    2. Deletes encrypted token record from MongoDB.
    """
    user_id = current_user["sub"]
    revoked = False

    access_token = await token_store.get_decrypted_token(user_id)
    if access_token:
        try:
            revoked = github_oauth.revoke_github_token(access_token)
        except Exception as exc:
            logger.warning(f"[GitHubAuth] Remote token revocation failed for {user_id}: {exc}")

    deleted = await token_store.delete_token(user_id)
    return {
        "disconnected": deleted,
        "revoked": revoked,
    }
