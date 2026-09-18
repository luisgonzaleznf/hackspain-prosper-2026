# Voice stack — day 0 notes

> Status: **decision made** (Sat morning — see [the update at the bottom](#update--sat-morning-going-diy-stt--llm--tts)). Last updated Fri 18 Sep, after reading the challenge + quickstart docs.

## The problem shape

Inbound phone call. Twilio sends us Media Streams over a WebSocket — `connected → start → media → stop`, 8 kHz µ-law, 20 ms frames, base64, camelCase keys. We have to turn that into a conversation and act on the clinic API. That wire format is fixed for everyone; every voice option is really "how do we bridge to it".

(The README says Anthropic-first, but STT → LLM → TTS chained through `lib/ai.py` means three hops of latency per turn, and pace is scored. That's pushing us toward the speech-to-speech realtime models — comparing both anyway.)

## Options on the table

| Option | One-liner | Why it's tempting | Why we hesitate |
|---|---|---|---|
| OpenAI Realtime API | speech-to-speech over WS, native function calling, server VAD | one hop, tools mid-stream | cost per minute vs the €100 card; µ-law handling unclear |
| pipecat | Python voice framework — the organiser quickstart literally points at its Twilio example | shortest path to "it talks" | framework lock-in on a 2-day clock; unclear how much of the wire it hides vs helps |
| LiveKit Agents | agent framework with its own telephony | solid turn-taking story | we'd adopt their stack just to use the Twilio stream we're handed anyway |
| DIY STT → LLM → TTS | Whisper + Claude + TTS, our own bridge | max control, reuses `lib/ai.py` | latency, and we own all the turn-taking pain |

**No decision yet.** Leaning toward spiking the realtime route first, pipecat as the fallback if the wire fight eats too much of Saturday.

## Open questions (must answer before real code)

- [x] Does the Realtime API accept 8 kHz µ-law directly, or resample to 16/24 kHz on the way in and back? — **answered: resample, and it hurts quality**
- [ ] Turn-taking on a phone line: the organiser docs say there's no server-side barge-in and `clear` is a no-op — so is interruption handling entirely on us either way?
- [ ] Function calling mid-utterance: does the model wait for the tool result, and what does the caller hear while it does?
- [x] Real cost per minute of speech + tools, and how far the €100 card actually gets us. — **answered: realtime burns it fast, see the decision below**
- [ ] Latency budget: first audible response after the caller stops talking.

## Update — Sat morning: going DIY STT → LLM → TTS

Slept on it, ran quick numbers, decision made.

**Chosen: Whisper → Claude → TTS, stitched by hand on the Twilio wire.** Models: `whisper-1` → `claude-3-5-sonnet-20241022` → `tts-1`. Spike: [`playground/luis/diy-voice-spike/`](../playground/luis/diy-voice-spike/).

**Why not the realtime API:**

- **Cost.** Audio tokens add up fast — our rough burst test (our setup, numbers not trustworthy, re-measuring) says a full scoring session would eat a scary chunk of the €100 card. The DIY path bills pennies per call.
- **µ-law pain.** The API wants 16/24 kHz PCM; resampling 8 kHz phone audio both ways cost noticeable quality, and that's before any VAD tuning.
- We do lose native function calling, but our tool needs are simple lookups — a plain JSON tool loop on Claude is fine.

**Why not pipecat:** parked. Its Twilio example gets you talking fast, but the abstractions hid exactly the wire-level details (framing, timing, turn-taking) that this challenge grades. On a two-day clock we'd rather own the loop than fight a framework's opinions about it.

**Why not LiveKit:** same — an extra platform to adopt for a stream we're already handed.

Current state of the DIY loop: works end to end, sequential and blocking, ~2 s added per turn. Streaming + interruption handling are the next TODOs.

---

## Original plan (Fri)

1. Hello-world bridge: Twilio frames in → audio out (spike: [`playground/luis/twilio-realtime-spike/`](../playground/luis/twilio-realtime-spike/) — **abandoned**, kept for reference).
2. One fake tool ("book a slot" against a hardcoded list) to see function calling over the same socket.
3. Pick the stack, then move real code into `app/`.
