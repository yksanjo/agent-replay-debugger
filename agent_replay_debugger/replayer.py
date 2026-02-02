"""Session replay functionality."""

import json
from pathlib import Path
from typing import Optional, Dict, Any, List, Iterator

from .models import Event, EventType, Session


class Replayer:
    """Replay and inspect recorded sessions."""

    def __init__(self, session: Session):
        """Initialize replayer.

        Args:
            session: Session to replay
        """
        self.session = session
        self._position = 0
        self._breakpoints: List[int] = []

    @classmethod
    def from_file(cls, filepath: str) -> "Replayer":
        """Load session from file.

        Args:
            filepath: Path to session file

        Returns:
            Replayer instance
        """
        with open(filepath) as f:
            data = json.load(f)
        session = Session.from_dict(data)
        return cls(session)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Replayer":
        """Create replayer from dictionary.

        Args:
            data: Session dictionary

        Returns:
            Replayer instance
        """
        session = Session.from_dict(data)
        return cls(session)

    @property
    def current_position(self) -> int:
        """Get current position in timeline."""
        return self._position

    @property
    def total_events(self) -> int:
        """Get total number of events."""
        return len(self.session.events)

    def has_next(self) -> bool:
        """Check if more events exist.

        Returns:
            True if more events available
        """
        return self._position < len(self.session.events)

    def has_prev(self) -> bool:
        """Check if previous events exist.

        Returns:
            True if previous events available
        """
        return self._position > 0

    def step(self) -> Optional[Event]:
        """Step to next event.

        Returns:
            Next event or None if at end
        """
        if not self.has_next():
            return None
        event = self.session.events[self._position]
        self._position += 1
        return event

    def step_back(self) -> Optional[Event]:
        """Step to previous event.

        Returns:
            Previous event or None if at start
        """
        if not self.has_prev():
            return None
        self._position -= 1
        return self.session.events[self._position]

    def current(self) -> Optional[Event]:
        """Get current event without advancing.

        Returns:
            Current event or None
        """
        if self._position == 0:
            return None
        return self.session.events[self._position - 1]

    def peek(self) -> Optional[Event]:
        """Peek at next event without advancing.

        Returns:
            Next event or None
        """
        if not self.has_next():
            return None
        return self.session.events[self._position]

    def goto(self, event_id: Optional[int] = None, position: Optional[int] = None) -> Optional[Event]:
        """Jump to specific event.

        Args:
            event_id: Event ID to jump to
            position: Position index to jump to

        Returns:
            Event at new position
        """
        if event_id is not None:
            for i, event in enumerate(self.session.events):
                if event.id == event_id:
                    self._position = i + 1
                    return event
            return None

        if position is not None:
            if 0 <= position < len(self.session.events):
                self._position = position + 1
                return self.session.events[position]
            return None

        return None

    def reset(self) -> None:
        """Reset to beginning."""
        self._position = 0

    def get_state(self, event_id: Optional[int] = None) -> Dict[str, Any]:
        """Get state at specific event.

        Args:
            event_id: Event ID (default: current position)

        Returns:
            State dictionary
        """
        if event_id is None:
            # Get state at current position
            if self._position == 0:
                return {}
            event_id = self.session.events[self._position - 1].id

        # Find closest state snapshot
        snapshots = self.session.state_snapshots
        if event_id in snapshots:
            return dict(snapshots[event_id])

        # Build state from history
        state = {}
        for event in self.session.events:
            if event.type == EventType.STATE_CHANGE:
                state[event.data["key"]] = event.data["new_value"]
            if event.id == event_id:
                break

        return state

    def filter(
        self,
        event_type: Optional[EventType] = None,
        tags: Optional[List[str]] = None,
        search: Optional[str] = None
    ) -> List[Event]:
        """Filter events.

        Args:
            event_type: Filter by event type
            tags: Filter by tags (any match)
            search: Search in event data

        Returns:
            Filtered events
        """
        events = self.session.events

        if event_type:
            events = [e for e in events if e.type == event_type]

        if tags:
            events = [e for e in events if any(t in e.tags for t in tags)]

        if search:
            search_lower = search.lower()
            filtered = []
            for e in events:
                data_str = json.dumps(e.data).lower()
                if search_lower in data_str:
                    filtered.append(e)
            events = filtered

        return events

    def get_llm_calls(self) -> List[Event]:
        """Get all LLM calls.

        Returns:
            List of LLM call events
        """
        return self.filter(event_type=EventType.LLM_CALL)

    def get_tool_calls(self) -> List[Event]:
        """Get all tool calls.

        Returns:
            List of tool call events
        """
        return self.filter(event_type=EventType.TOOL_CALL)

    def get_errors(self) -> List[Event]:
        """Get all errors.

        Returns:
            List of error events
        """
        return self.filter(event_type=EventType.ERROR)

    def iter_events(self) -> Iterator[Event]:
        """Iterate through all events.

        Yields:
            Events in order
        """
        for event in self.session.events:
            yield event

    def add_breakpoint(self, event_id: int) -> None:
        """Add a breakpoint.

        Args:
            event_id: Event ID to break at
        """
        if event_id not in self._breakpoints:
            self._breakpoints.append(event_id)

    def remove_breakpoint(self, event_id: int) -> None:
        """Remove a breakpoint.

        Args:
            event_id: Event ID to remove breakpoint from
        """
        if event_id in self._breakpoints:
            self._breakpoints.remove(event_id)

    def continue_to_breakpoint(self) -> Optional[Event]:
        """Continue until next breakpoint.

        Returns:
            Event at breakpoint or None if end reached
        """
        while self.has_next():
            event = self.step()
            if event and event.id in self._breakpoints:
                return event
        return None

    def get_summary(self) -> Dict[str, Any]:
        """Get session summary.

        Returns:
            Summary dictionary
        """
        tokens = self.session.get_total_tokens()
        return {
            "session_id": self.session.session_id,
            "started_at": self.session.started_at,
            "ended_at": self.session.ended_at,
            "duration_ms": self.session.duration_ms,
            "total_events": self.session.event_count,
            "llm_calls": len(self.session.llm_calls),
            "tool_calls": len(self.session.tool_calls),
            "errors": len(self.session.errors),
            "total_tokens": tokens,
            "metadata": self.session.metadata
        }

    def diff(self, other: "Replayer") -> Dict[str, Any]:
        """Compare with another session.

        Args:
            other: Another Replayer instance

        Returns:
            Diff result
        """
        self_events = {e.id: e for e in self.session.events}
        other_events = {e.id: e for e in other.session.events}

        # Compare outputs
        self_outputs = [e for e in self.session.events if e.type == EventType.OUTPUT]
        other_outputs = [e for e in other.session.events if e.type == EventType.OUTPUT]

        output_diffs = []
        for i, (s, o) in enumerate(zip(self_outputs, other_outputs)):
            if s.data != o.data:
                output_diffs.append({
                    "index": i,
                    "self": s.data,
                    "other": o.data
                })

        return {
            "self_events": len(self_events),
            "other_events": len(other_events),
            "self_tokens": self.session.get_total_tokens(),
            "other_tokens": other.session.get_total_tokens(),
            "output_diffs": output_diffs,
            "same_outputs": len(output_diffs) == 0
        }
