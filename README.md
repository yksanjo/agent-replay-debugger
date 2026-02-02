# Agent Replay Debugger

Record, replay, and debug AI agent sessions with full state inspection.

## Features

- **Session Recording**: Capture every API call, response, and state change
- **Replay Mode**: Re-execute sessions step-by-step or all at once
- **State Inspection**: View agent state at any point in time
- **Diff View**: Compare expected vs actual outputs
- **Time Travel**: Jump to any point in the session
- **Export**: Share sessions as JSON for debugging

## Quick Start

```bash
pip install agent-replay-debugger
```

```python
from agent_replay_debugger import Recorder, Replayer

# Record a session
recorder = Recorder(session_id="debug-001")

with recorder.capture():
    # Your agent code runs here
    response = agent.run("Analyze this document...")

# Save the recording
recorder.save("session-001.json")
```

## Recording

```python
from agent_replay_debugger import Recorder

recorder = Recorder()

# Record individual events
recorder.record_input("user", "What is the weather?")
recorder.record_llm_call(
    model="gpt-4",
    prompt="...",
    response="...",
    tokens={"input": 100, "output": 50}
)
recorder.record_tool_call(
    tool="weather_api",
    args={"city": "Tokyo"},
    result={"temp": 22, "condition": "sunny"}
)
recorder.record_output("agent", "The weather in Tokyo is 22C and sunny")

# Get full timeline
timeline = recorder.get_timeline()
```

## Replay

```python
from agent_replay_debugger import Replayer

replayer = Replayer.from_file("session-001.json")

# Step through events
while replayer.has_next():
    event = replayer.step()
    print(f"[{event.timestamp}] {event.type}: {event.summary}")

# Jump to specific event
replayer.goto(event_id=5)

# Get state at current position
state = replayer.get_state()
```

## CLI

```bash
# Replay a session interactively
agent-replay play session-001.json

# Show session summary
agent-replay info session-001.json

# Export to HTML report
agent-replay export session-001.json --format html --output report.html

# Compare two sessions
agent-replay diff session-001.json session-002.json
```

## Web UI

```bash
# Start the debug UI
agent-replay serve

# Opens at http://localhost:8800
```

Features:
- Timeline visualization
- State inspector
- LLM call viewer with token highlighting
- Tool execution traces
- Side-by-side diff mode

## Integration

### OpenAI

```python
from agent_replay_debugger.integrations import patch_openai

recorder = Recorder()
patch_openai(recorder)

# All OpenAI calls are now recorded
response = openai.chat.completions.create(...)
```

### LangChain

```python
from agent_replay_debugger.integrations import LangChainCallback

recorder = Recorder()
callback = LangChainCallback(recorder)

agent.run("...", callbacks=[callback])
```

### Anthropic

```python
from agent_replay_debugger.integrations import patch_anthropic

recorder = Recorder()
patch_anthropic(recorder)

# All Anthropic calls are now recorded
response = anthropic.messages.create(...)
```

## Event Types

| Type | Description |
|------|-------------|
| `input` | User or system input |
| `output` | Agent response |
| `llm_call` | LLM API call with prompt/response |
| `tool_call` | Tool/function execution |
| `state_change` | Agent state modification |
| `error` | Exception or error |
| `log` | Debug log message |

## Session Format

```json
{
  "session_id": "debug-001",
  "started_at": "2024-01-15T10:30:00Z",
  "ended_at": "2024-01-15T10:30:45Z",
  "events": [
    {
      "id": 1,
      "timestamp": "2024-01-15T10:30:00Z",
      "type": "input",
      "data": {"role": "user", "content": "What is 2+2?"}
    },
    {
      "id": 2,
      "timestamp": "2024-01-15T10:30:01Z",
      "type": "llm_call",
      "data": {
        "model": "gpt-4",
        "prompt": "...",
        "response": "4",
        "tokens": {"input": 50, "output": 1}
      }
    }
  ],
  "metadata": {
    "agent": "math-assistant",
    "version": "1.0.0"
  }
}
```

## License

MIT
