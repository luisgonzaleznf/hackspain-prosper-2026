"""The fallback reads the brain's latest batch of searches, not whichever search finished last.

Found in the first VOICE=gptlive call (simple_booking-3371): the brain fired six searches in
parallel, the last one to finish was an empty filtered variant, and the fallback reported
no_availability for a call that had offered the right slot."""

from app.session import FALLBACK, CallSession


def session_with(*searches: tuple[float, int, list[str]]) -> CallSession:
    s = CallSession(call_id="00000000-0000-0000-0000-0000000000bb")
    s.searches = [{"t": t, "slots_found": n, "blocked": b} for t, n, b in searches]
    return s


def test_parallel_searches_where_one_found_slots_are_not_no_availability():
    s = session_with((37.7, 93, []), (38.2, 12, []), (38.4, 0, []))
    assert s.fallback() == FALLBACK


def test_an_earlier_offer_does_not_mask_a_later_empty_batch():
    # no_slot_free-af9a: the first search offered a morning slot, the caller wanted afternoons,
    # and every afternoon search came back empty: that is no_availability.
    s = session_with((40.0, 64, []), (77.0, 0, []), (81.0, 0, []))
    assert s.fallback() == {"action": "NO_ACTION", "reason": "no_availability"}


def test_one_rule_blocking_every_search_in_the_batch_is_the_reason():
    s = session_with((30.0, 0, ["specialty_not_covered"]), (31.0, 0, ["specialty_not_covered"]))
    assert s.fallback() == {"action": "NO_ACTION", "reason": "specialty_not_covered"}


def test_different_rules_in_the_batch_stay_out_of_scope():
    s = session_with((30.0, 0, ["provider_on_leave"]), (31.0, 0, ["location_hours"]))
    assert s.fallback() == FALLBACK


def test_no_search_keeps_the_old_fallback():
    assert session_with().fallback() == FALLBACK
