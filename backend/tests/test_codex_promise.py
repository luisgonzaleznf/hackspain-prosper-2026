"""The codex brain's 'promise' detector: a turn that only promises work must be continued."""

import pytest
from app.voice.codex.peer import is_promise


@pytest.mark.parametrize(
    "text",
    [
        # verbatim brain turns that ended a call in silence (practice call 57ad8746, sim runs)
        "One moment while I check Dr. Ortiz Vidal’s next appointments.",  # noqa: RUF001 (verbatim)
        "Thanks, checking that now.",
        "Perfecto, voy a buscar la primera cita disponible para ginecología.",
        "Let me check the availability for that site and time",
        "Un momento, por favor, lo estoy mirando.",
    ],
)
def test_promises_are_detected(text: str) -> None:
    assert is_promise(text)


@pytest.mark.parametrize(
    "text",
    [
        "The earliest is Monday 21 September at 9:30 with Dr. Peral at Arenal Sur. Does that suit?",
        "I've booked Monday 21 September at 9:30 with Dr. Peral at Arenal Sur.",
        "Could you give me your date of birth, please?",
        "We don't have any free slots with that doctor in the next two weeks.",
        "Un momento: ¿la cita es para usted o para su hijo?",
        "",
    ],
)
def test_answers_and_questions_are_not_promises(text: str) -> None:
    assert not is_promise(text)
