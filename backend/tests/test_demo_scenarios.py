"""Studio role cards read diary facts from the clinic database when they are requested."""

from datetime import datetime, time, timedelta

from app import config
from app.demo.scenarios import get_scenario, list_scenarios

from clinic_fixture import booked, patient, seeded

IGNACIO = patient(
    "P00005",
    given_name="Ignacio",
    first_surname="Vázquez",
    second_surname="Moreno",
    national_id="65699248R",
    phone="731169716",
    insurer="cigna",
)


def test_the_cancellation_card_names_the_appointment_on_file():
    day = datetime.now(config.TZ).date() + timedelta(days=20)
    start = datetime.combine(day, time(12), tzinfo=config.TZ)
    past = start - timedelta(days=60)
    seeded(
        patients=[IGNACIO],
        appointments=[
            booked("A001101", "P00005", "PR05", "sur", start.isoformat(timespec="seconds")),
            booked("A000001", "P00005", "PR05", "sur", past.isoformat(timespec="seconds")),
        ],
    )
    facts = dict(get_scenario("cancellation").facts)
    assert facts["Appointment"] == (
        f"{start:%A} {start.day} {start:%B} at 12:00 with Dra. Elena Iglesias at Arenal Sur"
    )


def test_an_empty_diary_says_to_reseed_instead_of_inventing_one():
    facts = dict(next(s for s in list_scenarios() if s.id == "cancellation").facts)
    assert facts["Appointment"].startswith("None on file")
    assert dict(get_scenario("booking").facts)["DNI/NIE"] == "48064716Y"  # static cards unchanged
