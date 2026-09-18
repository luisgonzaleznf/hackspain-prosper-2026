# Recipe: vision (image input)

Send images to Claude — describe, extract, OCR, or reason over screenshots and
photos. Works inline as content blocks alongside text.

```python
import anthropic, base64, httpx

client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY

# --- Local file (base64) ---
with open("photo.png", "rb") as f:
    data = base64.standard_b64encode(f.read()).decode()

resp = client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=512,
    messages=[{
        "role": "user",
        "content": [
            {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/png",   # png | jpeg | gif | webp
                    "data": data,
                },
            },
            {"type": "text", "text": "What's in this image? List the objects."},
        ],
    }],
)
print("".join(b.text for b in resp.content if b.type == "text"))
```

URL source (no download needed on your side):

```python
resp = client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=512,
    messages=[{
        "role": "user",
        "content": [
            {"type": "image", "source": {"type": "url", "url": "https://example.com/chart.png"}},
            {"type": "text", "text": "Transcribe the data in this chart as a table."},
        ],
    }],
)
```

Notes:
- The base64 string must have **no newlines** (`standard_b64encode` is fine).
- Send multiple images in one turn — just add more `image` blocks; put the text
  block last for best results.
- Great hackathon uses: screenshot → code, receipt → JSON, whiteboard → diagram.
- Combine with structured outputs (`output_config.format`) to get clean JSON back.
