"""Build small clinic databases for tests: the real catalogue plus hand-placed rows.

store = seeded(patients=[patient("P1")], appointments=[booked("A1", "P1", "PR03", ...)])
"""

import json
from pathlib import Path

from integrations.local_store import LocalStore, columns, full_name

CATALOGUE = json.loads((Path(__file__).resolve().parents[1] / "seed/catalogue.json").read_text())
TYPES = {t["id"]: t for t in CATALOGUE["appointment_types"]}
PROVIDERS = {p["id"]: p for p in CATALOGUE["providers"]}


def patient(patient_id: str, **fields) -> dict:
    """A complete chart; every key the tools and the engine read is present."""
    return {
        "patient_id": patient_id,
        "given_name": "Marta",
        "first_surname": "Ruiz",
        "second_surname": "Gómez",
        "national_id": "00000000T",
        "date_of_birth": "1980-05-05",
        "phone": "600000001",
        "sex": "F",
        "has_visited_before": True,
        "insurer": "sanitas",
        "referrals": [],
        "note": "",
        "email": "",
        "source": "seed",
        "insurer_authorizations": [],
        "allowance_used": {},
        **fields,
    }


def booked(
    appointment_id: str,
    patient_id: str,
    provider_id: str,
    location_id: str,
    start_time: str,
    appointment_type_id: str = "review",
    status: str = "booked",
    **extra,
) -> dict:
    """A diary row as the seed writes it: slot fields plus the seed's bookkeeping."""
    kind = TYPES[appointment_type_id]
    provider = PROVIDERS[provider_id]
    return {
        "provider_id": provider_id,
        "provider_name": provider["name"],
        "specialty_id": provider["specialty_id"],
        "location_id": location_id,
        "appointment_type_id": appointment_type_id,
        "start_time": start_time,
        "duration_minutes": kind["duration_minutes"],
        "payable_with": ["sanitas"],
        "appointment_id": appointment_id,
        "patient_id": patient_id,
        "policy_id": "sanitas",
        "patient_name": "",
        "source": "seed",
        "call_id": None,
        "updated_at": 1.0,
        "status": status,
        **extra,
    }


def seeded(
    *,
    horizon_end: str = "2026-10-18",
    patients=(),
    appointments=(),
    absences=(),
    closures=(),
    catalogue: dict | None = None,
    store: LocalStore | None = None,
) -> LocalStore:
    """Write the catalogue, the horizon and the given rows into the test's clinic database.

    absences: (provider_id, start_date, end_date, start_time, end_time, reason)
    closures: (date, location_id | None, name)
    """
    store = store or LocalStore()
    names = {p["patient_id"]: full_name(p) for p in patients}
    with store.connect() as db:
        db.execute(
            "INSERT OR REPLACE INTO meta VALUES ('catalogue', ?)",
            (json.dumps(catalogue or CATALOGUE),),
        )
        db.execute("INSERT OR REPLACE INTO meta VALUES ('horizon_end', ?)", (horizon_end,))
        for p in patients:
            db.execute(
                "INSERT INTO patients VALUES (?, ?, ?)",
                (p["patient_id"], p["national_id"], json.dumps(p)),
            )
        for a in appointments:
            data = {k: v for k, v in a.items() if k != "status"}
            data["patient_name"] = data["patient_name"] or names.get(a["patient_id"], "")
            db.execute(
                "INSERT INTO appointments VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    a["appointment_id"],
                    a["patient_id"],
                    a["status"],
                    json.dumps(data),
                    *columns(data),
                ),
            )
        db.executemany(
            "INSERT INTO absences (provider_id, start_date, end_date, start_time, end_time, reason) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            absences,
        )
        db.executemany("INSERT INTO closures VALUES (?, ?, ?)", closures)
    return store
