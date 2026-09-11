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
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from pydantic import BaseModel

from app.auth import github_oauth
from app.auth.dependencies import get_current_user
from app.db import token_store

logger = logging.getLogger("uvicorn")

router = APIRouter(prefix="/auth/github", tags=["github-auth"])


class GitHubCallbackRequest(BaseModel):
    """Payload for frontend SPA POST callback."""
    code: str
    state: str


@router.get("/login")
async def github_login(
    redirect: bool = Query(
        default=True,
        description="Whether to return a 307 redirect directly to GitHub or a JSON payload with authorize_url",
    ),
    redirect_uri: Optional[str] = Query(
        default=None,
        description="Optional custom callback redirect URI for OAuth",
    ),
    current_user: dict = Depends(get_current_user),
):
    """
    Generate GitHub OAuth consent-screen URL with user-bound CSRF state.
    Requires authenticated Clerk user.
    """
    user_id = current_user["sub"]
    authorize_url = github_oauth.generate_github_auth_url(user_id, redirect_uri=redirect_uri)

    if redirect:
        return RedirectResponse(
            url=authorize_url,
            status_code=status.HTTP_307_TEMPORARY_REDIRECT,
        )
    return {"authorize_url": authorize_url}


@router.get("/callback")
async def github_callback_get(
    code: str = Query(..., description="Authorization code returned by GitHub"),
    state: str = Query(..., description="Signed state token returned by GitHub"),
    request: Request = None,
):
    """
    Handle GitHub OAuth redirect callback in the browser.
    Validates state token, exchanges code for access token, encrypts token into MongoDB,
    and returns a success confirmation page.
    Does NOT require get_current_user because the user is redirected directly by GitHub's servers.
    """
    # 1. Validate signed state (extracts user_id securely bound to state JWT)
    user_id = github_oauth.verify_state(state)

    # 2. Exchange code for access token and scopes
    access_token, scopes = github_oauth.exchange_code_for_token(code)

    # 3. Fetch GitHub username
    github_login = github_oauth.fetch_github_login(access_token)

    # 4. Encrypt and store token in MongoDB
    await token_store.save_user_token(
        user_id=user_id,
        token=access_token,
        github_login=github_login,
        scopes=scopes,
    )

    # Return clean success HTML confirmation
    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
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
        </style>
    </head>
    <body>
        <div class="card">
            <h2>Account Connected!</h2>
            <div class="badge">@{github_login}</div>
            <p>Your GitHub account has been successfully linked to your study workspace.</p>
            <p>You can now safely close this window.</p>
            <script>
                if (window.opener) {{
                    window.opener.postMessage({{ type: 'GITHUB_AUTH_SUCCESS', login: '{github_login}' }}, '*');
                }}
            </script>
        </div>
    </body>
    </html>
    """
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

    return HTMLResponse(content=html_content, status_code=status.HTTP_200_OK)


@router.post("/callback")
async def github_callback_post(
    body: GitHubCallbackRequest,
    current_user: Optional[dict] = Depends(get_current_user),
):
    """
    JSON API endpoint for Single Page Applications (SPAs) posting OAuth code and state.
    """
    state_user_id = github_oauth.verify_state(body.state)

    if current_user and current_user.get("sub") != state_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="GitHub sign-in state does not match the logged-in user.",
        )

    access_token, scopes = github_oauth.exchange_code_for_token(body.code)
    github_login = github_oauth.fetch_github_login(access_token)

    await token_store.save_user_token(
        user_id=state_user_id,
        token=access_token,
        github_login=github_login,
        scopes=scopes,
    )

    return {
        "connected": True,
        "github_login": github_login,
        "user_id": state_user_id,
    }


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


# DELETE alias for REST compliance
@router.delete("/disconnect")
async def github_disconnect_delete(current_user: dict = Depends(get_current_user)):
    """Alias for POST /disconnect."""
    return await github_disconnect(current_user=current_user)
