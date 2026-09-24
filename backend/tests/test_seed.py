"""The clinic seed: invariants, demo guarantees, the 2026-09-24 absence plan and determinism."""

import hashlib
import json
import shutil
import sqlite3
from pathlib import Path

import pytest
from scripts import seed_clinic
from seed import validate

ANCHOR = "2026-09-24"
SEED_DIR = Path(__file__).resolve().parents[1] / "seed"


def run(db: Path, *extra: str) -> int:
    return seed_clinic.main(["--db", str(db), "--anchor", ANCHOR, "--patients", "500", "--quiet", *extra])


def content_hash(db: Path) -> str:
    conn = sqlite3.connect(db)
    digest = hashlib.sha256()
    for table in seed_clinic.TABLES:
        for row in conn.execute(f"SELECT * FROM {table} ORDER BY 1, 2"):
            if table == "meta" and row[0] == "seeded_at":
                continue
            digest.update(repr(row).encode())
    conn.close()
    return digest.hexdigest()


@pytest.fixture(scope="module")
def seeded(tmp_path_factory) -> Path:
    db = tmp_path_factory.mktemp("seed") / "clinic.sqlite3"
    assert run(db) == 0
    return db


@pytest.fixture(scope="module")
def clinic(seeded) -> validate.Clinic:
    return validate.Clinic(seeded)


def test_every_row_passes_the_independent_validator(seeded):
    report = validate.check(seeded)
    assert report["errors"] == []


def test_meta_and_catalogue(clinic):
    assert clinic.meta["anchor"] == ANCHOR
    assert clinic.meta["horizon_end"] == "2026-11-19"
    assert clinic.cat == json.loads((SEED_DIR / "catalogue.json").read_text())
    assert json.loads(clinic.meta["seed_params"])["patients"] == 500
    assert len(clinic.patients) == 500


def test_absence_plan_for_the_reference_anchor(clinic):
    got = {(a["provider_id"], a["start_date"], a["end_date"], a["start_time"], a["end_time"], a["reason"])
           for a in clinic.absences}
    assert {
        ("PR02", "2026-09-14", "2026-09-30", None, None, "sick leave"),
        ("PR05", "2026-09-30", "2026-10-02", None, None, "congress (EADV, Vienna)"),
        ("PR10", "2026-09-30", "2026-10-02", None, None, "congress (SECOT, Córdoba)"),
        ("PR01", "2026-10-07", "2026-10-10", None, None, "congress (SEMERGEN, Santiago)"),
        ("PR06", "2026-10-09", "2026-10-16", None, None, "annual leave"),
        ("PR09", "2026-10-16", "2026-10-16", None, None, "training course"),
        ("PR04", "2026-10-02", "2026-10-02", "12:00", "14:00", "personal"),
        ("PR07", "2026-10-06", "2026-10-06", "11:30", "14:00", "personal"),
        ("PR12", "2026-10-19", "2026-10-19", "10:00", "12:00", "personal"),
        ("PR11", "2026-10-22", "2026-10-22", "09:00", "11:00", "hospital teaching session"),
    } <= got


def test_holidays_close_the_right_sites(clinic):
    closures = {(r["date"], r["location_id"]) for r in clinic.closure_rows}
    assert ("2026-10-12", None) in closures and ("2026-11-02", None) in closures
    assert {("2026-11-09", "centro"), ("2026-11-09", "norte")} <= closures   # Madrid city only
    assert ("2026-11-09", "sur") not in closures and ("2026-11-09", None) not in closures
    booked_days = {a["start_time"][:10] for r, a in clinic.appointments if r["status"] == "booked"}
    assert "2026-10-12" not in booked_days


def test_demo_personas(clinic):
    upcoming = {pid: [a for r, a in clinic.appointments if a["patient_id"] == pid and r["status"] == "booked"
                      and a["start_time"][:10] >= ANCHOR] for pid in ("P00001", "P00003", "P00005")}
    [ignacio] = upcoming["P00005"]
    assert (ignacio["appointment_id"], ignacio["start_time"], ignacio["provider_id"], ignacio["location_id"],
            ignacio["appointment_type_id"], ignacio["policy_id"]) == (
        "A001101", "2026-10-13T12:00:00+02:00", "PR05", "sur", "dermatology_review", "cigna")
    assert len(upcoming["P00001"]) <= 1 and len(upcoming["P00003"]) <= 1
    for pid in ("P00001", "P00003", "P00005"):
        assert clinic.patients[pid]["has_visited_before"] is True
        rows = [a for r, a in clinic.appointments if a["patient_id"] == pid]
        assert 1 <= len(rows) <= 5   # light, plausible charts


def test_people_that_must_and_must_not_exist(clinic):
    ids = {p["national_id"] for p in clinic.patients.values()}
    phones = {p["phone"] for p in clinic.patients.values()}
    assert not ids & {"18921027P", "X0500252W", "50454876Y", "31426012P", "99887766P"}
    assert "699887766" not in phones
    assert "X8148593S" in ids and "607034486" in phones
    rosario = [p for p in clinic.patients.values()
               if {"rosario", "sanz"} <= validate.tokens(f"{p['given_name']} {p['first_surname']} {p['second_surname']}")]
    assert len(rosario) == 4
    assert all(not p["email"] or p["email"].rsplit("@", 1)[1] in ("example.com", "example.org", "example.net")
               for p in clinic.patients.values())


def test_national_ids_agree_with_the_app_validator(clinic):
    app_clinic = pytest.importorskip("app.clinic")
    assert all(app_clinic.national_id_valid(p["national_id"]) for p in clinic.patients.values())


def test_start_times_follow_madrid_dst(clinic):
    for _, a in clinic.appointments:
        day = a["start_time"][:10]
        if "2026-04-01" <= day <= "2026-10-24":
            assert a["start_time"].endswith("+02:00"), a["start_time"]
        elif "2026-10-26" <= day <= "2027-03-27":
            assert a["start_time"].endswith("+01:00"), a["start_time"]


def test_diary_shape(clinic):
    taken = clinic.busy()
    dense = list(validate.days(clinic.anchor.fromordinal(clinic.anchor.toordinal() + 1), clinic.dense_end))
    full = [p for p in clinic.providers
            if sum(len((clinic.open_cells(p, d) or (None, []))[1]) for d in dense)
            and not any(clinic.free_cells(p, d, taken) for d in dense)]
    assert full == ["PR06"]
    upcoming = {}
    for r, a in clinic.appointments:
        if r["status"] == "booked" and a["start_time"][:10] > ANCHOR:
            upcoming[a["patient_id"]] = upcoming.get(a["patient_id"], 0) + 1
    assert max(upcoming.values()) <= 8
    assert sum(1 for p in clinic.patients if upcoming.get(p, 0) <= 1) >= 0.6 * len(clinic.patients)


def test_deterministic_and_refuses_to_clobber(seeded, tmp_path):
    again = tmp_path / "again.sqlite3"
    assert run(again) == 0
    assert content_hash(again) == content_hash(seeded)
    assert run(again) == 2   # has data, no --force
    other = tmp_path / "other.sqlite3"
    assert run(other, "--seed", "8") == 0
    assert content_hash(other) != content_hash(seeded)


def test_validator_is_not_vacuous(seeded, tmp_path):
    broken = tmp_path / "broken.sqlite3"
    shutil.copy(seeded, broken)
    conn = sqlite3.connect(broken)
    _, data = conn.execute("SELECT appointment_id, data FROM appointments WHERE status = 'booked' "
                             "AND provider_id = 'PR06' AND start_date > ? LIMIT 1", (ANCHOR,)).fetchone()
    row = json.loads(data)
    row.update(appointment_id="A999999", patient_id="P00001", patient_name="Josefa Domínguez Navarro")
    conn.execute("INSERT INTO appointments VALUES (?, ?, 'booked', ?, ?, ?, ?)",
                 ("A999999", "P00001", json.dumps(row), row["provider_id"], row["start_time"][:10], row["start_time"]))
    conn.commit()
    conn.close()
    errors = validate.check(broken)["errors"]
    assert any("overlap for PR06" in e for e in errors)
