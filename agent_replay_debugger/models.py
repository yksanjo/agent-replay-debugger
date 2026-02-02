"""Data models for replay debugger."""

from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any, List


class EventType(Enum):
    """Types of events that can be recorded."""
    INPUT = "input"
    OUTPUT = "output"
    LLM_CALL = "llm_call"
    TOOL_CALL = "tool_call"
    STATE_CHANGE = "state_change"
    ERROR = "error"
    LOG = "log"
    CUSTOM = "custom"


@dataclass
class Event:
    """A single recorded event."""
    id: int
    timestamp: str
    type: EventType
    data: Dict[str, Any]
    duration_ms: Optional[float] = None
    parent_id: Optional[int] = None  # For nested events
    tags: List[str] = field(default_factory=list)

    @property
    def summary(self) -> str:
        """Get a short summary of the event."""
        if self.type == EventType.INPUT:
            content = self.data.get("content", "")
            return f"Input: {content[:50]}..." if len(content) > 50 else f"Input: {content}"
        elif self.type == EventType.OUTPUT:
            content = self.data.get("content", "")
            return f"Output: {content[:50]}..." if len(content) > 50 else f"Output: {content}"
        elif self.type == EventType.LLM_CALL:
            model = self.data.get("model", "unknown")
            tokens = self.data.get("tokens", {})
            return f"LLM ({model}): {tokens.get('input', 0)} in / {tokens.get('output', 0)} out"
        elif self.type == EventType.TOOL_CALL:
            tool = self.data.get("tool", "unknown")
            return f"Tool: {tool}"
        elif self.type == EventType.ERROR:
            error = self.data.get("error", "unknown")
            return f"Error: {error}"
        elif self.type == EventType.STATE_CHANGE:
            key = self.data.get("key", "unknown")
            return f"State: {key} changed"
        else:
            return f"{self.type.value}"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "timestamp": self.timestamp,
            "type": self.type.value,
            "data": self.data,
            "duration_ms": self.duration_ms,
            "parent_id": self.parent_id,
            "tags": self.tags
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Event":
        return cls(
            id=data["id"],
            timestamp=data["timestamp"],
            type=EventType(data["type"]),
            data=data["data"],
            duration_ms=data.get("duration_ms"),
            parent_id=data.get("parent_id"),
            tags=data.get("tags", [])
        )


@dataclass
class Session:
    """A complete recorded session."""
    session_id: str
    started_at: str
    ended_at: Optional[str] = None
    events: List[Event] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    state_snapshots: Dict[int, Dict[str, Any]] = field(default_factory=dict)  # event_id -> state

    @property
    def duration_ms(self) -> Optional[float]:
        """Get total session duration."""
        if not self.ended_at or not self.started_at:
            return None
        start = datetime.fromisoformat(self.started_at.replace("Z", "+00:00"))
        end = datetime.fromisoformat(self.ended_at.replace("Z", "+00:00"))
        return (end - start).total_seconds() * 1000

    @property
    def event_count(self) -> int:
        return len(self.events)

    @property
    def llm_calls(self) -> List[Event]:
        return [e for e in self.events if e.type == EventType.LLM_CALL]

    @property
    def tool_calls(self) -> List[Event]:
        return [e for e in self.events if e.type == EventType.TOOL_CALL]

    @property
    def errors(self) -> List[Event]:
        return [e for e in self.events if e.type == EventType.ERROR]

    def get_total_tokens(self) -> Dict[str, int]:
        """Get total token counts."""
        total_input = 0
        total_output = 0
        for event in self.llm_calls:
            tokens = event.data.get("tokens", {})
            total_input += tokens.get("input", 0)
            total_output += tokens.get("output", 0)
        return {"input": total_input, "output": total_output, "total": total_input + total_output}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "events": [e.to_dict() for e in self.events],
            "metadata": self.metadata,
            "state_snapshots": {str(k): v for k, v in self.state_snapshots.items()}
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Session":
        return cls(
            session_id=data["session_id"],
            started_at=data["started_at"],
            ended_at=data.get("ended_at"),
            events=[Event.from_dict(e) for e in data.get("events", [])],
            metadata=data.get("metadata", {}),
            state_snapshots={int(k): v for k, v in data.get("state_snapshots", {}).items()}
        )
