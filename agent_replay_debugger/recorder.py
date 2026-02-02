"""Session recording functionality."""

import json
import time
import uuid
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List

from .models import Event, EventType, Session


class Recorder:
    """Record agent sessions for debugging."""

    def __init__(self, session_id: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None):
        """Initialize recorder.

        Args:
            session_id: Unique session identifier (auto-generated if not provided)
            metadata: Session metadata (agent name, version, etc.)
        """
        self.session = Session(
            session_id=session_id or str(uuid.uuid4())[:8],
            started_at=datetime.utcnow().isoformat() + "Z",
            metadata=metadata or {}
        )
        self._event_counter = 0
        self._current_state: Dict[str, Any] = {}
        self._event_stack: List[int] = []  # For nested events
        self._recording = False

    @contextmanager
    def capture(self):
        """Context manager to capture events.

        Yields:
            Self for chaining
        """
        self._recording = True
        try:
            yield self
        finally:
            self._recording = False
            self.session.ended_at = datetime.utcnow().isoformat() + "Z"

    def _next_id(self) -> int:
        """Get next event ID."""
        self._event_counter += 1
        return self._event_counter

    def _create_event(
        self,
        event_type: EventType,
        data: Dict[str, Any],
        duration_ms: Optional[float] = None,
        tags: Optional[List[str]] = None
    ) -> Event:
        """Create and record an event."""
        event = Event(
            id=self._next_id(),
            timestamp=datetime.utcnow().isoformat() + "Z",
            type=event_type,
            data=data,
            duration_ms=duration_ms,
            parent_id=self._event_stack[-1] if self._event_stack else None,
            tags=tags or []
        )
        self.session.events.append(event)

        # Save state snapshot
        if self._current_state:
            self.session.state_snapshots[event.id] = dict(self._current_state)

        return event

    def record_input(
        self,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Event:
        """Record an input event.

        Args:
            role: Role (user, system, etc.)
            content: Input content
            metadata: Additional metadata

        Returns:
            Created Event
        """
        data = {"role": role, "content": content}
        if metadata:
            data["metadata"] = metadata
        return self._create_event(EventType.INPUT, data)

    def record_output(
        self,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Event:
        """Record an output event.

        Args:
            role: Role (assistant, agent, etc.)
            content: Output content
            metadata: Additional metadata

        Returns:
            Created Event
        """
        data = {"role": role, "content": content}
        if metadata:
            data["metadata"] = metadata
        return self._create_event(EventType.OUTPUT, data)

    def record_llm_call(
        self,
        model: str,
        prompt: Any,
        response: Any,
        tokens: Optional[Dict[str, int]] = None,
        duration_ms: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Event:
        """Record an LLM API call.

        Args:
            model: Model identifier
            prompt: Input prompt (string or messages)
            response: Model response
            tokens: Token counts {input, output}
            duration_ms: Call duration
            metadata: Additional metadata

        Returns:
            Created Event
        """
        data = {
            "model": model,
            "prompt": prompt,
            "response": response,
            "tokens": tokens or {}
        }
        if metadata:
            data["metadata"] = metadata
        return self._create_event(EventType.LLM_CALL, data, duration_ms=duration_ms)

    def record_tool_call(
        self,
        tool: str,
        args: Dict[str, Any],
        result: Any,
        duration_ms: Optional[float] = None,
        success: bool = True,
        error: Optional[str] = None
    ) -> Event:
        """Record a tool/function call.

        Args:
            tool: Tool name
            args: Tool arguments
            result: Tool result
            duration_ms: Call duration
            success: Whether call succeeded
            error: Error message if failed

        Returns:
            Created Event
        """
        data = {
            "tool": tool,
            "args": args,
            "result": result,
            "success": success
        }
        if error:
            data["error"] = error
        return self._create_event(EventType.TOOL_CALL, data, duration_ms=duration_ms)

    def record_state_change(
        self,
        key: str,
        old_value: Any,
        new_value: Any
    ) -> Event:
        """Record a state change.

        Args:
            key: State key
            old_value: Previous value
            new_value: New value

        Returns:
            Created Event
        """
        self._current_state[key] = new_value
        return self._create_event(EventType.STATE_CHANGE, {
            "key": key,
            "old_value": old_value,
            "new_value": new_value
        })

    def record_error(
        self,
        error: str,
        error_type: Optional[str] = None,
        stack_trace: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Event:
        """Record an error.

        Args:
            error: Error message
            error_type: Exception type
            stack_trace: Stack trace
            context: Additional context

        Returns:
            Created Event
        """
        data = {"error": error}
        if error_type:
            data["error_type"] = error_type
        if stack_trace:
            data["stack_trace"] = stack_trace
        if context:
            data["context"] = context
        return self._create_event(EventType.ERROR, data, tags=["error"])

    def record_log(
        self,
        level: str,
        message: str,
        data: Optional[Dict[str, Any]] = None
    ) -> Event:
        """Record a log message.

        Args:
            level: Log level (debug, info, warn, error)
            message: Log message
            data: Additional data

        Returns:
            Created Event
        """
        log_data = {"level": level, "message": message}
        if data:
            log_data["data"] = data
        return self._create_event(EventType.LOG, log_data)

    @contextmanager
    def span(self, name: str, tags: Optional[List[str]] = None):
        """Create a span for grouping events.

        Args:
            name: Span name
            tags: Span tags

        Yields:
            Span event
        """
        start = time.time()
        event = self._create_event(EventType.CUSTOM, {"span": name, "status": "started"}, tags=tags)
        self._event_stack.append(event.id)

        try:
            yield event
        finally:
            self._event_stack.pop()
            duration_ms = (time.time() - start) * 1000
            self._create_event(
                EventType.CUSTOM,
                {"span": name, "status": "completed", "span_start_id": event.id},
                duration_ms=duration_ms,
                tags=tags
            )

    def set_state(self, key: str, value: Any) -> None:
        """Set current state without recording event.

        Args:
            key: State key
            value: State value
        """
        self._current_state[key] = value

    def get_state(self) -> Dict[str, Any]:
        """Get current state.

        Returns:
            Current state dictionary
        """
        return dict(self._current_state)

    def get_timeline(self) -> List[Event]:
        """Get event timeline.

        Returns:
            List of events in order
        """
        return list(self.session.events)

    def save(self, filepath: str) -> None:
        """Save session to file.

        Args:
            filepath: Output path
        """
        if not self.session.ended_at:
            self.session.ended_at = datetime.utcnow().isoformat() + "Z"

        with open(filepath, "w") as f:
            json.dump(self.session.to_dict(), f, indent=2, default=str)

    def to_dict(self) -> Dict[str, Any]:
        """Export session as dictionary.

        Returns:
            Session dictionary
        """
        return self.session.to_dict()
