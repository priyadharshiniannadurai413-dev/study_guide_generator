"""
app/auth
--------
Authentication and authorization layer:
- Clerk session JWT verification
- FastAPI dependencies (get_current_user)
- GitHub OAuth application flow helpers
"""

from .clerk import verify_clerk_token
from .dependencies import get_current_user
from .github_oauth import (
    generate_github_auth_url,
    exchange_code_for_token,
    revoke_github_token,
    verify_state,
    fetch_github_login,
    is_token_active,
)

__all__ = [
    "verify_clerk_token",
    "get_current_user",
    "generate_github_auth_url",
    "exchange_code_for_token",
    "revoke_github_token",
    "verify_state",
    "fetch_github_login",
    "is_token_active",
]
