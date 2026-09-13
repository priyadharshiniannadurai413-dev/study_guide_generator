"""
app/tools/github_tools.py
-------------------------
Direct, reliable GitHub API tools for the LangGraph assistant.
Operates on behalf of the student using their decrypted GitHub OAuth access token.
Serves as native fallback or direct tools alongside GitHub MCP.
"""

import base64
import logging
import os
from typing import Any, Dict, List, Optional, Tuple

import requests
from langchain_core.tools import BaseTool, StructuredTool
from pydantic import BaseModel, Field

logger = logging.getLogger("uvicorn")

GITHUB_API_BASE = "https://api.github.com"
DEFAULT_TIMEOUT = 10


def _get_headers(token: str) -> Dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "User-Agent": "AI-Study-Assistant/1.0",
    }


def _handle_api_response(resp: requests.Response, endpoint: str) -> Optional[str]:
    """
    Log safe status and check for errors, specifically handling 401 Unauthorized.
    """
    logger.info(f"[GitHubTools] endpoint={endpoint} github_status={resp.status_code}")
    if resp.status_code == 401:
        logger.warning(
            f"[GitHubTools] github_status=401 endpoint={endpoint}. "
            "GitHub access token is invalid, expired, or revoked."
        )
        return (
            "GitHub API error 401: Bad credentials. The connected GitHub access token is "
            "invalid, expired, or revoked. Please reconnect your GitHub account in Settings."
        )
    if resp.status_code != 200:
        return f"GitHub API error {resp.status_code}: {resp.text}"
    return None


def _parse_owner_repo(owner: str, repo: str, default_owner: str = "") -> Tuple[str, str]:
    """
    Safely normalize owner and repo strings.
    Handles 'owner/repo' combined in owner or repo fields, or omitted owner.
    """
    owner = (owner or "").strip()
    repo = (repo or "").strip()

    if "/" in owner:
        parts = owner.split("/", 1)
        return parts[0].strip(), parts[1].strip()
    if "/" in repo:
        parts = repo.split("/", 1)
        return parts[0].strip(), parts[1].strip()
    if not owner and default_owner:
        return default_owner.strip(), repo

    return owner, repo


def create_user_github_tools(token: str, default_owner: str = "") -> List[BaseTool]:
    """
    Instantiate LangChain tools pre-bound with the user's GitHub token.
    Provides tools with both 'github_' prefixes and bare aliases for maximum LLM compatibility.
    """
    headers = _get_headers(token)

    # 1. Search Repositories
    class SearchReposInput(BaseModel):
        query: str = Field(..., description="Search keyword or query string, e.g. 'study guide' or 'pic16f877a'")
        per_page: int = Field(default=5, description="Number of results (max 15)")

    def search_repositories(query: str, per_page: int = 5) -> str:
        """Search public and accessible GitHub repositories by keyword or name."""
        try:
            resp = requests.get(
                f"{GITHUB_API_BASE}/search/repositories",
                headers=headers,
                params={"q": query.strip(), "per_page": min(max(per_page, 1), 15)},
                timeout=DEFAULT_TIMEOUT,
            )
            err = _handle_api_response(resp, "/search/repositories")
            if err:
                return err
            items = resp.json().get("items", [])
            if not items:
                return f"No repositories found matching '{query}'."

            lines = [f"### Repositories matching '{query}':"]
            for r in items:
                name = r.get("full_name")
                desc = r.get("description") or "No description"
                lang = r.get("language") or "Unknown"
                stars = r.get("stargazers_count", 0)
                url = r.get("html_url")
                lines.append(f"- **[{name}]({url})** (Stars: {stars}, {lang}): {desc}")
            return "\n".join(lines)
        except Exception as exc:
            return f"Failed to search repositories: {exc}"

    # 2. List Repositories
    class ListReposInput(BaseModel):
        per_page: int = Field(default=10, description="Number of repositories to return (max 30)")
        sort: str = Field(default="updated", description="Sort order: updated, pushed, created, full_name")

    def list_repositories(per_page: int = 10, sort: str = "updated") -> str:
        """List repositories owned or accessible by the authenticated user."""
        try:
            resp = requests.get(
                f"{GITHUB_API_BASE}/user/repos",
                headers=headers,
                params={"per_page": min(per_page, 30), "sort": sort},
                timeout=DEFAULT_TIMEOUT,
            )
            err = _handle_api_response(resp, "/user/repos")
            if err:
                return err
            repos = resp.json()
            if not repos:
                return "No repositories found for this account."

            lines = ["### Accessible Repositories:"]
            for r in repos:
                name = r.get("full_name")
                desc = r.get("description") or "No description"
                lang = r.get("language") or "Unknown"
                private = "Private" if r.get("private") else "Public"
                stars = r.get("stargazers_count", 0)
                url = r.get("html_url")
                lines.append(f"- **[{name}]({url})** ({private}, {lang}, Stars: {stars}): {desc}")
            return "\n".join(lines)
        except Exception as exc:
            return f"Failed to list repositories: {exc}"

    # 3. Get Repository Info
    class RepoInfoInput(BaseModel):
        owner: str = Field(..., description="GitHub owner or organization, e.g. 'octocat'")
        repo: str = Field(..., description="Repository name, e.g. 'Hello-World'")

    def get_repository_details(owner: str, repo: str) -> str:
        """Get summary details and description of a specific repository."""
        owner, repo = _parse_owner_repo(owner, repo, default_owner)
        try:
            resp = requests.get(
                f"{GITHUB_API_BASE}/repos/{owner}/{repo}",
                headers=headers,
                timeout=DEFAULT_TIMEOUT,
            )
            if resp.status_code == 404:
                return f"Repository '{owner}/{repo}' not found or access denied."
            err = _handle_api_response(resp, f"/repos/{owner}/{repo}")
            if err:
                return err
            data = resp.json()
            return (
                f"### Repository: {data.get('full_name')}\n"
                f"- **Description**: {data.get('description') or 'None'}\n"
                f"- **Default Branch**: `{data.get('default_branch')}`\n"
                f"- **Language**: {data.get('language') or 'N/A'}\n"
                f"- **Stars**: {data.get('stargazers_count', 0)} | **Forks**: {data.get('forks_count', 0)}\n"
                f"- **Open Issues**: {data.get('open_issues_count', 0)}\n"
                f"- **URL**: {data.get('html_url')}"
            )
        except Exception as exc:
            return f"Failed to fetch repository details: {exc}"

    # 4. Get File or Directory Contents
    class FileContentInput(BaseModel):
        owner: str = Field(..., description="Repository owner username or org")
        repo: str = Field(..., description="Repository name")
        path: str = Field(default="", description="Path to file or folder, e.g. 'src/main.py' or 'README.md'")
        ref: Optional[str] = Field(default=None, description="Branch or commit SHA (defaults to default branch)")

    def get_file_contents(owner: str, repo: str, path: str = "", ref: Optional[str] = None) -> str:
        """Read code from a repository file or list items inside a repository folder."""
        owner, repo = _parse_owner_repo(owner, repo, default_owner)
        clean_path = path.strip().lstrip("/")

        def _fetch_content(p: str):
            params = {}
            if ref:
                params["ref"] = ref
            return requests.get(
                f"{GITHUB_API_BASE}/repos/{owner}/{repo}/contents/{p}",
                headers=headers,
                params=params,
                timeout=DEFAULT_TIMEOUT,
            )

        try:
            resp = _fetch_content(clean_path)

            # If 404, attempt case variations for top-level files like README.md
            if resp.status_code == 404 and clean_path:
                basename = os.path.basename(clean_path)
                dirname = os.path.dirname(clean_path)
                variations = [basename.lower(), basename.capitalize(), basename.upper()]
                if basename.lower() == "readme.md":
                    variations.extend(["Readme.md", "README.md", "readme.md", "README", "Readme"])

                for var in set(variations):
                    if var != basename:
                        candidate_path = f"{dirname}/{var}".lstrip("/") if dirname else var
                        candidate_resp = _fetch_content(candidate_path)
                        if candidate_resp.status_code == 200:
                            resp = candidate_resp
                            clean_path = candidate_path
                            break

            # If still 404, list directory to assist user
            if resp.status_code == 404:
                dirname = os.path.dirname(clean_path)
                dir_resp = _fetch_content(dirname)
                hint = ""
                if dir_resp.status_code == 200 and isinstance(dir_resp.json(), list):
                    avail = [f"- `{item.get('name')}`" for item in dir_resp.json()[:25]]
                    hint = f"\n\nAvailable items in `{owner}/{repo}/{dirname or 'root'}`:\n" + "\n".join(avail)
                return f"File or path '{path}' not found in '{owner}/{repo}'.{hint}"

            err = _handle_api_response(resp, f"/repos/{owner}/{repo}/contents/{clean_path}")
            if err:
                return err

            data = resp.json()

            # If path points to a directory
            if isinstance(data, list):
                lines = [f"### Directory listing for `{owner}/{repo}/{clean_path}`:"]
                for item in data[:40]:
                    t = item.get("type", "file")
                    p = item.get("name")
                    lines.append(f"- `[{t}]` {p}")
                return "\n".join(lines)

            # If path points to a file
            encoding = data.get("encoding")
            raw_content = data.get("content", "")
            if encoding == "base64":
                if raw_content:
                    decoded = base64.b64decode(raw_content).decode("utf-8", errors="replace")
                    if len(decoded) > 14000:
                        decoded = decoded[:14000] + "\n\n...[File truncated to first 14,000 characters]"
                else:
                    decoded = "(Empty file — 0 bytes)"
                return f"### File `{data.get('path')}` ({data.get('size')} bytes):\n```\n{decoded}\n```"

            return f"File '{clean_path}' has unsupported encoding: {encoding}"
        except Exception as exc:
            return f"Failed to read file content: {exc}"

    # 5. List Commits
    class ListCommitsInput(BaseModel):
        owner: str = Field(..., description="Repository owner")
        repo: str = Field(..., description="Repository name")
        per_page: int = Field(default=5, description="Number of recent commits (max 15)")

    def list_commits(owner: str, repo: str, per_page: int = 5) -> str:
        """Fetch recent commit history for a repository."""
        owner, repo = _parse_owner_repo(owner, repo, default_owner)
        try:
            resp = requests.get(
                f"{GITHUB_API_BASE}/repos/{owner}/{repo}/commits",
                headers=headers,
                params={"per_page": min(per_page, 15)},
                timeout=DEFAULT_TIMEOUT,
            )
            err = _handle_api_response(resp, f"/repos/{owner}/{repo}/commits")
            if err:
                return err
            commits = resp.json()
            if not commits:
                return f"No commits found for '{owner}/{repo}'."

            lines = [f"### Recent Commits for `{owner}/{repo}`:"]
            for c in commits:
                sha = c.get("sha", "")[:7]
                msg = c.get("commit", {}).get("message", "").split("\n")[0]
                author = c.get("commit", {}).get("author", {}).get("name", "Unknown")
                date = c.get("commit", {}).get("author", {}).get("date", "")[:10]
                lines.append(f"- [`{sha}`] {msg} *(by {author} on {date})*")
            return "\n".join(lines)
        except Exception as exc:
            return f"Failed to list commits: {exc}"

    # 6. Search Code
    class SearchCodeInput(BaseModel):
        query: str = Field(..., description="Code search keywords or symbols")
        owner: Optional[str] = Field(default=None, description="Scope search to owner or org")
        repo: Optional[str] = Field(default=None, description="Scope search to specific repo")

    def search_code(query: str, owner: Optional[str] = None, repo: Optional[str] = None) -> str:
        """Search code files on GitHub matching a keyword or function name."""
        try:
            q = query
            if repo:
                if owner and "/" not in repo:
                    q += f" repo:{owner}/{repo}"
                else:
                    q += f" repo:{repo}"
            elif owner:
                q += f" user:{owner}"

            resp = requests.get(
                f"{GITHUB_API_BASE}/search/code",
                headers=headers,
                params={"q": q, "per_page": 5},
                timeout=DEFAULT_TIMEOUT,
            )
            err = _handle_api_response(resp, "/search/code")
            if err:
                return err
            items = resp.json().get("items", [])
            if not items:
                return f"No code results found for '{query}'."

            lines = [f"### Code Search Results for `{query}`:"]
            for it in items[:5]:
                repo_name = it.get("repository", {}).get("full_name")
                file_path = it.get("path")
                html_url = it.get("html_url")
                lines.append(f"- **[{repo_name}]({html_url})**: `{file_path}`")
            return "\n".join(lines)
        except Exception as exc:
            return f"Failed to search code: {exc}"

    # Return registered tools with both prefixed and bare names
    return [
        StructuredTool.from_function(
            func=search_repositories,
            name="github_search_repositories",
            description="Search public and accessible GitHub repositories by keyword, name, or topic.",
            args_schema=SearchReposInput,
        ),
        StructuredTool.from_function(
            func=search_repositories,
            name="search_repositories",
            description="Search public and accessible GitHub repositories by keyword, name, or topic.",
            args_schema=SearchReposInput,
        ),
        StructuredTool.from_function(
            func=list_repositories,
            name="github_list_repositories",
            description="List repositories accessible by the student's connected GitHub account.",
            args_schema=ListReposInput,
        ),
        StructuredTool.from_function(
            func=list_repositories,
            name="list_repositories",
            description="List repositories accessible by the student's connected GitHub account.",
            args_schema=ListReposInput,
        ),
        StructuredTool.from_function(
            func=get_repository_details,
            name="github_get_repository",
            description="Get details, stars, language, and default branch for a specific GitHub repository.",
            args_schema=RepoInfoInput,
        ),
        StructuredTool.from_function(
            func=get_repository_details,
            name="get_repository",
            description="Get details, stars, language, and default branch for a specific GitHub repository.",
            args_schema=RepoInfoInput,
        ),
        StructuredTool.from_function(
            func=get_file_contents,
            name="github_get_file_contents",
            description="Read the contents of a code file or list directory contents in a GitHub repository.",
            args_schema=FileContentInput,
        ),
        StructuredTool.from_function(
            func=get_file_contents,
            name="get_file_contents",
            description="Read the contents of a code file or list directory contents in a GitHub repository.",
            args_schema=FileContentInput,
        ),
        StructuredTool.from_function(
            func=list_commits,
            name="github_list_commits",
            description="List recent git commit messages, authors, and dates for a repository.",
            args_schema=ListCommitsInput,
        ),
        StructuredTool.from_function(
            func=list_commits,
            name="list_commits",
            description="List recent git commit messages, authors, and dates for a repository.",
            args_schema=ListCommitsInput,
        ),
        StructuredTool.from_function(
            func=search_code,
            name="github_search_code",
            description="Search for keywords, symbols, or code patterns across student GitHub repositories.",
            args_schema=SearchCodeInput,
        ),
        StructuredTool.from_function(
            func=search_code,
            name="search_code",
            description="Search for keywords, symbols, or code patterns across student GitHub repositories.",
            args_schema=SearchCodeInput,
        ),
    ]


__all__ = ["create_user_github_tools"]
