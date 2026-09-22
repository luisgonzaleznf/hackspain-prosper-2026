"""Generate clearly marked synthetic call logs for the metrics demo.

    python scripts/seed_metrics_demo.py /tmp/metrics-history --days 14

Writes only new demo-metrics-*.jsonl files; existing files are never overwritten.
All calls end before today in Europe/Madrid. No API, voice service, clinic database,
or email service is contacted. Copy the generated files into CALLS_DIR to publish.
Remove those exact files to undo the seed. No audio recordings are fabricated.
"""

import argparse
import json
import os
import random
from collections import Counter
from datetime import date, datetime, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

MADRID = ZoneInfo("Europe/Madrid")
DATASET = "rosario-metrics-demo-v1"
GIVEN_NAMES = (
    "Lucía",
    "María",
    "Carmen",
    "Ana",
    "Isabel",
    "Elena",
    "Marta",
    "Paula",
    "Laura",
    "Nuria",
    "Carlos",
    "Javier",
    "Pablo",
    "Miguel",
    "David",
    "Antonio",
    "Manuel",
    "Sergio",
    "Daniel",
    "José",
    "Teresa",
    "Rosa",
    "Alba",
    "Irene",
)
SURNAMES = (
    "García",
    "Martínez",
    "López",
    "Sánchez",
    "Pérez",
    "Fernández",
    "Ruiz",
    "Romero",
    "Navarro",
    "Torres",
    "Vega",
    "Molina",
    "Serrano",
    "Ortega",
    "Moreno",
    "Delgado",
    "Castro",
    "Santos",
    "Gil",
    "Ramos",
    "Soler",
    "Vidal",
)
REQUESTS = {
    "BOOK": "Quería pedir una cita de medicina general para la próxima semana.",
    "RESCHEDULE": "Tengo una cita, pero necesito cambiarla a otro día.",
    "CANCEL": "Necesito cancelar mi próxima cita, por favor.",
    "NO_ACTION": "¿Tienen alguna cita libre con mi médico esta semana?",
    "ESCALATE": "Tengo una consulta que me gustaría comentar con el médico.",
}
REPLIES = {
    "BOOK": "He encontrado un hueco que encaja con su disponibilidad. ¿Lo confirmamos?",
    "RESCHEDULE": "Hay un nuevo horario disponible. ¿Confirmo el cambio?",
    "CANCEL": "He localizado su próxima cita. ¿Confirma que quiere cancelarla?",
    "NO_ACTION": "No quedan huecos con ese médico esta semana. Podemos buscar otra fecha.",
    "ESCALATE": "Voy a derivar su consulta al equipo médico para que puedan ayudarle.",
}
CLOSINGS = {
    "BOOK": "Su cita ha quedado confirmada. Gracias por llamar a Clínica Arenal.",
    "RESCHEDULE": "El cambio de cita ha quedado confirmado. Gracias por llamar.",
    "CANCEL": "Su cita ha quedado cancelada. Gracias por avisarnos.",
    "NO_ACTION": "De acuerdo, no he cambiado ninguna cita. Gracias por llamar.",
    "ESCALATE": "He dejado registrada la solicitud para el equipo médico. Gracias por llamar.",
}


def calls_for_day(day: date) -> list[tuple[str, list[dict]]]:
    rng = random.Random(f"{DATASET}:{day.isoformat()}")
    count = max(4, (46, 39, 35, 38, 29, 12, 6)[day.weekday()] + rng.randint(-4, 6))
    calls = []
    for index in range(count):
        call_id = f"demo-metrics-{day:%Y%m%d}-{index + 1:03d}"
        verb = rng.choices(list(REQUESTS), weights=[62, 15, 9, 9, 5])[0]
        name = f"{rng.choice(GIVEN_NAMES)} {rng.choice(SURNAMES)} {rng.choice(SURNAMES)}"
        patient_id = f"DEMO-P-{day:%Y%m%d}-{index + 1:03d}"
        # A morning peak, an afternoon peak, and a lighter lunch period.
        hour = rng.choices([9, 10, 11, 12, 13, 15, 16, 17, 18], [14, 20, 17, 10, 4, 8, 12, 10, 5])[
            0
        ]
        if day.weekday() >= 5:
            hour = rng.choice([9, 10, 11, 12])
        started = datetime.combine(day, time(hour, rng.randrange(60), rng.randrange(60)), MADRID)
        typical = {"BOOK": 166, "RESCHEDULE": 204, "CANCEL": 89, "NO_ACTION": 136, "ESCALATE": 111}[
            verb
        ]
        duration = round(max(48, min(390, rng.gauss(typical, typical * 0.24))), 2)
        slot_day = day + timedelta(days=rng.randint(2, 9))
        while slot_day.weekday() >= 5:
            slot_day += timedelta(days=1)
        slot = datetime.combine(
            slot_day, time(rng.choice([9, 10, 11, 12, 16, 17]), rng.choice([0, 20, 40])), MADRID
        ).isoformat()
        action = {"action": verb, "patient_id": patient_id}
        if verb in {"BOOK", "RESCHEDULE", "CANCEL"}:
            action.update(
                {
                    "appointment_id": f"DEMO-APT-{day:%Y%m%d}-{index + 1:03d}",
                    "provider_id": rng.choice(["DEMO-PR01", "DEMO-PR02", "DEMO-PR03"]),
                    "location_id": rng.choice(["centro", "centro", "norte", "sur"]),
                    "appointment_type_id": "general_practice",
                    "slot": slot,
                }
            )
        elif verb == "NO_ACTION":
            action["reason"] = "no_availability"
        else:
            action["reason"] = "out_of_scope"

        events = []

        def event(
            fraction: float,
            kind: str,
            *,
            _events=events,
            _started=started,
            _duration=duration,
            **payload,
        ) -> None:
            _events.append(
                {
                    "t": round(_started.timestamp() + fraction * _duration, 3),
                    "kind": kind,
                    "synthetic": True,
                    "dataset": DATASET,
                    **payload,
                }
            )

        event(
            0,
            "call_started",
            call_id=call_id,
            from_number=f"+3400000{index + 1:04d}",
            source="synthetic_demo",
        )
        event(
            0.01,
            "transcript",
            role="agent",
            text="Clínica Arenal, soy Rosario. ¿En qué puedo ayudarle?",
        )
        event(0.09, "transcript", role="user", text=f"Buenos días, soy {name}. {REQUESTS[verb]}")
        event(
            0.16, "transcript", role="agent", text="Voy a comprobar sus datos antes de continuar."
        )
        event(
            0.25,
            "tool",
            name="find_patient",
            args={"name": name},
            result={
                "count": 1,
                "matches": [
                    {"patient_id": patient_id, "name": name, "note": "Synthetic demo patient"}
                ],
            },
        )
        event(0.31, "transcript", role="user", text="Sí, esos son mis datos.")
        event(0.34, "identity_verified", patient_id=patient_id, source="synthetic_demo")
        if verb in {"BOOK", "RESCHEDULE", "NO_ACTION"}:
            slots = (
                []
                if verb == "NO_ACTION"
                else [
                    {
                        key: value
                        for key, value in action.items()
                        if key in {"slot", "provider_id", "location_id", "appointment_type_id"}
                    }
                ]
            )
            event(
                0.43,
                "tool",
                name="search_availability",
                args={"patient_id": patient_id},
                result={"earliest_slots": slots},
            )
        elif verb == "CANCEL":
            event(
                0.43,
                "tool",
                name="list_appointments",
                args={"patient_id": patient_id},
                result={"appointments": [action]},
            )
        event(0.53, "transcript", role="agent", text=REPLIES[verb])
        event(
            0.67,
            "transcript",
            role="user",
            text="No, gracias. Volveré a llamar otro día."
            if verb == "NO_ACTION"
            else "Sí, de acuerdo. Muchas gracias.",
        )
        event(0.77, "action_staged", action=action, all_staged=[action])
        event(
            0.85,
            "submit",
            action=action,
            status=200,
            response={
                "ok": True,
                "synthetic": True,
                "note": "Demo report only; no API request or clinic write occurred.",
            },
        )
        event(0.93, "transcript", role="agent", text=CLOSINGS[verb])
        event(
            0.99,
            "audio.timeline",
            turns={"responses": 4, "latency_p50_s": round(rng.triangular(0.65, 3.1, 1.25), 3)},
            caller={"talk_s": round(duration * rng.uniform(0.27, 0.36), 2)},
            agent={"talk_s": round(duration * rng.uniform(0.38, 0.49), 2)},
        )
        event(1, "call_ended", submitted=[200])
        calls.append((call_id, events))
    return calls


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output_dir", type=Path)
    parser.add_argument("--days", type=int, default=14)
    parser.add_argument(
        "--ending", type=date.fromisoformat, default=datetime.now(MADRID).date() - timedelta(days=1)
    )
    args = parser.parse_args()
    if args.days < 1 or args.ending >= datetime.now(MADRID).date():
        parser.error("Use at least one day, ending before today in Europe/Madrid.")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    counts, outcomes = Counter(), Counter()
    created = skipped = 0
    for offset in range(args.days - 1, -1, -1):
        day = args.ending - timedelta(days=offset)
        for call_id, events in calls_for_day(day):
            path = args.output_dir / f"{call_id}.jsonl"
            try:
                with path.open("x", encoding="utf-8") as handle:
                    handle.write(
                        "".join(json.dumps(event, ensure_ascii=False) + "\n" for event in events)
                    )
                ended = events[-1]["t"]
                os.utime(path, (ended, ended))
                created += 1
            except FileExistsError:
                skipped += 1
            counts[day.isoformat()] += 1
            outcomes[
                next(event["action"]["action"] for event in events if event["kind"] == "submit")
            ] += 1
    print(
        json.dumps(
            {
                "dataset": DATASET,
                "created": created,
                "skipped_existing": skipped,
                "days": counts,
                "outcomes": outcomes,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
