"""Integrations with popular LLM libraries."""

import time
from typing import Any, Optional
from functools import wraps


def patch_openai(recorder: Any) -> None:
    """Patch OpenAI client to record calls.

    Args:
        recorder: Recorder instance
    """
    try:
        import openai
    except ImportError:
        raise ImportError("openai package required for this integration")

    original_create = openai.chat.completions.create

    @wraps(original_create)
    def patched_create(*args, **kwargs):
        start = time.time()
        response = original_create(*args, **kwargs)
        duration_ms = (time.time() - start) * 1000

        # Extract data
        model = kwargs.get("model", "unknown")
        messages = kwargs.get("messages", [])

        recorder.record_llm_call(
            model=model,
            prompt=messages,
            response=response.choices[0].message.content if response.choices else "",
            tokens={
                "input": response.usage.prompt_tokens if response.usage else 0,
                "output": response.usage.completion_tokens if response.usage else 0
            },
            duration_ms=duration_ms
        )

        return response

    openai.chat.completions.create = patched_create


def patch_anthropic(recorder: Any) -> None:
    """Patch Anthropic client to record calls.

    Args:
        recorder: Recorder instance
    """
    try:
        import anthropic
    except ImportError:
        raise ImportError("anthropic package required for this integration")

    original_create = anthropic.Anthropic.messages.create

    @wraps(original_create)
    def patched_create(self, *args, **kwargs):
        start = time.time()
        response = original_create(self, *args, **kwargs)
        duration_ms = (time.time() - start) * 1000

        model = kwargs.get("model", "unknown")
        messages = kwargs.get("messages", [])

        recorder.record_llm_call(
            model=model,
            prompt=messages,
            response=response.content[0].text if response.content else "",
            tokens={
                "input": response.usage.input_tokens if response.usage else 0,
                "output": response.usage.output_tokens if response.usage else 0
            },
            duration_ms=duration_ms
        )

        return response

    anthropic.Anthropic.messages.create = patched_create


class LangChainCallback:
    """LangChain callback handler for recording.

    Usage:
        recorder = Recorder()
        callback = LangChainCallback(recorder)
        agent.run("...", callbacks=[callback])
    """

    def __init__(self, recorder: Any):
        """Initialize callback.

        Args:
            recorder: Recorder instance
        """
        self.recorder = recorder
        self._llm_start_times: dict = {}

    def on_llm_start(self, serialized: dict, prompts: list, **kwargs):
        """Called when LLM starts."""
        run_id = kwargs.get("run_id", "unknown")
        self._llm_start_times[run_id] = time.time()

    def on_llm_end(self, response: Any, **kwargs):
        """Called when LLM ends."""
        run_id = kwargs.get("run_id", "unknown")
        start_time = self._llm_start_times.pop(run_id, time.time())
        duration_ms = (time.time() - start_time) * 1000

        # Extract response data
        text = ""
        tokens = {}

        if hasattr(response, "generations") and response.generations:
            text = response.generations[0][0].text if response.generations[0] else ""

        if hasattr(response, "llm_output") and response.llm_output:
            usage = response.llm_output.get("token_usage", {})
            tokens = {
                "input": usage.get("prompt_tokens", 0),
                "output": usage.get("completion_tokens", 0)
            }

        self.recorder.record_llm_call(
            model="langchain",
            prompt="[LangChain prompt]",
            response=text,
            tokens=tokens,
            duration_ms=duration_ms
        )

    def on_tool_start(self, serialized: dict, input_str: str, **kwargs):
        """Called when tool starts."""
        pass

    def on_tool_end(self, output: str, **kwargs):
        """Called when tool ends."""
        tool_name = kwargs.get("name", "unknown")
        self.recorder.record_tool_call(
            tool=tool_name,
            args={},
            result=output
        )

    def on_tool_error(self, error: Exception, **kwargs):
        """Called on tool error."""
        self.recorder.record_error(
            error=str(error),
            error_type=type(error).__name__
        )

    def on_chain_start(self, serialized: dict, inputs: dict, **kwargs):
        """Called when chain starts."""
        pass

    def on_chain_end(self, outputs: dict, **kwargs):
        """Called when chain ends."""
        pass

    def on_agent_action(self, action: Any, **kwargs):
        """Called on agent action."""
        if hasattr(action, "tool") and hasattr(action, "tool_input"):
            self.recorder.record_log(
                "info",
                f"Agent action: {action.tool}",
                {"input": action.tool_input}
            )
