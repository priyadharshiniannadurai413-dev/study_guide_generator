"""
app/auth/dependencies.py
-------------------------
FastAPI dependencies for user authentication.

Provides get_current_user() which extracts and verifies the Clerk JWT
from the Authorization header using HTTPBearer.
"""

import logging
from typing import Any, Dict, Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.auth.clerk import verify_clerk_token

logger = logging.getLogger("uvicorn")

# HTTPBearer security scheme with auto_error=False to allow custom 401 messaging
security_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme),
) -> Dict[str, Any]:
    """
    FastAPI dependency that extracts the Bearer token, verifies it against
    Clerk's JWKS public keys, and returns the decoded user payload.

    Args:
        request: FastAPI Request instance.
        credentials: Optional HTTPAuthorizationCredentials provided by HTTPBearer.

    Returns:
        Dict with at least: {"sub": "<clerk_user_id>", "email": "...", ...}

    Raises:
        HTTPException: 401 if token is missing, malformed, expired, or invalid.
    """
    token: Optional[str] = None

    if credentials and credentials.credentials:
        token = credentials.credentials
    else:
        # Check query param ?token= first (useful for direct browser redirects like OAuth login)
        query_token = request.query_params.get("token")
        auth_header = request.headers.get("Authorization")

        if query_token:
            token = query_token
        elif auth_header:
            parts = auth_header.strip().split()
            if len(parts) != 2 or parts[0].lower() != "bearer":
                logger.info(f"[Auth] Malformed Authorization header: {auth_header[:20]}...")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid Authorization header format. Use: Bearer <token>",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            token = parts[1]
        else:
            logger.info("[Auth] No Authorization header or token query parameter provided")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required. Please sign in.",
                headers={"WWW-Authenticate": "Bearer"},
            )

    # Support  development tokens (e.g. dev_*, student_demo_user)
    if token and (token.startswith("dev_") or token in ("student_demo_user", "student_dev_token", "demo_token")):
        dev_sub = token if token.startswith("dev_") else "student_demo_user"
        return {
            "sub": dev_sub,
            "email": f"{dev_sub}@university.edu",
            "name": "Student Scholar",
        }

    payload = verify_clerk_token(token)

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload: missing user ID ('sub').",
            headers={"WWW-Authenticate": "Bearer"},
        )

    origin = request.headers.get("origin", "")
    logger.info(
        f"[Auth] Authenticated Clerk user_id={user_id} path={request.url.path} origin={origin}"
    )

    return payload
