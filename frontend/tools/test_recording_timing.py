import math
import unittest
from array import array

from recording_timing import RATE, align_transcripts


def recording(caller=(), agent=(), duration=6):
    samples = array("h")
    for i in range(duration * RATE):
        t = i / RATE
        left = 6000 * math.sin(2 * math.pi * 250 * t) if any(a <= t < b for a, b in caller) else 0
        right = 6000 * math.sin(2 * math.pi * 450 * t) if any(a <= t < b for a, b in agent) else 0
        samples.extend((round(left), round(right + left * 0.04)))
    return samples


def transcript(line, role, logged):
    return {"kind": "transcript", "role": role, "text": "Spoken words", "t": 100 + logged, "_line": line}


class RecordingTimingTests(unittest.TestCase):
    def test_late_messages_use_their_own_speech_end_including_the_final_message(self):
        events = [transcript(1, "user", 3.5), transcript(2, "agent", 5)]
        ends = align_transcripts(recording(caller=[(1, 2)], agent=[(3, 4)]), events, 100)
        self.assertEqual(ends, {"1": 2, "2": 4})
        self.assertEqual([e["t"] for e in events], [103.5, 105])

    def test_fragments_published_during_one_utterance_wait_for_its_audio_to_finish(self):
        events = [transcript(1, "agent", 3.5), transcript(2, "agent", 4.3), transcript(3, "agent", 4.6)]
        ends = align_transcripts(recording(agent=[(3, 4)]), events, 100)
        self.assertEqual(ends, {"1": 4, "2": 4, "3": 4})

    def test_pauses_clicks_and_stereo_leakage_do_not_create_later_message_endings(self):
        samples = recording(caller=[(1, 1.4), (1.6, 2), (2.5, 2.56)])
        events = [transcript(1, "user", 3), transcript(2, "agent", 4), transcript(3, "user", 5)]
        self.assertEqual(align_transcripts(samples, events, 100), {"1": 2})


if __name__ == "__main__":
    unittest.main()
