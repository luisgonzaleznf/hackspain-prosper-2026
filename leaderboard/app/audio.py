"""8 kHz G.711 µ-law helpers for the Twilio Media Streams wire (stdlib only; audioop is gone in 3.13)."""

from __future__ import annotations

import math
import wave
from array import array
from pathlib import Path

RATE = 8000
FRAME_BYTES = 160  # 20 ms of 8 kHz µ-law
SILENCE = b"\xff" * FRAME_BYTES  # µ-law 0xFF decodes to 0
AUDIBLE_RMS = 200  # ~-44 dBFS; below this a frame counts as silence


def _ulaw_to_linear(u: int) -> int:
    u = ~u & 0xFF
    magnitude = ((((u & 0x0F) << 3) + 0x84) << ((u >> 4) & 0x07)) - 0x84
    return -magnitude if u & 0x80 else magnitude


def _linear_to_ulaw(sample: int) -> int:
    sign = 0x80 if sample < 0 else 0
    magnitude = min(abs(sample), 32635) + 0x84
    exponent = 7
    while exponent > 0 and not magnitude & (0x4000 >> (7 - exponent)):
        exponent -= 1
    mantissa = (magnitude >> (exponent + 3)) & 0x0F
    return ~(sign | (exponent << 4) | mantissa) & 0xFF


_DECODE = [_ulaw_to_linear(i) for i in range(256)]


def decode(ulaw: bytes | bytearray) -> array:
    return array("h", (_DECODE[b] for b in ulaw))


def encode(pcm: array) -> bytes:
    return bytes(_linear_to_ulaw(s) for s in pcm)


def pcm_rms(pcm: array) -> float:
    if not pcm:
        return 0.0
    return math.sqrt(sum(sample**2 for sample in pcm) / len(pcm))


def rms(ulaw: bytes) -> float:
    return pcm_rms(decode(ulaw))


def tone(seconds: float, hz: float = 440.0, level: float = 0.3) -> bytes:
    n = int(RATE * seconds)
    return encode(
        array("h", (int(level * 32767 * math.sin(2 * math.pi * hz * i / RATE)) for i in range(n)))
    )


def write_wav(path: Path, pcm: array) -> None:
    with wave.open(str(path), "wb") as out:
        out.setnchannels(1)
        out.setsampwidth(2)
        out.setframerate(RATE)
        out.writeframes(pcm.tobytes())


def mix(a: array, b: array) -> array:
    n = max(len(a), len(b))
    return array(
        "h",
        (
            max(-32768, min(32767, (a[i] if i < len(a) else 0) + (b[i] if i < len(b) else 0)))
            for i in range(n)
        ),
    )
