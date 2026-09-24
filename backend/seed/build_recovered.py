"""One-off: rebuild recovered_patients.json from the Prosper data-recovery sweep.

    python seed/build_recovered.py --recover-dir <dir with patients.json and public_cases.json>

The inputs came from a read-only extraction of the team's own logs and git history (the platform's
synthetic world, not real people). Only identity, date of birth, phone, sex, plan, referrals, note
and has_visited_before are kept, for:
- the 33 people the published cases reference (identities exactly as the cases publish them),
- the 100 full charts the platform returned,
- other recovered people whose identity is complete (their phones came only from caller ID
  in our call logs, so they are dropped and the seed invents new ones).
Never copied: call rows, caller numbers from logs, local registrations, the registration personas.
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from seed import realism

CASE_IDS = ["P00001", "P00003", "P00004", "P00005", "P00006", "P00008", "P00009", "P00011", "P00012", "P00015", "P00020", "P00023", "P00028", "P00032", "P00038", "P00050", "P00057", "P00067", "P00100", "P00121", "P00330", "P00358", "P00402", "P01842", "P01843", "P01846", "P01847", "P01850", "P01971", "P02809", "P00196", "P00293", "P00301"]
INSURER_NAMES = {"mapfre salud": "mapfre", "asisa": "asisa", "sanitas": "sanitas", "cigna": "cigna",
                 "axa": "axa", "dkv": "dkv", "adeslas": "adeslas", "caser salud": "caser",
                 "nueva mutua sanitaria": "nueva_mutua", "privado": "privado"}


def female_names() -> set[str]:
    names = {n for cohort in realism.GIVEN_NAMES_F.values() for n, _ in cohort}
    names |= {n for cohort in realism.GIVEN_NAMES_TAIL_F.values() for n in cohort}
    names |= {n for f in realism.FOREIGN_NAMES.values() for n in f[1]}
    return names | {"Lola", "Amparo", "Gloria", "Chloe", "Amelia", "Grace", "Jessica", "Sarah", "Rachel"}


def split(full: str) -> tuple[str, str, str] | None:
    words = full.split()
    return (words[0], words[1], words[2]) if len(words) == 3 else None


def plan(value) -> str | None:
    if not value:
        return None
    return INSURER_NAMES.get(str(value).lower(), str(value).lower())


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--recover-dir", required=True, type=Path)
    args = parser.parse_args()
    patients = {x["patient_id"]: x for x in json.loads((args.recover_dir / "patients.json").read_text())["patients"]}
    cases = json.loads((args.recover_dir / "public_cases.json").read_text())["cases"]
    females = female_names()

    persona: dict[str, dict] = {}  # identity as the published cases give it
    for case in cases:
        data, caller_phone = case["persona"]["data"], case["persona"].get("caller_id_phone") or ""
        for person in case["people"]:
            pid = person.get("patient_id")
            if not pid or pid in persona:
                continue
            if person["role"] == "caller":
                full = data.get("caller_full_name")
                ident = {"national_id": data.get("caller_national_id"), "date_of_birth": data.get("caller_date_of_birth"),
                         "phone": data.get("caller_phone") or caller_phone, "insurer": plan(data.get("caller_insurer"))}
            elif person["role"] == "self" and data.get("given_name"):
                full = data["full_name"]
                ident = {"national_id": data.get("national_id"), "date_of_birth": data.get("date_of_birth"),
                         "phone": data.get("phone") or caller_phone, "insurer": plan(data.get("insurer"))}
            else:
                continue
            names = split(full or "")
            if names and all(ident.values() if person["role"] == "self" else
                             (ident["national_id"], ident["date_of_birth"], ident["phone"])):
                persona[pid] = {**dict(zip(("given_name", "first_surname", "second_surname"), names, strict=True)), **ident}

    out = []
    for pid, entry in sorted(patients.items()):
        rec = entry["record"]
        chart = entry["best_shape"] == "dashboard_chart"
        if pid in CASE_IDS:
            base = {k: rec.get(k) for k in ("given_name", "first_surname", "second_surname", "national_id",
                                             "date_of_birth", "phone", "insurer")} if chart else persona[pid]
            source = "chart" if chart else "case persona"
        elif chart:
            base = {k: rec.get(k) for k in ("given_name", "first_surname", "second_surname", "national_id",
                                             "date_of_birth", "phone", "insurer")}
            source = "chart"
        else:
            names = split(rec.get("full_name") or "")
            if not (names and rec.get("national_id") and rec.get("date_of_birth") and rec.get("insurer")):
                continue
            base = {**dict(zip(("given_name", "first_surname", "second_surname"), names, strict=True)),
                    "national_id": rec["national_id"], "date_of_birth": rec["date_of_birth"],
                    "insurer": rec["insurer"],
                    # a phone only ever seen as a caller ID in our logs is not copied
                    "phone": rec.get("phone") if entry["field_sources"].get("phone") in ("dashboard_chart", "directory_match") else None}
            source = "agent view"
        full_name = " ".join((base["given_name"], base["first_surname"], base["second_surname"]))
        if base["national_id"] in realism.FORBIDDEN_NATIONAL_IDS or full_name in realism.FORBIDDEN_NAMES:
            continue
        sex = rec.get("sex") or ("F" if base["given_name"] in females else "M")
        out.append({
            "patient_id": pid, **base, "sex": sex,
            "insurer": base.get("insurer") or rec.get("insurer"),
            "referrals": rec.get("referrals"), "note": rec.get("note") or "",
            "has_visited_before": rec.get("has_visited_before"),
            "case_identity": pid in CASE_IDS, "source": source,
        })
    missing = sorted(set(CASE_IDS) - {p["patient_id"] for p in out})
    if missing:
        raise SystemExit(f"case identities missing: {missing}")
    doc = {
        "provenance": "Synthetic patients of the HackSpain 2026 Prosper platform world (the organisers' "
                      "generated clinic), recovered read-only from the team's own logs, case files and "
                      "git history. Only the fields the seed needs; no call data, no caller numbers, no "
                      "local registrations.",
        "patients": out,
    }
    target = Path(__file__).resolve().parent / "recovered_patients.json"
    target.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + "\n")
    print(f"{len(out)} patients -> {target}")


if __name__ == "__main__":
    main()
