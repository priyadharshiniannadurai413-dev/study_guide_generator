"""
app/routes/integrations.py
--------------------------
FastAPI router for external integrations management (GitHub PAT, tool connector status).

Endpoints:
    GET    /api/integrations/status  → Returns {"github_connected": bool}
    POST   /api/integrations/github  → Saves and encrypts a GitHub Personal Access Token (PAT)
    DELETE /api/integrations/github  → Disconnects and deletes stored GitHub token
"""

import logging
from typing import Optional

import requests
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.auth.dependencies import get_current_user
from app.db import token_store

logger = logging.getLogger("uvicorn")

router = APIRouter(prefix="/api/integrations", tags=["integrations"])


class GitHubPATRequest(BaseModel):
    github_pat: str = Field(..., description="GitHub Personal Access Token (classic or fine-grained)")


@router.get("/status")
async def get_integration_status(current_user: dict = Depends(get_current_user)):
    """
    Return integration status for the authenticated student.
    Returns: {"github_connected": bool, "github_login": Optional[str], "fetch_mcp_active": bool}
    """
    user_id = current_user.get("sub", "")
    token = await token_store.get_decrypted_token(user_id)
    login = await token_store.get_github_login(user_id) if token else None

    return {
        "github_connected": bool(token),
        "github_login": login,
        "fetch_mcp_active": True,
    }


@router.get("/health")
async def get_integrations_health(current_user: dict = Depends(get_current_user)):
    """
    Return detailed health diagnostic for all MCP tool connectors.
    """
    user_id = current_user.get("sub", "")
    token = await token_store.get_decrypted_token(user_id)
    login = await token_store.get_github_login(user_id) if token else None

    return {
        "status": "operational",
        "connectors": {
            "github_mcp": {
                "server": "@modelcontextprotocol/server-github",
                "connected": bool(token),
                "login": login,
                "transport": "stdio / sse proxy",
            },
            "fetch_mcp": {
                "server": "mcp-server-fetch",
                "active": True,
                "engine": "python-httpx-html2text",
                "transport": "stdio (zero-config)",
            },
        },
    }


@router.post("/github")
async def save_github_pat(
    payload: GitHubPATRequest,
    current_user: dict = Depends(get_current_user),
):
    """
    Validate, encrypt, and store a student's GitHub Personal Access Token (PAT).
    """
    pat = payload.github_pat.strip()
    if not pat:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="GitHub PAT cannot be empty.",
        )

    user_id = current_user.get("sub", "")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required.",
        )

    # Validate token against GitHub API to fetch username and verify validity
    login = ""
    scopes = "repo,read:user"
    try:
        resp = requests.get(
            "https://api.github.com/user",
            headers={
                "Authorization": f"Bearer {pat}",
                "Accept": "application/vnd.github+json",
                "User-Agent": "AI-Study-Assistant/1.0",
            },
            timeout=10,
        )
        if resp.status_code == 401:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid GitHub Personal Access Token. Please check token permissions.",
            )
        if resp.status_code == 200:
            user_data = resp.json()
            login = user_data.get("login", "")
            scopes = resp.headers.get("x-oauth-scopes", scopes)
    except requests.RequestException as exc:
        logger.warning(f"[Integrations] GitHub verification error: {exc}")

    # Encrypt and save to MongoDB
    await token_store.save_user_token(
        user_id=user_id,
        token=pat,
        github_login=login or "connected_user",
        scopes=scopes,
    )

    logger.info(f"[Integrations] Stored GitHub PAT for user {user_id} (@{login})")
    return {
        "success": True,
        "github_connected": True,
        "github_login": login,
        "message": "GitHub Personal Access Token configured successfully.",
    }


@router.delete("/github")
async def delete_github_integration(current_user: dict = Depends(get_current_user)):
    """
    Disconnect GitHub integration by removing stored token.
    """
    user_id = current_user.get("sub", "")
    deleted = await token_store.delete_token(user_id)
    return {
        "success": deleted,
        "github_connected": False,
        "message": "GitHub integration disconnected.",
    }


__all__ = ["router"]
