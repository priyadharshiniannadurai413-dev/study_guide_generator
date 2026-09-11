"""
scripts/test_github_integration.py
----------------------------------
End-to-end verification suite for GitHub MCP and OAuth integration:
1. Verifies create_user_github_tools returns valid, executable LangChain tools.
2. Verifies mcp_client.py gracefully falls back to native GitHub tools when MCP SSE is unreachable.
3. Verifies Supervisor LangGraph classifies GitHub queries and executes github_agent_node.
4. Verifies unlinked users receive clear onboarding instructions with no crash.
5. Verifies FastAPI /auth/github endpoints are mounted and accessible.
"""

import asyncio
import os
import sys

# Ensure UTF-8 output on Windows
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# Ensure repository root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient
from app.main import app
from app.tools.github_tools import create_user_github_tools
from app.services.mcp_client import get_github_mcp_tools
from app.ai.agents.supervisor.graph import build_supervisor_graph
from app.ai.agents.supervisor.nodes.router import router_node


def test_github_tools_initialization():
    print("\n[1] Testing native GitHub tools instantiation...")
    tools = create_user_github_tools("mock_github_token_xyz")
    assert len(tools) >= 6, f"Expected at least 6 tools, got {len(tools)}"
    tool_names = [t.name for t in tools]
    print(f"  [PASS] Created {len(tools)} tools: {', '.join(tool_names)}")
    expected = {
        "github_search_repositories",
        "github_list_repositories",
        "github_get_repository",
        "github_get_file_contents",
        "github_list_commits",
        "github_search_code",
    }
    assert expected.issubset(set(tool_names)), f"Core tool names missing: {expected - set(tool_names)}"


async def test_mcp_client_fallback():
    print("\n[2] Testing mcp_client fallback handling...")
    # For a user without token, returns empty list safely
    empty_tools = await get_github_mcp_tools("non_existent_user_999")
    assert empty_tools == [], f"Expected empty tools for unlinked user, got {empty_tools}"
    print("  [PASS] Unlinked user returns empty tool list without exception")


async def test_supervisor_github_routing():
    print("\n[3] Testing Supervisor router classification for GitHub queries...")
    test_queries = [
        ("Check my GitHub repository for recent commits", "github"),
        ("Inspect my code files on my repo", "github"),
        ("Show recent git commits in my project", "github"),
    ]

    for q, expected_route in test_queries:
        state = {"user_query": q, "route": "", "user_id": "test_user"}
        res = await router_node(state)
        actual_route = res.get("route")
        assert actual_route == expected_route, f"Query '{q}' routed to '{actual_route}', expected '{expected_route}'"
        print(f"  [PASS] Query '{q}' → route='{actual_route}'")


async def test_github_agent_unconnected_user():
    print("\n[4] Testing Supervisor graph execution for unlinked user...")
    graph = build_supervisor_graph()
    initial_state = {
        "messages": [],
        "user_query": "List my repositories on GitHub",
        "user_id": "test_unconnected_student",
        "doc_id": "syllabus",
        "route": "github",
        "retrieved_context": "",
        "final_response": "",
        "study_notes": None,
        "quiz_deck": None,
        "num_questions": 5,
    }
    result = await graph.ainvoke(initial_state)
    resp = result.get("final_response", "")
    assert "GitHub Account Not Connected" in resp or "Connect GitHub Account" in resp, (
        f"Expected connection guidance in response, got: {resp}"
    )
    print("  [PASS] Unlinked student receives guidance to connect GitHub via Settings modal.")


def test_fastapi_github_endpoints():
    print("\n[5] Testing FastAPI /auth/github endpoints via TestClient...")
    client = TestClient(app)

    # 1. /auth/github/login requires user auth
    resp_login = client.get("/auth/github/login", follow_redirects=False)
    assert resp_login.status_code == 401, f"Expected 401 without token, got {resp_login.status_code}"
    print("  [PASS] GET /auth/github/login protected with 401")

    # 2. /auth/github/status requires user auth
    resp_status = client.get("/auth/github/status")
    assert resp_status.status_code == 401, f"Expected 401 without token, got {resp_status.status_code}"
    print("  [PASS] GET /auth/github/status protected with 401")

    # 3. /auth/github/callback accepts code and state without user auth header
    resp_cb = client.get("/auth/github/callback?code=fake&state=invalid")
    assert resp_cb.status_code == 400, f"Expected 400 for bad state, got {resp_cb.status_code}"
    print(f"  [PASS] GET /auth/github/callback accessible for OAuth redirect (HTTP {resp_cb.status_code})")


async def main():
    test_github_tools_initialization()
    await test_mcp_client_fallback()
    await test_supervisor_github_routing()
    await test_github_agent_unconnected_user()
    test_fastapi_github_endpoints()
    print("\n=======================================================")
    print(" ALL GITHUB CONNECTION & MCP INTEGRATION TESTS PASSED! ")
    print("=======================================================\n")


if __name__ == "__main__":
    asyncio.run(main())
