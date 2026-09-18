# diy-voice-spike

The chosen direction ([`notes/voice-stack.md`](../../../notes/voice-stack.md)): Twilio µ-law → `whisper-1` → `claude-3-5-sonnet` → `tts-1` → µ-law, stitched by hand.

Works end to end but sequential and blocking: whole utterance in, whole reply out, ~2 s added per turn. Next up: streaming STT/TTS, interruption handling.

Run: `OPENAI_API_KEY=... ANTHROPIC_API_KEY=... uv run --with openai,anthropic,websockets python spike.py`
