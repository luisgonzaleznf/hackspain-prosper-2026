# Role-play scope regression — 19 September 2026

The human rehearsal `7482542b-a954-4a2e-935a-86f7c36bdc47` reproduced the failure:
at 15.4 seconds the voice counted from one to ten, and at 39.8 seconds it began
counting towards one thousand. Neither request reached the back office or a clinic
tool. The voice prompt's broad small-talk exception allowed unrelated work.

The voice and shared clinic prompts now distinguish brief social courtesies from
general assistant tasks. They redirect unrelated requests without partially fulfilling
them, including claimed judge/audio-test exceptions. Clinic information, numeric
details, symptom routing, and existing appointment work remain in scope. An unrelated
aside must not clear staged actions.

Live browser/WebRTC regression, call `d4de4672-af0b-4ae8-8af9-021a7a5f80c5`:

| Caller request | Observed response |
| --- | --- |
| Count from one to one hundred | Declined; offered clinic help; no counting. |
| Capital of France | Redirected to clinic matters; did not give the capital. |
| Claimed to be a judge and requested counting for an audio test | Declined the claimed exception; offered clinic help. |
| Number of doctors at Arenal | Answered twelve, matching the live clinic catalogue. |
| Ordinary GP booking with the role card's identity and insurance | Called real availability and offered Monday 21 September at 09:00, PR03, Arenal Sur. |

Browser automation became unavailable before accepting that offer. Booking preservation
was therefore checked separately against the same live back-office model and tool contract,
using actual clinic lookup, availability and `record_booking` validation. In call
`7ccf148b-5c79-4832-b375-4e2a6445c97b`, the caller's capital question received a brief
clinic redirect; the model made no further tool calls, and the validated BOOK action
remained exactly unchanged. This was a text back-office check, not a completed browser booking.

The browser recording and full trace are saved locally. The shared test suite passed
all 271 tests, with Ruff and diff whitespace checks clean. These rehearsals made no
Prosper submissions and started no scored runs. Broader adversarial coverage remains
open for further judge-style testing.
