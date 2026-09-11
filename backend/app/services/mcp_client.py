"""
app/services/mcp_client.py
--------------------------
GitHub MCP (Model Context Protocol) client integration.
Connects to https://api.githubcopilot.com/mcp/ using decrypted user OAuth tokens.
Filters down to the essential 32 tools to conserve LLM context window.
Maintains in-memory user client cache with LRU / TTL eviction.
Ensures timeouts and token revocations fail safely without crashing the chat loop.
"""

import asyncio
import logging
import time
from typing import Any, Dict, List, Optional, Set, Tuple

from langchain_core.tools import BaseTool

from app.db.token_store import get_decrypted_token

logger = logging.getLogger("uvicorn")

GITHUB_MCP_ENDPOINT = "https://api.githubcopilot.com/mcp/"
CACHE_TTL_SECONDS = 600  # 10 minutes
CACHE_MAX_ENTRIES = 100
MCP_TIMEOUT_SECONDS = 8.0

# 32 essential GitHub operations to conserve LLM context window
ESSENTIAL_GITHUB_TOOLS: Set[str] = {
    # Repositories & Files (8)
    "list_repositories",
    "get_repository",
    "search_repositories",
    "get_file_contents",
    "create_or_update_file",
    "delete_file",
    "list_directory_contents",
    "get_tree",
    # Issues & Comments (7)
    "list_issues",
    "get_issue",
    "create_issue",
    "update_issue",
    "add_issue_comment",
    "list_issue_comments",
    "search_issues",
    # Pull Requests & Reviews (9)
    "list_pull_requests",
    "get_pull_request",
    "create_pull_request",
    "update_pull_request",
    "merge_pull_request",
    "list_pull_request_commits",
    "list_pull_request_files",
    "get_pull_request_diff",
    "create_pull_request_review",
    # Commits & Branches (6)
    "list_commits",
    "get_commit",
    "list_branches",
    "get_branch",
    "create_branch",
    "delete_branch",
    # User & Code Search (2)
    "get_authenticated_user",
    "search_code",
}


class MCPToolCache:
    """In-memory LRU / TTL tool cache per authenticated user."""

    def __init__(self, ttl: float = CACHE_TTL_SECONDS, max_size: int = CACHE_MAX_ENTRIES):
        self.ttl = ttl
        self.max_size = max_size
        self._cache: Dict[str, Tuple[List[BaseTool], float]] = {}

    def get(self, user_id: str) -> Optional[List[BaseTool]]:
        now = time.time()
        if user_id in self._cache:
            tools, timestamp = self._cache[user_id]
            if now - timestamp <= self.ttl:
                # Refresh LRU access
                self._cache[user_id] = (tools, now)
                return tools
            else:
                del self._cache[user_id]
        return None

    def set(self, user_id: str, tools: List[BaseTool]) -> None:
        now = time.time()
        # Evict expired entries
        expired_keys = [k for k, (_, ts) in self._cache.items() if now - ts > self.ttl]
        for k in expired_keys:
            self._cache.pop(k, None)

        # Evict oldest if capacity exceeded
        if len(self._cache) >= self.max_size:
            oldest_key = min(self._cache.keys(), key=lambda k: self._cache[k][1])
            self._cache.pop(oldest_key, None)

        self._cache[user_id] = (tools, now)

    def invalidate(self, user_id: str) -> None:
        self._cache.pop(user_id, None)


_tool_cache = MCPToolCache()


async def get_github_mcp_tools(clerk_user_id: str) -> List[BaseTool]:
    """
    Load essential GitHub MCP tools for an authenticated Clerk user.

    Steps:
    1. Check user tool cache.
    2. Decrypt user's GitHub OAuth token from MongoDB.
    3. Connect to GitHub Copilot MCP server using SSE transport.
    4. Filter tools to the 32 essential GitHub operations.
    5. Cache and return tools.

    Safely catches timeouts, token revocations, and network errors, returning
    an empty tool list so the primary chat conversation never crashes.
    """
    if not clerk_user_id:
        return []

    # 1. Cache hit
    cached = _tool_cache.get(clerk_user_id)
    if cached is not None:
        return cached

    # 2. Token lookup
    token = await get_decrypted_token(clerk_user_id)
    if not token:
        logger.info(f"[MCPClient] No connected GitHub token found for user {clerk_user_id}")
        return []

    # 3. Connect via langchain_mcp_adapters with timeout safety
    try:
        from langchain_mcp_adapters.sessions import SSEConnection
        from langchain_mcp_adapters.tools import load_mcp_tools

        connection = SSEConnection(
            transport="sse",
            url=GITHUB_MCP_ENDPOINT,
            headers={
                "Authorization": f"Bearer {token}",
                "User-Agent": "AI-Study-Assistant-MCP-Client/1.0",
            },
            timeout=MCP_TIMEOUT_SECONDS,
            sse_read_timeout=MCP_TIMEOUT_SECONDS,
        )

        raw_tools = await asyncio.wait_for(
            load_mcp_tools(connection=connection),
            timeout=MCP_TIMEOUT_SECONDS,
        )

        # 4. Filter down to the essential 32 tools to conserve context window
        filtered_tools: List[BaseTool] = []
        for t in raw_tools:
            name_clean = t.name.lower()
            # Check direct match or prefixed match
            is_essential = any(
                name_clean == ess or name_clean.endswith(f"_{ess}")
                for ess in ESSENTIAL_GITHUB_TOOLS
            )
            if is_essential:
                filtered_tools.append(t)
            if len(filtered_tools) >= 32:
                break

        # Fallback if names differ: take up to 32 tools
        if not filtered_tools and raw_tools:
            filtered_tools = raw_tools[:32]

        logger.info(
            f"[MCPClient] Loaded {len(filtered_tools)} GitHub MCP tools for user {clerk_user_id}"
        )
        _tool_cache.set(clerk_user_id, filtered_tools)
        return filtered_tools

    except asyncio.TimeoutError:
        logger.warning(
            f"[MCPClient] GitHub MCP connection timed out after {MCP_TIMEOUT_SECONDS}s for user {clerk_user_id}"
        )
        return []
    except Exception as exc:
        err_msg = str(exc)
        if "401" in err_msg or "403" in err_msg or "unauthorized" in err_msg.lower():
            logger.warning(
                f"[MCPClient] GitHub OAuth token revoked/expired for user {clerk_user_id}: {exc}"
            )
            _tool_cache.invalidate(clerk_user_id)
        else:
            logger.warning(
                f"[MCPClient] Failed to load GitHub MCP tools for user {clerk_user_id}: {exc}"
            )
        return []


__all__ = [
    "ESSENTIAL_GITHUB_TOOLS",
    "get_github_mcp_tools",
    "_tool_cache",
]
