"""
app/ai/agents/supervisor/nodes/github_agent.py
----------------------------------------------
Specialist GitHub agent node for the Supervisor LangGraph.
Executes code inspection, commit reviews, and repo queries using
GitHub MCP or native token-bound GitHub tools.
"""

import logging
from typing import Any, Dict, List

from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage

from app.ai.models import get_llm_with_fallback
from app.ai.state import SupervisorState
from app.db.token_store import get_github_login
from app.services.mcp_client import get_github_mcp_tools

logger = logging.getLogger("uvicorn")

GITHUB_SYSTEM_PROMPT = """You are an expert AI software engineering & study assistant with access to the student's connected GitHub account.

Your goal is to inspect student repositories, read source code, review commits, or search files to help them study, debug, and understand their projects.

Guidelines:
1. Always use the available GitHub tools to retrieve real data before answering.
2. Present repository information, file contents, and commit histories in clear, educational markdown.
3. If reading code, explain key architectural patterns, functions, and logic for academic revision.
4. If a file or repository is not found, explain what might be missing (e.g. check repository name or branch) and suggest available alternatives.
5. Provide actionable advice, complexity analysis, and bug fixes when reviewing code.
"""


async def github_agent_node(state: SupervisorState) -> dict:
    """
    Execute GitHub operations for the authenticated student.

    1. Loads GitHub MCP or native tools for user_id.
    2. Injects student's GitHub username context into the prompt.
    3. Executes a multi-turn tool calling loop (up to 3 turns).
    4. Guarantees a synthesized markdown final response.
    """
    user_id = state.get("user_id", "")
    user_query = state.get("user_query", "")

    logger.info(f"[GitHubAgent] Invoked for user_id={user_id} — query: {user_query[:60]}...")

    # 1. Fetch user's GitHub tools
    tools = await get_github_mcp_tools(user_id) if user_id else []

    # 2. Check if GitHub is connected
    if not tools:
        logger.info(f"[GitHubAgent] GitHub not connected for user_id={user_id}. Returning connection guide.")
        return {
            "final_response": (
                "### 🔗 GitHub Account Not Connected\n\n"
                "To inspect your repositories, read project code, or review recent commits, "
                "please link your GitHub account:\n\n"
                "1. Click the **Settings & Shield** icon (🛡️) in the top-right navigation bar.\n"
                "2. In the **GitHub MCP Connector** section, paste your Personal Access Token (PAT) with `repo` scope.\n"
                "3. Click **Save & Activate Connector**.\n\n"
                "Once connected, run your action again and I will inspect your repositories, files, and git history!"
            )
        }

    # 3. Retrieve student's GitHub username to supply context
    github_login = await get_github_login(user_id) if user_id else ""
    system_prompt = GITHUB_SYSTEM_PROMPT
    if github_login:
        system_prompt += (
            f"\n6. The student's connected GitHub username is '{github_login}'. "
            f"If a repository query does not explicitly specify an owner, use '{github_login}' as the default owner."
        )

    # 4. Multi-turn tool execution loop
    try:
        tool_map = {t.name: t for t in tools}
        llm = get_llm_with_fallback(temperature=0.1)
        llm_with_tools = llm.bind_tools(tools)

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_query),
        ]

        max_turns = 3
        turn = 0
        final_text = ""
        tool_outputs_collected = []

        while turn < max_turns:
            turn += 1
            logger.info(f"[GitHubAgent] Turn {turn}/{max_turns}: Invoking LLM...")
            ai_msg = await llm_with_tools.ainvoke(messages)
            tool_calls = getattr(ai_msg, "tool_calls", None)

            if not tool_calls:
                content = ai_msg.content
                if isinstance(content, list):
                    content = "".join(
                        b.get("text", "") if isinstance(b, dict) else str(b)
                        for b in content
                    )
                final_text = str(content).strip()
                break

            # Process tool calls
            messages.append(ai_msg)
            for tc in tool_calls:
                t_name = tc.get("name")
                t_args = tc.get("args", {})
                t_id = tc.get("id")

                logger.info(f"[GitHubAgent] Executing tool '{t_name}' with args {t_args}")
                if t_name in tool_map:
                    try:
                        selected_tool = tool_map[t_name]
                        if hasattr(selected_tool, "ainvoke"):
                            out = await selected_tool.ainvoke(t_args)
                        else:
                            out = selected_tool.invoke(t_args)
                    except Exception as err:
                        logger.warning(f"[GitHubAgent] Tool error ({t_name}): {err}")
                        out = f"Tool '{t_name}' error: {err}"
                else:
                    out = f"Unknown tool '{t_name}'"

                out_str = str(out)
                tool_outputs_collected.append(out_str)
                messages.append(ToolMessage(content=out_str, tool_call_id=t_id))

        # If LLM didn't produce final text after tool calls, run synthesis
        if not final_text:
            logger.info("[GitHubAgent] Synthesizing final response from tool outputs...")
            synthesis_messages = messages + [
                HumanMessage(
                    content=(
                        "Synthesize a clear, detailed, educational response in Markdown "
                        "explaining the GitHub results above to the student. "
                        "Do NOT call any further tools; output your complete analysis directly in markdown."
                    )
                )
            ]
            synth_msg = await llm.ainvoke(synthesis_messages)
            c = synth_msg.content
            if isinstance(c, list):
                c = "".join(b.get("text", "") if isinstance(b, dict) else str(b) for b in c)
            final_text = str(c).strip()

        # Fallback guarantee if text is still empty
        if not final_text and tool_outputs_collected:
            final_text = "\n\n".join(tool_outputs_collected)

        return {"final_response": final_text or "GitHub operation completed successfully."}

    except Exception as exc:
        logger.error(f"[GitHubAgent] Execution failed: {exc}", exc_info=True)
        return {
            "final_response": (
                f"### ⚠️ GitHub Operation Notice\n\n"
                f"An issue occurred while processing the GitHub request: `{exc}`\n\n"
                f"Please verify your GitHub Personal Access Token permissions in the Settings modal."
            )
        }


__all__ = ["github_agent_node"]
