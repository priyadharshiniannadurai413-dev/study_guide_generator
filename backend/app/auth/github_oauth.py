"""
app/auth/github_oauth.py
-------------------------
GitHub OAuth web application flow helpers.

Implements:
1. Authorization URL creation with signed, user-bound state tokens (HS256).
2. Code-for-token exchange via GitHub's OAuth API.
3. User profile information retrieval.
4. Server-side OAuth grant / token revocation.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple
from urllib.parse import urlencode

import requests
from fastapi import HTTPException, status
from jose import ExpiredSignatureError, JWTError, jwt

from app.core.config import settings

logger = logging.getLogger("uvicorn")

_GITHUB_AUTHORIZE_URL = "https://github.com/login/oauth/authorize"
_GITHUB_TOKEN_URL = "https://github.com/login/oauth/access_token"
_GITHUB_USER_API = "https://api.github.com/user"
_GITHUB_GRANT_DELETE_URL = "https://api.github.com/applications/{client_id}/grant"
_GITHUB_TOKEN_REVOKE_URL = "https://api.github.com/applications/{client_id}/token"

# Scopes requested: repo management + user profile read
_GITHUB_SCOPES = "repo read:user"
_STATE_TTL_MINUTES = 10


def _signing_key() -> bytes:
    """Return encryption key bytes for signing OAuth state tokens."""
    key = getattr(settings, "TOKEN_ENCRYPTION_KEY", None)
    if not key:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="TOKEN_ENCRYPTION_KEY is not configured.",
        )
    return key.encode()


def _require_oauth_config() -> None:
    """Ensure required GitHub OAuth environment settings are populated."""
    missing = [
        name
        for name in (
            "GITHUB_OAUTH_CLIENT_ID",
            "GITHUB_OAUTH_CLIENT_SECRET",
            "GITHUB_OAUTH_REDIRECT_URI",
        )
        if not getattr(settings, name, None)
    ]
    if missing:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"GitHub OAuth is not configured. Missing: {', '.join(missing)}",
        )


class TokenExchangeResult(str):
    """
    Custom string type returning access_token while supporting tuple unpacking (token, scopes)
    for seamless compatibility across both caller styles.
    """
    scopes: str = ""

    def __new__(cls, token: str, scopes: str = ""):
        instance = super().__new__(cls, token)
        instance.scopes = scopes
        return instance

    def __iter__(self):
        return iter((str(self), self.scopes))


def generate_github_auth_url(user_id: str, redirect_uri: Optional[str] = None) -> str:
    """
    Generate the GitHub OAuth redirect URL with a secure signed state parameter
    encoding the user's ID to prevent CSRF attacks.

    Args:
        user_id: Clerk user identifier ('sub').
        redirect_uri: Optional custom redirect URI (defaults to settings.GITHUB_OAUTH_REDIRECT_URI).

    Returns:
        Full GitHub authorization URL string.
    """
    _require_oauth_config()
    state = jwt.encode(
        {
            "sub": user_id,
            "exp": datetime.now(timezone.utc) + timedelta(minutes=_STATE_TTL_MINUTES),
        },
        _signing_key(),
        algorithm="HS256",
    )
    target_redirect = redirect_uri or settings.GITHUB_OAUTH_REDIRECT_URI
    params_dict = {
        "client_id": settings.GITHUB_OAUTH_CLIENT_ID,
        "scope": _GITHUB_SCOPES,
        "state": state,
    }
    if target_redirect:
        params_dict["redirect_uri"] = target_redirect

    params = urlencode(params_dict)
    return f"{_GITHUB_AUTHORIZE_URL}?{params}"


# Alias for backward compatibility
build_authorize_url = generate_github_auth_url


def verify_state(state: str) -> str:
    """
    Validate the signed OAuth state JWT and return the user ID it was issued for.

    Args:
        state: State token received from GitHub redirect callback.

    Returns:
        The verified user_id (Clerk 'sub').

    Raises:
        HTTPException: 400 if state is expired, tampered, or invalid.
    """
    try:
        payload = jwt.decode(state, _signing_key(), algorithms=["HS256"])
        user_id = payload.get("sub")
        if not user_id:
            raise JWTError("state payload missing 'sub'")
        return user_id
    except ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="GitHub sign-in link expired. Please try connecting again.",
        )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid GitHub sign-in state.",
        )


def exchange_code_for_token(
    code: str,
    state: Optional[str] = None,
    redirect_uri: Optional[str] = None,
) -> TokenExchangeResult:
    """
    Exchange the GitHub OAuth authorization code for an access token.

    Args:
        code: Authorization code from GitHub redirect.
        state: Optional state token to verify before exchange.
        redirect_uri: Optional redirect URI matching the authorize request.

    Returns:
        TokenExchangeResult: Access token string, also unpackable as (token, scopes).

    Raises:
        HTTPException: 400 if GitHub rejects exchange, 502 on network errors.
    """
    _require_oauth_config()

    if state:
        verify_state(state)

    target_redirect = redirect_uri or settings.GITHUB_OAUTH_REDIRECT_URI
    payload_data = {
        "client_id": settings.GITHUB_OAUTH_CLIENT_ID,
        "client_secret": settings.GITHUB_OAUTH_CLIENT_SECRET,
        "code": code,
    }
    if target_redirect:
        payload_data["redirect_uri"] = target_redirect

    try:
        resp = requests.post(
            _GITHUB_TOKEN_URL,
            json=payload_data,
            headers={"Accept": "application/json"},
            timeout=15,
        )
        resp.raise_for_status()
    except requests.RequestException as exc:
        logger.error(f"[GitHubOAuth] Token exchange request failed: {exc}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Could not reach GitHub to complete sign-in. Please retry.",
        )

    data = resp.json()
    access_token = data.get("access_token")
    if not access_token:
        error = data.get("error_description") or data.get("error") or "unknown error"
        logger.warning(f"[GitHubOAuth] Token exchange rejected: {error}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"GitHub rejected the sign-in: {error}",
        )

    scopes = data.get("scope") or ""
    if isinstance(scopes, list):
        scopes = ",".join(scopes)

    return TokenExchangeResult(access_token, scopes)


def fetch_github_login(access_token: str) -> str:
    """
    Fetch the authenticated user's GitHub username for display.

    Args:
        access_token: Plaintext GitHub OAuth access token.

    Returns:
        GitHub login username string (e.g. 'octocat').
    """
    try:
        resp = requests.get(
            _GITHUB_USER_API,
            headers={
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/vnd.github+json",
            },
            timeout=15,
        )
        resp.raise_for_status()
        return resp.json().get("login", "")
    except (requests.RequestException, KeyError) as exc:
        logger.error(f"[GitHubOAuth] Failed to fetch GitHub user profile: {exc}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Signed in with GitHub but could not fetch your username.",
        )


def is_token_active(access_token: str) -> Optional[bool]:
    """
    Check whether an access token is still valid on GitHub.

    Returns:
        True: Token is active.
        False: Token is revoked or dead (HTTP 401).
        None: Inconclusive (rate-limited, timeout, network error).
    """
    try:
        resp = requests.get(
            _GITHUB_USER_API,
            headers={
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/vnd.github+json",
            },
            timeout=5,
        )
    except requests.RequestException as exc:
        logger.warning(f"[GitHubOAuth] Token validation request failed: {exc}")
        return None

    if resp is not None:
        logger.info(f"[GitHubOAuth] endpoint=/user github_status={resp.status_code}")
    if resp.status_code == 200:
        return True
    if resp.status_code == 401:
        logger.warning("[GitHubOAuth] github_status=401 endpoint=/user — token is revoked or expired")
        return False

    return None


def revoke_github_token(token: str) -> bool:
    """
    Server-side revocation of a GitHub OAuth token or authorization grant.

    Tries deleting the OAuth application grant first so reconnecting requires
    explicit re-consent, falling back to token revocation.

    Args:
        token: Plaintext GitHub access token to revoke.

    Returns:
        bool: True if revocation succeeded on GitHub, False otherwise.
    """
    _require_oauth_config()
    basic = (settings.GITHUB_OAUTH_CLIENT_ID, settings.GITHUB_OAUTH_CLIENT_SECRET)
    headers = {"Accept": "application/vnd.github+json"}
    payload = {"access_token": token}

    # 1. Attempt grant deletion
    try:
        resp = requests.delete(
            _GITHUB_GRANT_DELETE_URL.format(client_id=settings.GITHUB_OAUTH_CLIENT_ID),
            json=payload,
            auth=basic,
            headers=headers,
            timeout=15,
        )
        if resp.status_code == 204:
            logger.info("[GitHubOAuth] Authorization grant successfully deleted on GitHub.")
            return True
        logger.warning(f"[GitHubOAuth] Grant deletion returned HTTP {resp.status_code}; trying token revoke.")
    except requests.RequestException as exc:
        logger.warning(f"[GitHubOAuth] Grant deletion request failed: {exc}")

    # 2. Attempt token revocation fallback
    try:
        resp = requests.post(
            _GITHUB_TOKEN_REVOKE_URL.format(client_id=settings.GITHUB_OAUTH_CLIENT_ID),
            json=payload,
            auth=basic,
            headers=headers,
            timeout=15,
        )
        if resp.status_code == 204:
            logger.info("[GitHubOAuth] Access token successfully revoked via Applications API.")
            return True
        logger.warning(f"[GitHubOAuth] Token revocation returned HTTP {resp.status_code}")
    except requests.RequestException as exc:
        logger.warning(f"[GitHubOAuth] Token revocation request failed: {exc}")

    return False


# Alias for backward compatibility
revoke_user_authorization = revoke_github_token
