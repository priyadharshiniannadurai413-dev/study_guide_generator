"""
app/ai/chat_service.py
----------------------
Multi-round agent execution loop with dynamic tool binding, model failover,
and SSE token streaming.
Primary model: Mistral Small (via LiteLLM / langchain_mistralai)
Fallback model: Google Gemini 1.5 Flash
"""

import asyncio
import json
import logging
from typing import Any, AsyncGenerator, Dict, List, Optional

from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)
from langchain_core.tools import BaseTool

from app.ai.litellm_wrapper import ChatLiteLLM
from app.ai.router import Intent, route_query
from app.core.config import settings
from app.services.mcp_client import get_github_mcp_tools
from app.tools.rag_tool import syllabus_rag_search
from app.tools.tavily_tool import web_search_tool

logger = logging.getLogger("uvicorn")

SYSTEM_PROMPT = (
    "You are an expert AI Study Assistant for university engineering and college students. "
    "Provide clear, accurate, high-yield academic guidance, syllabus breakdowns, and revision notes. "
    "When answering questions about the syllabus, refer to relevant course codes, units, and credits. "
    "When executing GitHub actions, summarize repo details and pull requests clearly. "
    "Be encouraging, concise, and structured."
)


def _extract_text_content(content: Any) -> str:
    """Normalize message content to plain string whether it is str, list, or dict blocks."""
    if isinstance(content, str):
        return content
    elif isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict) and "text" in item:
                parts.append(item["text"])
        return "".join(parts)
    return str(content or "")


class ChatService:
    """
    Intelligent multi-model chat coordinator.
    Handles dynamic intent-based tool binding, parallel tool dispatch,
    automatic model failover, and SSE streaming token generation.
    """

    def __init__(self):
        self.primary_model_name = "mistral/mistral-small-latest"
        self.fallback_model_name = "gemini-3.5-flash"

    def _get_primary_llm(self, tools: Optional[List[BaseTool]] = None) -> Any:
        """Instantiate Mistral Small model with optional tool bindings."""
        api_key = settings.MISTRAL_API_KEY
        llm = ChatLiteLLM(
            model=self.primary_model_name,
            api_key=api_key,
            temperature=0.2,
        )
        if tools:
            return llm.bind_tools(tools)
        return llm

    def _get_fallback_llm(self, tools: Optional[List[BaseTool]] = None) -> Any:
        """Instantiate Google Gemini fallback model with optional tool bindings."""
        from langchain_google_genai import ChatGoogleGenerativeAI

        api_key = settings.GEMINI_API_KEY
        llm = ChatGoogleGenerativeAI(
            model=self.fallback_model_name,
            google_api_key=api_key,
            temperature=0.2,
        )
        if tools:
            return llm.bind_tools(tools)
        return llm

    async def _resolve_tools(self, intent: Intent, user_id: str) -> List[BaseTool]:
        """Dynamically select active tools based on classified intent and user context."""
        if intent == Intent.GITHUB:
            # Bind MCP tools only when GitHub intent is active
            mcp_tools = await get_github_mcp_tools(user_id)
            return mcp_tools

        elif intent == Intent.SYLLABUS:
            return [syllabus_rag_search]

        elif intent == Intent.STUDY_MATERIAL:
            return [syllabus_rag_search]

        elif intent == Intent.WEB_SEARCH:
            return [web_search_tool]

        elif intent == Intent.GREETING:
            return []

        else:
            # UNKNOWN / General query: bind standard local tools
            return [syllabus_rag_search, web_search_tool]

    async def _execute_tool_call(self, tool: BaseTool, args: Dict[str, Any], call_id: str) -> ToolMessage:
        """Execute a single tool call asynchronously with protective exception handling."""
        try:
            if hasattr(tool, "ainvoke"):
                result = await tool.ainvoke(args)
            else:
                result = await asyncio.to_thread(tool.invoke, args)
            content = str(result)
        except Exception as exc:
            logger.warning(f"[ChatService] Tool '{tool.name}' execution failed: {exc}")
            content = f"Error executing tool {tool.name}: {exc}"

        return ToolMessage(content=content, tool_call_id=call_id)

    async def _invoke_with_failover(self, messages: List[BaseMessage], tools: Optional[List[BaseTool]] = None) -> Any:
        """Invoke LLM with automatic failover from Mistral Small to Gemini 1.5 Flash."""
        # 1. Try primary Mistral model
        try:
            primary_llm = self._get_primary_llm(tools)
            response = await primary_llm.ainvoke(messages)
            return response
        except Exception as primary_err:
            logger.warning(f"[ChatService] Primary model failed ({primary_err}); switching to fallback.")

        # 2. Fallback to Gemini 1.5 Flash
        fallback_llm = self._get_fallback_llm(tools)
        return await fallback_llm.ainvoke(messages)

    async def stream_tokens(
        self,
        user_prompt: str,
        user_id: str,
        conversation_history: Optional[List[dict]] = None,
    ) -> AsyncGenerator[str, None]:
        """
        Execute multi-round tool loop (up to 4 rounds) and stream final response tokens.
        """
        # 1. Route query to intent
        intent = route_query(user_prompt)
        logger.info(f"[ChatService] User '{user_id}' query intent: {intent.value}")

        # 2. Dynamically bind matching tools
        tools = await self._resolve_tools(intent, user_id)
        tool_map: Dict[str, BaseTool] = {t.name: t for t in tools}

        # 3. Assemble message history
        messages: List[BaseMessage] = [SystemMessage(content=SYSTEM_PROMPT)]
        if conversation_history:
            for item in conversation_history:
                role = item.get("role", "")
                content = item.get("content", "")
                if role == "user":
                    messages.append(HumanMessage(content=content))
                elif role == "assistant":
                    messages.append(AIMessage(content=content))
        messages.append(HumanMessage(content=user_prompt))

        # 4. Multi-round tool execution loop (up to 4 tool rounds)
        max_tool_rounds = 4
        current_round = 0

        while current_round < max_tool_rounds and tools:
            current_round += 1
            response = await self._invoke_with_failover(messages, tools)

            # Check if model made tool calls
            tool_calls = getattr(response, "tool_calls", None) or []
            if not tool_calls:
                # No more tools needed — yield response content
                final_text = _extract_text_content(getattr(response, "content", ""))
                if final_text:
                    yield final_text
                return

            logger.info(
                f"[ChatService] Round {current_round}: Dispatched {len(tool_calls)} tool calls in parallel."
            )
            messages.append(response)

            # Parallel tool dispatch via asyncio.gather
            tasks = []
            for tc in tool_calls:
                call_id = tc.get("id", "")
                fn_name = tc.get("name", "")
                fn_args = tc.get("args", {})
                target_tool = tool_map.get(fn_name)

                if target_tool:
                    tasks.append(self._execute_tool_call(target_tool, fn_args, call_id))
                else:
                    msg = f"Tool '{fn_name}' not available."
                    tasks.append(asyncio.sleep(0, result=ToolMessage(content=msg, tool_call_id=call_id)))

            tool_results = await asyncio.gather(*tasks)
            messages.extend(tool_results)

        # 5. Final generation: stream tokens to caller with failover
        try:
            primary_llm = self._get_primary_llm(tools=None)
            async for chunk in primary_llm.astream(messages):
                raw_c = getattr(chunk, "content", "")
                text = _extract_text_content(raw_c)
                if text:
                    yield text
            return
        except Exception as stream_err:
            logger.warning(f"[ChatService] Primary streaming failed ({stream_err}); falling back to Gemini.")

        fallback_llm = self._get_fallback_llm(tools=None)
        async for chunk in fallback_llm.astream(messages):
            raw_c = getattr(chunk, "content", "")
            text = _extract_text_content(raw_c)
            if text:
                yield text

    async def stream_response(
        self,
        user_prompt: str,
        user_id: str,
        conversation_history: Optional[List[dict]] = None,
    ) -> AsyncGenerator[str, None]:
        """
        Yield SSE-formatted event data chunks: `data: {"text": "..."}\n\n`
        followed by `data: [DONE]\n\n` on completion.
        """
        try:
            async for token in self.stream_tokens(user_prompt, user_id, conversation_history):
                payload = json.dumps({"text": token})
                yield f"data: {payload}\n\n"
        except Exception as exc:
            logger.error(f"[ChatService] Error in stream_response for user {user_id}: {exc}")
            err_payload = json.dumps({"error": f"Stream error: {exc}"})
            yield f"data: {err_payload}\n\n"
        finally:
            yield "data: [DONE]\n\n"


_chat_service_instance: Optional[ChatService] = None


def get_chat_service() -> ChatService:
    """Return singleton ChatService instance."""
    global _chat_service_instance
    if _chat_service_instance is None:
        _chat_service_instance = ChatService()
    return _chat_service_instance


__all__ = ["ChatService", "get_chat_service"]
