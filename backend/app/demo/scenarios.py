from app import appointment_email
from app.demo.models import DemoPersona

_SCENARIOS = (
    DemoPersona(
        id="new_patient",
        title="Register and book a first visit",
        name="Prueba Sistema Temporal",
        phone="699887766",
        facts=[
            (
                "Registration",
                "Only your name and surnames; the rest is done at reception on arrival",
            ),
            ("Email", "qa@example.test, only if asked, for the confirmation"),
        ],
        objective="Register with just your name and book a General Practice appointment. On later calls, use the saved profile: your name and this phone number.",
        opening_hint="I would like to register and book my first General Practice visit.",
        expected_outcome="BOOK",
    ),
    DemoPersona(
        id="account",
        title="Create your customer account",
        name="You",
        phone="",
        facts=[
            ("Your details", "Use your name and the personal inbox you want to receive the email.")
        ],
        objective="Create a local demo customer account and receive a welcome email after hanging up.",
        opening_hint="I'd like to create a customer account.",
        expected_outcome="REGISTER",
    ),
    DemoPersona(
        id="booking",
        title="Book the earliest GP visit",
        name="Josefa Domínguez Navarro",
        phone="711330529",
        facts=[
            ("Date of birth", "19 September 2001"),
            ("DNI/NIE", "48064716Y"),
            ("Insurance", "Mapfre Salud"),
            ("Reason", "High blood-pressure readings at the pharmacy"),
        ],
        objective="Book the earliest available General Practice appointment.",
        opening_hint="I need the earliest General Practice appointment you have.",
        expected_outcome="BOOK",
    ),
    DemoPersona(
        id="cancellation",
        title="Cancel an existing appointment",
        name="Ignacio Vázquez Moreno",
        phone="731169716",
        facts=[
            ("Date of birth", "9 December 1939"),
            ("DNI/NIE", "65699248R"),
            ("Insurance", "Cigna"),
            (
                "Appointment",
                "Tuesday 13 October at 12:00 with Dra. Elena Iglesias at Arenal Sur",
            ),
        ],
        objective="Cancel the one appointment on file because of a family commitment.",
        opening_hint="I need to cancel my appointment, please.",
        expected_outcome="CANCEL",
    ),
    DemoPersona(
        id="emergency",
        title="Get urgent guidance",
        name="Lucas Jones Smith",
        phone="757036760",
        facts=[
            ("Date of birth", "4 April 1980"),
            ("DNI/NIE", "Z5361712A"),
            ("Insurance", "Sanitas"),
            ("Symptoms", "Tight chest pain and struggling to catch breath"),
            ("Timing", "Started about twenty minutes ago and is not easing"),
        ],
        objective="Describe the symptoms and follow the urgent guidance given; do not request an appointment.",
        opening_hint="I have a tight pain across my chest and I am struggling to catch my breath.",
        expected_outcome="ESCALATE",
    ),
)


def list_scenarios() -> list[DemoPersona]:
    return [
        scenario
        for scenario in _SCENARIOS
        if scenario.id != "account" or appointment_email.enabled()
    ]


def get_scenario(scenario_id: str) -> DemoPersona | None:
    return next((scenario for scenario in list_scenarios() if scenario.id == scenario_id), None)
