"""
app/auth/clerk.py
-----------------
Clerk JWT verification using JSON Web Key Set (JWKS).

Verifies Clerk session tokens passed as Bearer tokens in the Authorization header.
Caches the JWKS endpoint response in-memory with a 1-hour TTL.
"""

import logging
import threading
import time
from typing import Any, Dict, Optional

import requests
from fastapi import HTTPException, status
from jose import JWTError, jwt

from app.core.config import settings

logger = logging.getLogger("uvicorn")

# In-memory JWKS cache
_jwks_cache: Optional[Dict[str, Any]] = None
_jwks_cache_time: float = 0.0
_jwks_lock = threading.Lock()
JWKS_CACHE_TTL = 3600  # 1 hour in seconds


def _fetch_jwks() -> Dict[str, Any]:
    """
    Fetch Clerk's JWKS public keys with thread-safe in-memory caching.

    Returns:
        Dict representing the JWKS (containing a list of keys).

    Raises:
        HTTPException: 500 if CLERK_JWKS_URL is unconfigured or unreachable.
    """
    global _jwks_cache, _jwks_cache_time

    with _jwks_lock:
        now = time.time()
        if _jwks_cache and (now - _jwks_cache_time) < JWKS_CACHE_TTL:
            return _jwks_cache

        jwks_url = getattr(settings, "CLERK_JWKS_URL", None)
        if not jwks_url:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="CLERK_JWKS_URL is not configured.",
            )

        try:
            resp = requests.get(jwks_url, timeout=10)
            resp.raise_for_status()
            _jwks_cache = resp.json()
            _jwks_cache_time = now
            logger.info("[Auth] Clerk JWKS fetched and cached successfully.")
            return _jwks_cache
        except requests.RequestException as exc:
            logger.error(f"[Auth] Failed to fetch Clerk JWKS from {jwks_url}: {exc}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to fetch authentication keys from Clerk.",
            )


def verify_clerk_token(token: str) -> Dict[str, Any]:
    """
    Verify and decode a Clerk RS256 session JWT.

    Validates:
    - Token structure and 'kid' in header
    - Matching public key in Clerk's JWKS
    - Expiration ('exp') and not-before ('nbf') claims
    - Issuer ('iss') against settings.CLERK_ISSUER if configured

    Args:
        token: Raw JWT string from Bearer header.

    Returns:
        Dict containing decoded claims including 'sub' (User ID) and 'email'.

    Raises:
        HTTPException: 401 if token is invalid, expired, missing kid, or untrusted.
                       500 if JWKS configuration or fetch fails.
    """
    if not token or not token.strip():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token is empty or missing.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        unverified_header = jwt.get_unverified_header(token)
        kid = unverified_header.get("kid")
        if not kid:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: missing key ID (kid) in header.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        jwks = _fetch_jwks()
        rsa_key: Optional[Dict[str, Any]] = None
        for key in jwks.get("keys", []):
            if key.get("kid") == kid:
                rsa_key = {k: key[k] for k in ("kty", "kid", "use", "n", "e") if k in key}
                break

        if not rsa_key:
            logger.warning(f"[Auth] No matching key found in JWKS for kid={kid}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: no matching public key found.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Decoding options: verify exp and nbf
        options = {
            "verify_signature": True,
            "verify_exp": True,
            "verify_nbf": True,
            "verify_aud": False,
        }

        issuer = getattr(settings, "CLERK_ISSUER", None)
        if issuer:
            issuer_clean = issuer.strip().rstrip("/")
            options["verify_iss"] = True
            payload = jwt.decode(
                token,
                rsa_key,
                algorithms=["RS256"],
                issuer=issuer_clean,
                options=options,
            )
        else:
            options["verify_iss"] = False
            payload = jwt.decode(
                token,
                rsa_key,
                algorithms=["RS256"],
                options=options,
            )

        # Ensure user identifier (sub) is present
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: missing 'sub' claim.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Extract email if present, or check alternate claim names
        if "email" not in payload:
            email = (
                payload.get("email_address")
                or payload.get("primary_email_address")
                or ""
            )
            payload["email"] = email

        return payload

    except HTTPException:
        raise
    except JWTError as exc:
        err_lower = str(exc).lower()
        if "expired" in err_lower:
            logger.warning(f"[Auth] Clerk token expired: {exc}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired. Please sign in again.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        logger.warning(f"[Auth] Clerk JWT validation failed: {exc}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid authentication token: {exc}",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as exc:
        logger.error(f"[Auth] Unexpected error during token verification: {exc}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed.",
            headers={"WWW-Authenticate": "Bearer"},
        )
