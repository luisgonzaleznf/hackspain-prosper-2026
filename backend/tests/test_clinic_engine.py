"""The clinic engine against small hand-built diaries: slot grid, rules, closures, absences,
windows, appointment types, and the patient directory."""

import asyncio
import time as clock
from datetime import datetime, timedelta

import pytest
from app import clinic, config
from app.clinic import ClinicError
from integrations.local_clinic import LocalClinic
from integrations.local_store import LocalStore

from clinic_fixture import CATALOGUE, booked, patient, seeded

NOW = datetime(2026, 9, 20, 10, tzinfo=config.TZ)  # Sunday
MON, TUE, SAT = "2026-09-21", "2026-09-22", "2026-09-26"


@pytest.fixture
def db():
    """A seeded clinic with the published catalogue, as of NOW."""

    def build(**rows) -> LocalStore:
        store = seeded(**rows)
        clinic._catalogue = clinic.build(store, NOW.date())
        return store

    return build


def search(store, date_from, date_to=None, now=NOW, **filters) -> dict:
    return asyncio.run(
        LocalClinic(store, now).availability(date_from, date_to or date_from, **filters)
    )


def starts(result, provider=None, site=None) -> list[str]:
    return [
        s["start_time"][11:16]
        for s in result["slots"]
        if (provider is None or s["provider_id"] == provider)
        and (site is None or s["location_id"] == site)
    ]


def blocked(result) -> dict[str, str]:
    return {b["provider_id"]: b["restriction"] for b in result["blocked"]}


def grid(first: str, last: str, step=15) -> list[str]:
    t = datetime.strptime(first, "%H:%M")
    end = datetime.strptime(last, "%H:%M")
    out = []
    while t <= end:
        out.append(t.strftime("%H:%M"))
        t += timedelta(minutes=step)
    return out


# ── slot grid ───────────────────────────────────────────────────────


def test_grid_fits_each_type_inside_the_doctors_hours(db):
    store = db(
        patients=[
            patient("RET", has_visited_before=True),
            patient("NEW", national_id="2", has_visited_before=False),
            patient(
                "PHY",
                national_id="3",
                has_visited_before=False,
                referrals=["physiotherapy"],
                insurer="privado",
            ),
        ]
    )
    # PR01 at Centro, Mon 09-14: a 15-minute review starts every quarter to 13:45 ...
    review = search(store, MON, provider_id="PR01", patient_id="RET")
    assert review["appointment_type"]["id"] == "review"
    assert starts(review) == grid("09:00", "13:45")
    first = review["slots"][0]
    assert list(first) == [
        "provider_id",
        "provider_name",
        "specialty_id",
        "location_id",
        "appointment_type_id",
        "start_time",
        "duration_minutes",
        "payable_with",
    ]
    assert first["start_time"] == "2026-09-21T09:00:00+02:00"
    assert first["payable_with"] == ["sanitas"]
    # ... a 30-minute first visit to 13:30 ...
    new = search(store, MON, provider_id="PR01", patient_id="NEW")
    assert new["appointment_type"]["id"] == "first_visit"
    assert starts(new) == grid("09:00", "13:30")
    # ... and a 45-minute physiotherapy assessment (PR09 at Sur, Mon 09-17) to 16:15.
    physio = search(store, MON, provider_id="PR09", patient_id="PHY")
    assert physio["appointment_type"]["duration_minutes"] == 45
    assert starts(physio) == grid("09:00", "16:15")


def test_saturday_hours_and_site_hours_bound_the_grid(db):
    store = db()
    # PR01 sits Saturdays 09-13 at Centro (open 09-14).
    assert starts(search(store, SAT, provider_id="PR01"))[-1] == "12:30"  # 30-min first visit
    # PR10 sits at Norte Fridays 10-18; Norte is open 09-19.
    friday = search(store, "2026-09-25", provider_id="PR10")
    assert (
        starts(friday, site="norte")[0] == "10:00" and starts(friday, site="norte")[-1] == "17:15"
    )
    assert search(store, "2026-09-27", specialty_id="general_practice")["slots"] == []  # Sunday


def test_booked_cells_block_every_start_that_would_overlap(db):
    store = db(
        patients=[patient("RET"), patient("NEW", national_id="2", has_visited_before=False)],
        appointments=[
            booked("A1", "RET", "PR01", "centro", f"{MON}T10:00:00+02:00"),  # 15 min
            booked("A2", "RET", "PR01", "centro", f"{MON}T11:00:00+02:00", "first_visit"),  # 30
            booked("X1", "RET", "PR01", "centro", f"{MON}T12:00:00+02:00", status="cancelled"),
        ],
    )
    new = starts(search(store, MON, provider_id="PR01", patient_id="NEW"))
    assert "09:30" in new and "09:45" not in new and "10:00" not in new and "10:15" in new
    assert "10:30" in new and "10:45" not in new and "11:15" not in new and "11:30" in new
    assert "12:00" in new  # a cancelled appointment frees its cells


def test_times_already_past_are_not_offered(db):
    store = db()
    now = datetime(2026, 9, 21, 11, 5, tzinfo=config.TZ)
    assert starts(search(store, MON, now=now, provider_id="PR01"))[0] == "11:15"


# ── closures and absences ───────────────────────────────────────────


def test_a_national_holiday_closes_every_site_and_blocks_nobody(db):
    store = db(closures=[(MON, None, "Fiesta")])
    result = search(store, MON, TUE, specialty_id="general_practice")
    assert {s["start_time"][:10] for s in result["slots"]} == {TUE}
    assert result["blocked"] == []


def test_a_local_holiday_closes_only_its_site(db):
    store = db(closures=[(MON, "sur", "Getafe")])
    result = search(store, MON, specialty_id="general_practice")
    assert starts(result, provider="PR03") == []  # Sáez sits at Sur on Mondays
    assert starts(result, provider="PR01")  # Ortiz at Centro is open
    assert result["blocked"] == []


def test_part_of_a_day_away_removes_only_those_hours(db):
    store = db(
        patients=[patient("RET")],
        absences=[("PR01", MON, MON, "11:00", "12:00", "personal")],
    )
    got = starts(search(store, MON, provider_id="PR01", patient_id="RET"))
    assert got == [t for t in grid("09:00", "13:45") if not "11:00" <= t < "12:00"]


def test_whole_days_away_remove_those_days(db):
    store = db(absences=[("PR01", MON, MON, None, None, "training")])
    result = search(store, MON, TUE, provider_id="PR01")
    assert {s["start_time"][:10] for s in result["slots"]} == {TUE}
    assert result["blocked"] == []
    assert result["providers"][0]["on_leave_until"] == MON


def test_on_leave_blocks_only_a_window_the_leave_covers(db):
    store = db(absences=[("PR02", "2026-09-14", "2026-09-30", None, None, "sick leave")])
    inside = search(store, MON, "2026-09-30", specialty_id="general_practice")
    assert blocked(inside) == {"PR02": "provider_on_leave"}
    assert starts(inside, provider="PR02") == []
    assert starts(inside, provider="PR01")  # the others still offer slots
    # Emitted even for a site the doctor never sits at, or a day they never work.
    assert blocked(search(store, SAT, provider_id="PR02", location_id="sur")) == {
        "PR02": "provider_on_leave"
    }
    # A window running past the leave is not blocked: the slots after it are real.
    after = search(store, "2026-09-28", "2026-10-02", provider_id="PR02")
    assert after["blocked"] == []
    assert {s["start_time"][:10] for s in after["slots"]} == {"2026-10-01", "2026-10-02"}


def test_a_week_away_covers_the_weekend_the_doctor_never_works(db):
    store = db(absences=[("PR02", "2026-09-21", "2026-09-25", None, None, "vacation")])
    assert blocked(search(store, "2026-09-21", "2026-09-27", provider_id="PR02")) == {
        "PR02": "provider_on_leave"
    }


# ── the rules, in order ─────────────────────────────────────────────


def test_every_restriction_the_search_can_report(db):
    store = db(
        patients=[
            patient("KID", date_of_birth="2017-03-03"),
            patient("NOREF", national_id="2", insurer="sanitas"),
            patient("DKV", national_id="3", insurer="dkv", referrals=["dermatology"]),
            patient("ADES", national_id="4", insurer="adeslas"),
            patient("ASISA", national_id="5", insurer="asisa", referrals=["physiotherapy"]),
            patient("AUTH", national_id="6", insurer="adeslas", referrals=["physiotherapy"]),
            patient(
                "USED",
                national_id="7",
                insurer="sanitas",
                referrals=["physiotherapy"],
                allowance_used={"physiotherapy": 19},
            ),
        ],
        appointments=[
            booked(
                "P1",
                "USED",
                "PR09",
                "sur",
                "2026-09-07T09:00:00+02:00",
                "physiotherapy_session",
                attendance="attended",
            ),
            booked(
                "P2",
                "USED",
                "PR09",
                "sur",
                "2026-09-08T09:00:00+02:00",
                "physiotherapy_session",
                attendance="no_show",
            ),
        ],
        absences=[("PR11", MON, TUE, None, None, "congress")],
    )
    cases = [
        ("KID", {"specialty_id": "general_practice"}, "not_eligible_age", "review"),
        ("NOREF", {"specialty_id": "dermatology"}, "referral_required", "dermatology_review"),
        ("ADES", {"specialty_id": "gynaecology"}, "specialty_not_covered", "gynaecology_review"),
        ("ASISA", {"specialty_id": "physiotherapy"}, "location_not_covered", None),
        ("AUTH", {"specialty_id": "physiotherapy"}, "insurer_referral_required", None),
        ("USED", {"specialty_id": "physiotherapy"}, "allowance_exhausted", None),
    ]
    for pid, filters, rule, kind in cases:
        result = search(store, MON, TUE, patient_id=pid, **filters)
        assert set(blocked(result).values()) == {rule}, pid
        assert result["slots"] == [], pid
        if kind:
            assert result["appointment_type"]["id"] == kind  # named even when blocked
    # DKV: Iglesias refuses the plan, Vilar takes it.
    dkv = search(store, MON, TUE, specialty_id="dermatology", patient_id="DKV")
    assert blocked(dkv) == {"PR05": "provider_not_in_network"}
    assert {s["provider_id"] for s in dkv["slots"]} == {"PR12"}
    # The gynaecologist away the whole window, for a patient the plan covers.
    assert blocked(search(store, MON, TUE, specialty_id="gynaecology")) == {
        "PR11": "provider_on_leave"
    }
    # Four of the seven kinds need patient data: a second plan clears the insurance ones.
    second_plan = search(
        store, "2026-09-23", patient_id="ADES", specialty_id="gynaecology", insurers=["sanitas"]
    )
    assert second_plan["slots"][0]["payable_with"] == ["sanitas"]


def test_a_plan_valid_at_some_sites_drops_the_rest_silently(db):
    store = db(patients=[patient("ASISA", insurer="asisa")])
    # ASISA is not valid at Sur: Sáez's Sur Mondays vanish, nobody is blocked ...
    anywhere = search(store, MON, "2026-09-25", specialty_id="general_practice", patient_id="ASISA")
    assert anywhere["blocked"] == []
    assert {s["location_id"] for s in anywhere["slots"]} == {"centro", "norte"}
    assert starts(anywhere, provider="PR03")  # his Centro Friday stays
    # ... but asking for Sur blocks every GP, even those who never sit there.
    at_sur = search(
        store, MON, specialty_id="general_practice", location_id="sur", patient_id="ASISA"
    )
    assert set(blocked(at_sur)) == {"PR01", "PR02", "PR03", "PR07"}
    assert set(blocked(at_sur).values()) == {"location_not_covered"}


def test_authorisation_and_allowance_clear_with_the_right_chart(db):
    store = db(
        patients=[
            patient(
                "AUTH",
                insurer="adeslas",
                referrals=["physiotherapy"],
                insurer_authorizations=["physiotherapy"],
            ),
            patient(
                "LEFT",
                national_id="2",
                insurer="sanitas",
                referrals=["physiotherapy"],
                allowance_used={"physiotherapy": 18},
            ),
        ],
        appointments=[
            booked(
                "P1",
                "LEFT",
                "PR09",
                "sur",
                "2026-09-08T09:00:00+02:00",
                "physiotherapy_session",
                attendance="no_show",
            ),
        ],
    )
    assert search(store, MON, specialty_id="physiotherapy", patient_id="AUTH")["slots"]
    assert search(store, MON, specialty_id="physiotherapy", patient_id="LEFT")["slots"]


def test_age_is_checked_on_each_day(db):
    # Turns 14 on Wednesday 23 Sep: paediatrics until Tuesday, general practice from Wednesday.
    store = db(patients=[patient("TEEN", date_of_birth="2012-09-23")])
    gp = search(store, MON, "2026-09-25", specialty_id="general_practice", patient_id="TEEN")
    assert gp["blocked"] == [] and min(s["start_time"][:10] for s in gp["slots"]) == "2026-09-23"
    kids = search(store, MON, "2026-09-25", specialty_id="paediatrics", patient_id="TEEN")
    assert max(s["start_time"][:10] for s in kids["slots"]) == TUE


# ── appointment type ────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("specialty", "new", "returning"),
    [
        ("general_practice", "first_visit", "review"),
        ("gynaecology", "first_visit", "gynaecology_review"),
        ("paediatrics", "paediatric_first_visit", "paediatric_review"),
        ("dermatology", "dermatology_first_visit", "dermatology_review"),
        ("orthopaedics", "orthopaedic_first_visit", "orthopaedic_review"),
        ("physiotherapy", "physiotherapy_assessment", "physiotherapy_session"),
    ],
)
def test_the_type_follows_the_specialty_and_the_history(db, specialty, new, returning):
    store = db(
        patients=[
            patient("NEW", has_visited_before=False, referrals=[specialty]),
            patient("OLD", national_id="2", referrals=[specialty]),
        ]
    )
    assert (
        search(store, MON, specialty_id=specialty, patient_id="NEW")["appointment_type"]["id"]
        == new
    )
    assert (
        search(store, MON, specialty_id=specialty, patient_id="OLD")["appointment_type"]["id"]
        == returning
    )
    # No patient: the new-patient type, payable with every plan the doctor and site take.
    anonymous = search(store, MON, TUE, specialty_id=specialty)
    assert anonymous["appointment_type"]["id"] == new
    assert all(len(s["payable_with"]) > 1 for s in anonymous["slots"])


# ── the patient's own diary ─────────────────────────────────────────


def test_the_patients_own_appointments_are_never_double_booked(db):
    store = db(
        patients=[patient("RET")],
        appointments=[booked("MINE", "RET", "PR07", "centro", f"{MON}T09:00:00+02:00")],
    )
    got = starts(search(store, MON, provider_id="PR01", patient_id="RET"))
    assert "09:00" not in got and "09:15" in got
    # Without the patient, Dr. Ortiz is free at 09:00.
    assert "09:00" in starts(search(store, MON, provider_id="PR01"))


def test_excluding_the_appointment_being_moved_frees_its_time(db):
    store = db(
        patients=[patient("RET")],
        appointments=[booked("MINE", "RET", "PR01", "centro", f"{MON}T10:00:00+02:00")],
    )
    assert "10:00" not in starts(search(store, MON, provider_id="PR01", patient_id="RET"))
    moving = search(store, MON, provider_id="PR01", patient_id="RET", exclude_appointment_id="MINE")
    assert "10:00" in starts(moving)


def test_slots_are_sorted_by_time_then_doctor(db):
    result = search(db(), MON, specialty_id="general_practice")
    keys = [(s["start_time"], s["provider_id"]) for s in result["slots"]]
    assert keys == sorted(keys)
    assert [s["provider_id"] for s in result["slots"][:3]] == ["PR01", "PR02", "PR03"]
    assert [p["id"] for p in result["providers"]] == ["PR01", "PR02", "PR03", "PR07"]


def test_a_slot_after_the_clocks_change_carries_the_winter_offset(db):
    store = db(horizon_end="2026-11-30")
    result = search(store, "2026-10-26", provider_id="PR01", now=NOW + timedelta(days=30))
    assert result["slots"][0]["start_time"] == "2026-10-26T09:00:00+01:00"


# ── the window ──────────────────────────────────────────────────────


def test_the_window_is_clipped_to_the_calendar_or_refused_outside_it(db):
    store = db(horizon_end="2026-10-02")
    clipped = search(store, "2026-09-28", "2026-10-09", provider_id="PR01")
    assert max(s["start_time"][:10] for s in clipped["slots"]) == "2026-10-02"
    today = search(store, "2026-09-10", MON, provider_id="PR01")  # starts at the call's day
    assert {s["start_time"][:10] for s in today["slots"]} == {MON}
    refusals = [
        (("2026-10-03", "2026-10-05"), {}, "date range is outside the published calendar"),
        (("2026-09-01", "2026-09-10"), {}, "date range is outside the published calendar"),
        ((MON, "2026-10-05"), {}, "date range exceeds 14 days"),
        ((TUE, MON), {}, "date_to is before date_from"),
        (("21/09/2026", MON), {}, "dates must be YYYY-MM-DD"),
        ((MON, MON), {"provider_id": None}, "give specialty_id or provider_id"),
        ((MON, MON), {"provider_id": "PR99"}, "unknown provider_id PR99"),
        (
            (MON, MON),
            {"provider_id": None, "specialty_id": "oncology"},
            "unknown specialty_id oncology",
        ),
        ((MON, MON), {"specialty_id": "dermatology"}, "PR01 does not practise dermatology"),
        ((MON, MON), {"location_id": "este"}, "unknown location_id este"),
        ((MON, MON), {"patient_id": "P404"}, "unknown patient_id P404"),
        ((MON, MON), {"insurers": ["acme"]}, "unknown insurer acme"),
    ]
    for (first, last), extra, detail in refusals:
        with pytest.raises(ClinicError) as refused:
            search(store, first, last, **({"provider_id": "PR01"} | extra))
        assert (refused.value.status, refused.value.detail) == (422, detail)


def test_an_unseeded_database_says_how_to_fix_it():
    with pytest.raises(ClinicError) as refused:
        clinic.load()
    assert refused.value.status == 503
    assert "make seed" in refused.value.detail


# ── the directory ───────────────────────────────────────────────────


def names(matches) -> list[str]:
    return [m["patient_id"] for m in matches]


def find(store, **query):
    return asyncio.run(LocalClinic(store, NOW).directory(**query))


def test_exact_fields_filter_and_a_name_narrows_to_the_best_match(db):
    store = db(
        patients=[
            patient(
                "MUM",
                given_name="Rosa",
                first_surname="Gil",
                second_surname="Pardo",
                phone="611222333",
                national_id="1",
            ),
            patient(
                "KID",
                given_name="Lucía",
                first_surname="Martín",
                second_surname="Gil",
                phone="611222333",
                national_id="2",
                date_of_birth="2016-02-02",
            ),
            patient(
                "JOSEFA",
                given_name="Josefa",
                first_surname="Domínguez",
                second_surname="Navarro",
                date_of_birth="2001-09-19",
                national_id="48064716Y",
            ),
            patient(
                "SANTI",
                given_name="Santiago",
                first_surname="Sanz",
                second_surname="Hernández",
                date_of_birth="2001-09-19",
                national_id="4",
            ),
        ]
    )
    # A family line: the phone alone finds both, the name picks the mother.
    assert names(find(store, phone="+34 611 222 333")) == ["MUM", "KID"]
    assert names(find(store, phone="0034611222333", name="Rosa Gil")) == ["MUM"]
    # A misheard first name still reaches the right chart through the date of birth ...
    assert names(find(store, name="Xusefa Domínguez Navarro", date_of_birth="2001-09-19")) == [
        "JOSEFA"
    ]
    # ... a name nobody shares leaves every survivor of the exact field, for the tool to flag.
    assert names(find(store, name="Seth Mínguez", date_of_birth="2001-09-19")) == [
        "JOSEFA",
        "SANTI",
    ]
    # A wrong exact field excludes; the DNI is compared normalised.
    assert find(store, phone="611222334", name="Rosa Gil Pardo") == []
    match = find(store, national_id="48064716-y", name="Josefa")[0]
    assert match["patient_id"] == "JOSEFA"
    assert (match["matched_fields"], match["match_score"]) == (["name", "national_id"], 1.0)
    assert find(store) == []


def test_twins_are_told_apart_by_the_given_name(db):
    twin = {
        "first_surname": "Ruiz",
        "second_surname": "Gómez",
        "date_of_birth": "2015-06-01",
        "phone": "622333444",
    }
    store = db(
        patients=[
            patient("T1", given_name="Pablo", national_id="1", **twin),
            patient("T2", given_name="Marta", national_id="2", **twin),
        ]
    )
    assert names(find(store, date_of_birth="2015-06-01")) == ["T1", "T2"]
    assert names(find(store, name="Marta Ruiz Gómez", date_of_birth="2015-06-01")) == ["T2"]
    assert names(find(store, name="pablo ruiz", phone="622 333 444")) == ["T1"]


def test_a_name_alone_is_a_fuzzy_ranked_search_capped_at_ten(db):
    rosarios = [
        patient(
            "R1",
            given_name="Rosario",
            first_surname="Sanz",
            second_surname="González",
            national_id="1",
        ),
        patient(
            "R2",
            given_name="María del Rosario",
            first_surname="Sanz",
            second_surname="Moreno",
            national_id="2",
        ),
        patient(
            "R3",
            given_name="Rosario",
            first_surname="Sanz",
            second_surname="Gómez",
            national_id="3",
        ),
        patient(
            "R4",
            given_name="Rosario",
            first_surname="Martín",
            second_surname="Sanz",
            national_id="4",
        ),
    ]
    garcias = [
        patient(
            f"G{i:02d}",
            given_name="María",
            first_surname="García",
            second_surname=f"Ruiz{i}",
            national_id=f"g{i}",
        )
        for i in range(15)
    ]
    other = patient(
        "X", given_name="Pedro", first_surname="Olmedo", second_surname="Vidal", national_id="x"
    )
    exact = patient(
        "GX", given_name="Maria", first_surname="Garcia", second_surname="", national_id="gx"
    )
    store = db(patients=[*rosarios, *garcias, other, exact])
    cluster = find(store, name="rosario SANZ")
    assert set(names(cluster)[:4]) == {"R1", "R2", "R3", "R4"}
    assert all(m["matched_fields"] == ["name"] for m in cluster)
    assert "X" not in names(cluster)  # clearly someone else
    many = find(store, name="Maria Garcia")
    assert len(many) == 10
    assert names(many)[0] == "GX"  # the exact full name first, accents ignored
    assert all(m["match_score"] == 1.0 for m in many)
    misheard = find(store, name="Pedro Olmeda Vidal")
    assert names(misheard)[0] == "X" and misheard[0]["match_score"] < 1.0


# ── the live catalogue ──────────────────────────────────────────────


class Clock:
    today = datetime(2026, 9, 20, 9, tzinfo=config.TZ)

    @classmethod
    def now(cls, tz=None):
        return cls.today


def test_the_catalogue_is_recomputed_when_the_day_or_the_database_changes(monkeypatch):
    store = seeded(
        horizon_end="2026-10-18",
        patients=[patient("RET")],
        appointments=[booked("A1", "RET", "PR01", "centro", f"{MON}T09:00:00+02:00")],
        absences=[
            ("PR02", "2026-09-14", "2026-09-30", None, None, "sick leave"),
            ("PR02", "2026-10-14", "2026-10-15", None, None, "training"),
            ("PR04", "2026-09-25", "2026-09-25", "12:00", "14:00", "personal"),
            ("PR05", "2026-09-01", "2026-09-05", None, None, "congress"),
        ],
        closures=[
            ("2026-10-12", None, "Fiesta Nacional de España"),
            ("2026-10-02", "centro", "Local"),
            ("2026-10-09", "centro", "A"),
            ("2026-10-09", "norte", "A"),
            ("2026-10-09", "sur", "A"),
        ],
    )
    monkeypatch.setattr(clinic, "datetime", Clock)
    first = clinic.load()
    assert clinic.load() is first  # cached while nothing changes
    calendar = first["calendar"]
    assert (calendar["starts"], calendar["ends"]) == ("2026-09-20", "2026-10-18")
    assert (calendar["max_span_days"], calendar["slot_minutes"]) == (14, 15)
    assert calendar["closure_days"] == ["2026-10-09", "2026-10-12"]
    assert {"date": "2026-10-02", "location_id": "centro", "name": "Local"} in calendar["closures"]
    assert calendar["appointment_count"] == 1 and first["patient_count"] == 1
    providers = {p["id"]: p for p in first["providers"]}
    assert providers["PR02"]["leave"] == {
        "start": "2026-09-14",
        "end": "2026-09-30",
        "reason": "sick leave",
    }
    assert len(providers["PR02"]["absences"]) == 2
    assert (
        providers["PR04"]["leave"] is None
        and providers["PR04"]["absences"][0]["start_time"] == "12:00"
    )
    assert providers["PR05"]["absences"] == [] and providers["PR05"]["leave"] is None
    assert "plan_rules" in first and "restrictions" in first
    # A new day: the calendar and the leave move on.
    Clock.today = datetime(2026, 10, 1, 9, tzinfo=config.TZ)
    later = clinic.load()
    assert later is not first
    assert later["calendar"]["starts"] == "2026-10-01"
    assert {p["id"]: p for p in later["providers"]}["PR02"]["leave"]["reason"] == "training"
    # A write to the database (a booking, a re-seed) is picked up too.
    clock.sleep(0.01)
    seeded(
        store=store,
        appointments=[booked("A2", "RET", "PR01", "centro", "2026-10-05T09:00:00+02:00")],
    )
    assert clinic.load()["calendar"]["appointment_count"] == 1  # A1 is now in the past
    Clock.today = datetime(2026, 9, 20, 9, tzinfo=config.TZ)


def test_a_catalogue_a_test_sets_is_used_as_is(monkeypatch):
    fixed = {"providers": [], "locations": []}
    monkeypatch.setattr(clinic, "_catalogue", fixed)
    assert clinic.load() is fixed
    assert asyncio.run(clinic.catalogue()) is fixed


def test_the_prompt_text_names_absences_and_closures(db):
    db(
        absences=[
            ("PR05", "2026-09-30", "2026-10-02", None, None, "congress"),
            ("PR04", "2026-10-02", "2026-10-02", "12:00", "14:00", "personal"),
            ("PR09", "2026-10-16", "2026-10-16", None, None, "training"),
            ("PR06", "2026-09-01", "2026-09-10", None, None, "vacation"),
        ],
        closures=[
            ("2026-10-12", None, "Fiesta Nacional"),
            ("2026-10-09", "centro", "Madrid local holiday"),
            ("2026-10-09", "norte", "Madrid local holiday"),
        ],
    )
    cat = clinic._catalogue
    text = clinic.render_catalogue(cat, NOW.date())
    assert "AWAY 2026-09-30 to 2026-10-02 (congress)" in text
    assert "AWAY Fri 2 Oct 12:00-14:00 (personal)" in text
    assert "AWAY 2026-10-16 (training)" in text
    assert "vacation" not in text  # over before today
    days = clinic.calendar_text(NOW, cat)
    assert (
        "Mon 12 Oct 2026 (2026-10-12) — CLOSED everywhere (public holiday: Fiesta Nacional)" in days
    )
    assert (
        "Fri 09 Oct 2026 (2026-10-09) — closed at Arenal Centro and Arenal Norte "
        "(Madrid local holiday)" in days
    )
    assert "The bookable calendar ends Sunday 18 October 2026 (2026-10-18)" in days
    # A single past leave in an old-style catalogue is not rendered either.
    old = {
        **CATALOGUE,
        "providers": [
            dict(
                CATALOGUE["providers"][1],
                leave={"start": "2026-09-01", "end": "2026-09-10", "reason": "sick leave"},
            )
        ],
    }
    assert "AWAY" not in clinic.render_catalogue(old, NOW.date())


# ── scale ───────────────────────────────────────────────────────────


def test_a_fortnight_search_is_fast_at_clinic_scale(db):
    """3000 patients and 6000 diary rows: a 14-day specialty search stays well under 300 ms."""
    people = [
        patient(
            f"P{n:05d}",
            national_id=f"{n:08d}",
            phone=f"6{n:08d}",
            given_name=("Ana", "Luis", "Marta", "Jorge")[n % 4],
            first_surname=("García", "López", "Sanz", "Ruiz", "Gil")[n % 5],
        )
        for n in range(3000)
    ]
    rows = []
    cells = [
        (p["id"], s["location_id"], d["weekday"])
        for p in CATALOGUE["providers"]
        for s in p["schedules"]
        for d in s["days"]
    ]
    weekdays = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
    day0 = datetime(2026, 8, 24, tzinfo=config.TZ)
    for n in range(6000):
        day = day0 + timedelta(days=n % 56)
        options = [c for c in cells if c[2] == weekdays[day.weekday()]]
        if not options:
            continue
        provider, site, _ = options[n % len(options)]
        start = day.replace(hour=9 + (n // 56) % 4, minute=15 * ((n // 224) % 4))
        rows.append(
            booked(
                f"A{n:06d}", f"P{n % 3000:05d}", provider, site, start.isoformat(timespec="seconds")
            )
        )
    store = db(patients=people, appointments=rows)
    engine = LocalClinic(store, NOW)
    started = clock.perf_counter()
    result = asyncio.run(
        engine.availability(MON, "2026-10-04", specialty_id="general_practice", patient_id="P00042")
    )
    elapsed = clock.perf_counter() - started
    assert result["slots"]
    assert elapsed < 0.3, f"{elapsed * 1000:.0f} ms"
    started = clock.perf_counter()
    assert asyncio.run(engine.directory(name="Marta Sanz"))
    assert asyncio.run(engine.directory(phone="+34600000042"))
    assert clock.perf_counter() - started < 0.3


def test_an_old_database_gains_the_diary_columns_filled_from_its_rows(db):
    import json
    import sqlite3

    path = LocalStore().path
    path.parent.mkdir(parents=True, exist_ok=True)
    row = booked("OLD1", "RET", "PR01", "centro", f"{MON}T09:00:00+02:00")
    with sqlite3.connect(path) as old:
        old.execute(
            "CREATE TABLE appointments (appointment_id TEXT PRIMARY KEY, patient_id TEXT NOT NULL, "
            "status TEXT NOT NULL, data TEXT NOT NULL)"
        )
        old.execute(
            "INSERT INTO appointments VALUES (?, ?, 'booked', ?)",
            ("OLD1", "RET", json.dumps(row)),
        )
    store = db(patients=[patient("RET")])
    with store.connect() as conn:
        assert tuple(
            conn.execute("SELECT provider_id, start_date, start_time FROM appointments").fetchone()
        ) == ("PR01", MON, f"{MON}T09:00:00+02:00")
    assert "09:00" not in starts(search(store, MON, provider_id="PR01", patient_id="RET"))
