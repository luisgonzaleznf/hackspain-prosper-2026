# Recipe: tool calling (manual agentic loop)

Minimal multi-step tool loop with the Anthropic SDK. The model asks for a tool,
you run it, you feed the result back, repeat until it stops.

```python
import anthropic

client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY

TOOLS = [{
    "name": "get_weather",
    "description": "Get current weather for a city.",
    "input_schema": {
        "type": "object",
        "properties": {"city": {"type": "string"}},
        "required": ["city"],
    },
}]

def get_weather(city: str) -> str:
    return f"{city}: 72°F and sunny"

def run(user_msg: str, model: str = "claude-sonnet-4-6") -> str:
    messages = [{"role": "user", "content": user_msg}]
    for _ in range(6):  # cap the loop
        resp = client.messages.create(
            model=model, max_tokens=1024, tools=TOOLS, messages=messages
        )
        if resp.stop_reason != "tool_use":
            return "".join(b.text for b in resp.content if b.type == "text")

        # Append the assistant turn VERBATIM (it holds the tool_use blocks).
        messages.append({"role": "assistant", "content": resp.content})

        # Run every tool_use block; return ALL results in ONE user message.
        results = []
        for b in resp.content:
            if b.type == "tool_use":
                out = get_weather(**b.input)          # dispatch on b.name in real code
                results.append({
                    "type": "tool_result",
                    "tool_use_id": b.id,               # must match
                    "content": out,
                })
        messages.append({"role": "user", "content": results})
    return "(hit step cap)"

print(run("What's the weather in Paris?"))
```

Notes:
- Parse `b.input` as the already-decoded dict the SDK gives you — never raw-match the JSON string.
- On a tool failure, return the `tool_result` with `"is_error": True` instead of dropping it.
- Prefer this manual loop when you want logging/approval gates; the SDK's
  `client.beta.messages.tool_runner(...)` automates it.
- See the full runnable version in `templates/agent-app/agent.py`.
