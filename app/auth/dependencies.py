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
        # Fallback to manual Authorization header parsing
        auth_header = request.headers.get("Authorization")
        if not auth_header:
            logger.info("[Auth] No Authorization header provided")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required. Please sign in.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        parts = auth_header.strip().split()
        if len(parts) != 2 or parts[0].lower() != "bearer":
            logger.info(f"[Auth] Malformed Authorization header: {auth_header[:20]}...")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid Authorization header format. Use: Bearer <token>",
                headers={"WWW-Authenticate": "Bearer"},
            )
        token = parts[1]

    payload = verify_clerk_token(token)

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload: missing user ID ('sub').",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return payload
