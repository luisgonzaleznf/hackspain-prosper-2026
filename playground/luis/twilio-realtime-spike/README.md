# twilio-realtime-spike

Day-0 spike from the voice-stack research ([`notes/voice-stack.md`](../../../notes/voice-stack.md)). **Not the real agent** — this is just proving audio round-trips through the Realtime API over the Twilio Media Streams wire.

Known-missing (all TODOs in the code): tools/function calling, VAD tuning, barge-in, µ-law resampling, session bookkeeping, errors. If it plays a sound back, the spike did its job and the real build starts fresh in `app/`.
