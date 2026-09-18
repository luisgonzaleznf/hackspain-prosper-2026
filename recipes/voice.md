# Recipe: voice (speech-to-text → Claude → text-to-speech)

Claude is text-only, so wrap it: transcribe audio in, synthesize audio out.
Whisper handles STT; ElevenLabs handles TTS. A full voice turn in ~30 lines.

```python
import anthropic

client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY

# --- 1. Speech -> text (local Whisper, no key) ---
# pip install openai-whisper
import whisper
stt = whisper.load_model("base")
user_text = stt.transcribe("user_audio.wav")["text"]
print("heard:", user_text)

# --- 2. Text -> Claude ---
resp = client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=512,
    messages=[{"role": "user", "content": user_text}],
)
reply = "".join(b.text for b in resp.content if b.type == "text")
print("reply:", reply)

# --- 3. Text -> speech (ElevenLabs) ---
# pip install elevenlabs ; export ELEVENLABS_API_KEY=...
from elevenlabs.client import ElevenLabs
from elevenlabs import save
tts = ElevenLabs()  # reads ELEVENLABS_API_KEY
audio = tts.text_to_speech.convert(
    voice_id="JBFqnCBsd6RMkjVDRZzb",   # any ElevenLabs voice id
    model_id="eleven_turbo_v2_5",
    text=reply,
)
save(audio, "reply.mp3")
print("wrote reply.mp3")
```

Notes:
- Lower-latency STT alternatives: OpenAI's hosted `whisper-1`, Deepgram, or
  `faster-whisper` (CTranslate2) for local speedups.
- For a live voice loop, stream Whisper chunks and stream Claude's reply
  (see `streaming-chat.md`) into ElevenLabs streaming TTS to cut latency.
- macOS quick TTS with zero deps: `os.system(f'say "{reply}"')` — good enough for a demo.
- Keep turns short; round-trip latency is the demo killer, not model quality.
