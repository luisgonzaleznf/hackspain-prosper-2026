from app.prompt import RULES


def _registration_rules() -> str:
    return RULES.split("- A caller who is not on file and wants to be registered:", 1)[1].split(
        "- If the caller changes their mind", 1
    )[0]


def test_registration_questions_are_grouped_in_the_required_order():
    rules = _registration_rules()
    groups = [
        "full name with both surnames and date of birth",
        "DNI/NIE with its letter alone",
        'phone number and "which insurer do you have, or are you paying privately?"',
        "email,\n  spelled out",
    ]
    positions = [rules.index(group) for group in groups]
    assert positions == sorted(positions)
    assert "skip fields already given" in rules
    assert "do not ask again what they need" in rules


def test_registration_records_before_readback_and_replaces_corrections():
    rules = _registration_rules()
    assert "call record_registration immediately" in rules
    assert "before any read-back" in rules
    assert "second call replaces the first staged REGISTER" in rules
    assert "never invent or default an insurer" in rules


def test_registration_retries_only_once_and_splits_dni_retry():
    rules = _registration_rules()
    assert "retry that field only once" in rules
    assert '"the first four digits"' in rules
    assert '"the last four digits and the letter"' in rules
    assert "repeat the same digit-by-digit request" in rules
    assert "re-confirm a field that already" in rules
    assert "validated" in rules
