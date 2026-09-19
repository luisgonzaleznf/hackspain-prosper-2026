# Role-play Studio

Run `make roleplay-demo` and open <http://127.0.0.1:7860/demo/> in a browser with a microphone.
Choose a role, allow microphone access, and use the facts on its card. You can interrupt,
change your mind, change language, or ask something outside the clinic's remit.
End the call with the microphone button, then open **Review call** under **Saved rehearsals**.

The studio calls the same `app.voice.codex.run_call`, `CallSession`, prompt, and validated
clinic tools used by the scored server. Its base is serving commit `571b7db` (PR #69),
merged into studio commit `ad3e80f`. The brain is `gpt-5.6-luna`, low effort, with the
Codex subscription voice connection. The studio branch also contains its existing voice
reconnection recovery. It does not call `CallSession.finish()` or submit to Prosper.
The rehearsal also adds clinic-only scope instructions to the shared voice and back-office
prompts: unrelated tasks are redirected, while ordinary clinic questions remain supported.
These prompt changes are locally rehearsed; they have not been scored on the leaderboard.

Prerequisites: `uv sync --frozen`, `codex login` with voice access, and `PLATFORM_API_KEY`
in the ignored `.env`. The existing local `PROSPER_API` credential can be assigned to
`PLATFORM_API_KEY`; never commit its value. The server binds only to `127.0.0.1` and
needs no public tunnel or change to the team's scoring endpoint.

Every rehearsal saves:

- `logs/calls/<call_id>.jsonl`: transcript, exact tool inputs/results, voice events,
  staged actions, recording status, and call end.
- `logs/audio/<call_id>.wav`: 24 kHz stereo, caller left and agent right.
- `logs/audio/<call_id>.timing.json`: audio frame timing.
- `logs/demo/actions.jsonl`: completed and failed calls, including calls with no action.

`/demo/review.html?call=<call_id>` plays the recording and shows the transcript and
expandable tool details. The full JSONL is downloadable there. Audio finalizes after
hang-up; a live review can be refreshed after the call ends. Recordings and the local
history survive a server restart; the live in-memory session snapshot does not.

These are synthetic clinic records. The role cards are starting points, not scripts
the agent sees. Audio, transcripts, and identifiers stay in this local/private setup.
For a failure review, share the call ID and what you expected to happen.
