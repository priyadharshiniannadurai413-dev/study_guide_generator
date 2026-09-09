"""
app/ai/litellm_wrapper.py
-------------------------
Custom ChatLiteLLM wrapper implementing LangChain's BaseChatModel.
Supports tool calling (bind_tools), synchronous and asynchronous generation,
and token streaming via LiteLLM.
"""

import json
import logging
from typing import Any, AsyncIterator, Callable, Dict, Iterator, List, Optional, Sequence, Union

import litellm
from langchain_core.callbacks import (
    AsyncCallbackManagerForLLMRun,
    CallbackManagerForLLMRun,
)
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import (
    AIMessage,
    AIMessageChunk,
    BaseMessage,
    ChatMessage,
    FunctionMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)
from langchain_core.outputs import (
    ChatGeneration,
    ChatGenerationChunk,
    ChatResult,
)
from langchain_core.tools import BaseTool
from langchain_core.utils.function_calling import convert_to_openai_tool
from pydantic import Field

logger = logging.getLogger("uvicorn")


def _convert_message_to_dict(message: BaseMessage) -> Dict[str, Any]:
    """Convert a LangChain message object to standard OpenAI/LiteLLM dictionary format."""
    if isinstance(message, SystemMessage):
        return {"role": "system", "content": str(message.content)}
    elif isinstance(message, HumanMessage):
        return {"role": "user", "content": str(message.content)}
    elif isinstance(message, AIMessage):
        msg_dict: Dict[str, Any] = {"role": "assistant", "content": str(message.content or "")}
        if message.tool_calls:
            formatted_calls = []
            for tc in message.tool_calls:
                formatted_calls.append({
                    "id": tc.get("id", ""),
                    "type": "function",
                    "function": {
                        "name": tc.get("name", ""),
                        "arguments": json.dumps(tc.get("args", {})) if isinstance(tc.get("args"), dict) else str(tc.get("args", "{}")),
                    },
                })
            msg_dict["tool_calls"] = formatted_calls
        return msg_dict
    elif isinstance(message, ToolMessage):
        return {
            "role": "tool",
            "tool_call_id": message.tool_call_id,
            "content": str(message.content),
        }
    elif isinstance(message, FunctionMessage):
        return {
            "role": "function",
            "name": message.name,
            "content": str(message.content),
        }
    elif isinstance(message, ChatMessage):
        return {"role": message.role, "content": str(message.content)}
    else:
        return {"role": "user", "content": str(message.content)}


def _extract_tool_calls_from_response(raw_message: Any) -> List[Dict[str, Any]]:
    """Extract and normalize tool calls from LiteLLM response message."""
    tool_calls: List[Dict[str, Any]] = []
    raw_calls = getattr(raw_message, "tool_calls", None)
    if not raw_calls and isinstance(raw_message, dict):
        raw_calls = raw_message.get("tool_calls")

    if not raw_calls:
        return tool_calls

    for tc in raw_calls:
        if isinstance(tc, dict):
            fn = tc.get("function", {})
            call_id = tc.get("id", "")
            fn_name = fn.get("name", "")
            fn_args_raw = fn.get("arguments", "{}")
        else:
            fn = getattr(tc, "function", None)
            call_id = getattr(tc, "id", "")
            fn_name = getattr(fn, "name", "") if fn else ""
            fn_args_raw = getattr(fn, "arguments", "{}") if fn else "{}"

        if isinstance(fn_args_raw, str):
            try:
                fn_args = json.loads(fn_args_raw)
            except Exception:
                fn_args = {"raw": fn_args_raw}
        elif isinstance(fn_args_raw, dict):
            fn_args = fn_args_raw
        else:
            fn_args = {}

        tool_calls.append({
            "name": fn_name,
            "args": fn_args,
            "id": call_id,
        })

    return tool_calls


class ChatLiteLLM(BaseChatModel):
    """
    LangChain BaseChatModel implementation leveraging LiteLLM.
    Supports tool binding, streaming, and failover across model providers.
    """

    model: str = Field(default="mistral/mistral-small-latest", description="LiteLLM model identifier")
    api_key: Optional[str] = Field(default=None, description="API key for the underlying model provider")
    temperature: float = Field(default=0.2, description="Sampling temperature")
    max_tokens: Optional[int] = Field(default=None, description="Maximum tokens to generate")
    bound_tools: Optional[List[Dict[str, Any]]] = Field(default=None, description="Bound OpenAI-format tool definitions")
    extra_kwargs: Dict[str, Any] = Field(default_factory=dict, description="Additional kwargs passed to litellm.completion")

    @property
    def _llm_type(self) -> str:
        return "litellm"

    def bind_tools(
        self,
        tools: Sequence[Union[Dict[str, Any], type, Callable, BaseTool]],
        **kwargs: Any,
    ) -> "ChatLiteLLM":
        """
        Bind tools to the model instance in standard OpenAI function calling format.
        """
        formatted_tools = [convert_to_openai_tool(tool) for tool in tools]
        updated_kwargs = dict(self.extra_kwargs)
        updated_kwargs.update(kwargs)
        return self.__class__(
            model=self.model,
            api_key=self.api_key,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            bound_tools=formatted_tools,
            extra_kwargs=updated_kwargs,
        )

    def _prepare_payload(self, messages: List[BaseMessage], **kwargs: Any) -> Dict[str, Any]:
        converted_messages = [_convert_message_to_dict(m) for m in messages]
        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": converted_messages,
            "temperature": self.temperature,
        }
        if self.api_key:
            payload["api_key"] = self.api_key
        if self.max_tokens:
            payload["max_tokens"] = self.max_tokens

        tools = kwargs.get("tools") or self.bound_tools
        if tools:
            payload["tools"] = tools

        for k, v in self.extra_kwargs.items():
            if k not in payload:
                payload[k] = v
        for k, v in kwargs.items():
            if k != "tools":
                payload[k] = v

        return payload

    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> ChatResult:
        payload = self._prepare_payload(messages, **kwargs)
        if stop:
            payload["stop"] = stop

        response = litellm.completion(**payload)
        choice = response.choices[0]
        raw_msg = choice.message
        content = raw_msg.content or ""
        tool_calls = _extract_tool_calls_from_response(raw_msg)

        ai_message = AIMessage(
            content=content,
            tool_calls=tool_calls,
        )
        generation = ChatGeneration(message=ai_message)
        return ChatResult(generations=[generation])

    async def _agenerate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[AsyncCallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> ChatResult:
        payload = self._prepare_payload(messages, **kwargs)
        if stop:
            payload["stop"] = stop

        response = await litellm.acompletion(**payload)
        choice = response.choices[0]
        raw_msg = choice.message
        content = raw_msg.content or ""
        tool_calls = _extract_tool_calls_from_response(raw_msg)

        ai_message = AIMessage(
            content=content,
            tool_calls=tool_calls,
        )
        generation = ChatGeneration(message=ai_message)
        return ChatResult(generations=[generation])

    async def _astream(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[AsyncCallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> AsyncIterator[ChatGenerationChunk]:
        payload = self._prepare_payload(messages, **kwargs)
        payload["stream"] = True
        if stop:
            payload["stop"] = stop

        response = await litellm.acompletion(**payload)
        async for chunk in response:
            if not chunk or not chunk.choices:
                continue
            delta = chunk.choices[0].delta
            content = delta.content or ""
            chunk_message = AIMessageChunk(content=content)
            yield ChatGenerationChunk(message=chunk_message)
            if run_manager:
                await run_manager.on_llm_new_token(content)


__all__ = ["ChatLiteLLM"]
