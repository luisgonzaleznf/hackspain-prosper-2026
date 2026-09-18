# Recipe: streaming chat

Stream tokens as they arrive — essential for a responsive chat UI and to dodge
HTTP timeouts on long replies.

```python
import anthropic

client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY

with client.messages.stream(
    model="claude-sonnet-4-6",
    max_tokens=1024,
    messages=[{"role": "user", "content": "Write a haiku about hackathons."}],
) as stream:
    for text in stream.text_stream:        # just the text deltas
        print(text, end="", flush=True)

    final = stream.get_final_message()     # full Message after the stream ends
    print(f"\n\n[tokens: {final.usage.output_tokens}]")
```

Stream from a FastAPI endpoint with SSE:

```python
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
import anthropic

app = FastAPI()
client = anthropic.Anthropic()

@app.get("/stream")
def stream(q: str):
    def gen():
        with client.messages.stream(
            model="claude-sonnet-4-6", max_tokens=1024,
            messages=[{"role": "user", "content": q}],
        ) as s:
            for text in s.text_stream:
                yield f"data: {text}\n\n"      # SSE frame
    return StreamingResponse(gen(), media_type="text/event-stream")
```

Notes:
- Use `messages.stream(...)` (the helper) over `messages.create(stream=True)` —
  it accumulates state and gives you `text_stream` + `get_final_message()`.
- For thinking models, also handle `thinking_delta` events; see the SDK streaming docs.
- Client side: read the SSE stream with `EventSource` or `fetch` + a `ReadableStream` reader.
