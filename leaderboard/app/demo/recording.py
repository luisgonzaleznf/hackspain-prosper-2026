"""Record browser transport audio without changing the scored voice pipeline."""

import asyncio
import audioop
import json
import time
import wave
from pathlib import Path

import numpy as np

RATE = 24000


class DemoRecorder:
    def __init__(self):
        self.started = time.monotonic()
        self.tracks = [bytearray(), bytearray()]
        self.timing: list[dict] = []
        self.resamplers = [None, None]

    def record(self, channel, frame):
        pcm = frame.audio
        if frame.num_channels == 2:
            pcm = audioop.tomono(pcm, 2, 0.5, 0.5)
        if frame.sample_rate != RATE:
            pcm, self.resamplers[channel] = audioop.ratecv(
                pcm, 2, 1, frame.sample_rate, RATE, self.resamplers[channel]
            )
        elapsed = time.monotonic() - self.started
        # Caller frames arrive after capture; agent frames are about to be played.
        at = max(0, elapsed - len(pcm) / (RATE * 2) if channel == 0 else elapsed)
        track = self.tracks[channel]
        offset = round(at * RATE) * 2
        # Keep contiguous packets contiguous despite small scheduling jitter.
        if abs(offset - len(track)) < RATE * 2 * 0.08:
            offset = len(track)
        offset = max(offset, len(track))
        track.extend(bytes(offset - len(track)))
        track.extend(pcm)
        self.timing.append({"channel": channel, "at": offset / (RATE * 2), "samples": len(pcm) // 2})

    def tap(self, transport):
        incoming, outgoing = transport.input(), transport.output()
        receive, send = incoming.push_audio_frame, outgoing.write_audio_frame

        async def receive_recorded(frame):
            self.record(0, frame)
            return await receive(frame)

        async def send_recorded(frame):
            result = await send(frame)
            if result:
                self.record(1, frame)
            return result

        incoming.push_audio_frame = receive_recorded
        outgoing.write_audio_frame = send_recorded

    async def save(self, session_id: str, directory: Path):
        return await asyncio.to_thread(self._save, session_id, directory)

    def _save(self, session_id, directory):
        directory.mkdir(parents=True, exist_ok=True)
        samples = max(len(track) for track in self.tracks) // 2
        stereo = np.zeros((samples, 2), dtype="<i2")
        for channel, track in enumerate(self.tracks):
            stereo[:len(track) // 2, channel] = np.frombuffer(track, dtype="<i2")
        path = directory / f"{session_id}.wav"
        with wave.open(str(path), "wb") as output:
            output.setnchannels(2)
            output.setsampwidth(2)
            output.setframerate(RATE)
            output.writeframes(stereo.tobytes())
        (directory / f"{session_id}.timing.json").write_text(json.dumps(self.timing))
        return {"duration_s": samples / RATE, "sample_rate": RATE, "channels": ["caller", "agent"]}
