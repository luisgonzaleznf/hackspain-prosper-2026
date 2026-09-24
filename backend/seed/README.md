# Clinic seed

Everything needed to build Clínica Arenal's database: patients, a diary that looks like a busy
private clinic, doctors' absences and public holidays. The seed is deterministic: the same
anchor, seed and patient count always produce the same database.

## Run it

```bash
cd backend
uv run --project . python scripts/seed_clinic.py --force          # today's anchor, 500 patients
uv run --project . python scripts/seed_clinic.py --db /tmp/c.sqlite3 --anchor 2026-09-24 --patients 3000 --force
```

`make seed` should run the same script. Options: `--db` (default `$LOCAL_CLINIC_DB`, else
`backend/data/clinic.sqlite3`), `--anchor YYYY-MM-DD` (default: today in Madrid), `--patients`
(default 500), `--seed` (default 7), `--dense-weeks` (4), `--tail-weeks` (4). If the database
already has rows, the script refuses to run unless you pass `--force`. With `--force` it drops
and rebuilds every table, including bookings made on calls and the `changes` log.

Each run finishes with an independent validation (`validate.py`) and prints a stats report. The
exit code is non-zero if any row breaks a clinic rule or a demo guarantee is missing.
`uv run --project . --env-file .env.example python -m pytest tests/test_seed.py` runs the same
checks on a temporary database.

## The anchor and the horizon

The anchor is the day the diary is built around. Nothing in the seed is hard-coded to a
calendar date, so re-seeding next month gives the same shape.

| Window | Days | What is in it |
|---|---|---|
| Older history | 2025 up to 9 weeks before the anchor | 1-4 attended visits for every patient the clinic has seen. The first is a first-visit type. |
| Recent history | the 8 weeks before the anchor | Attended visits (about 94%), no-shows (booked, `attendance: "no_show"`), cancellations, physiotherapy courses. |
| Anchor day | the anchor | Today's diary. No attendance yet. |
| Dense weeks | anchor+1 to anchor+28 | Busy. Targets fall from about 92% to 62% by specialty. Dr. Emilio Iglesia (PR06) is fully booked. |
| Tail | up to `horizon_end` = anchor + 8 weeks | Lighter, from 55% down to 25%. Physiotherapy courses carry on into it. |

The targets are ceilings. Each patient only accepts a realistic number of upcoming visits
(many take 0 or 1, and a physiotherapy course counts as one), so with few patients every week
thins out evenly. At 500 patients the diary is about 10-20% full outside PR06. At 3,000
patients the targets are reached. The script prints the scale factors it applied.

Absences are placed relative to the anchor. A real 2026 congress (EADV, SECOT, SEMERGEN) is
used when it falls inside the dense weeks. Otherwise a generic congress takes the same slot.
For the anchor 2026-09-24 the plan is:

- PR02: sick leave to 30 Sep.
- PR05: EADV, 30 Sep to 2 Oct.
- PR10: SECOT, 30 Sep to 2 Oct.
- PR01: SEMERGEN, 7 to 10 Oct.
- PR06: annual leave, 9 to 16 Oct.
- PR09: training course, 16 Oct.
- Four half-days.
- Summer and Christmas leave every year.

Holidays (`realism.HOLIDAYS`) cover 2025 to 2027:

- National and Comunidad de Madrid days close every site.
- Madrid-city days close Centro and Norte only.
- Getafe days close Sur only.
- 2027 is provisional, because the regional decree had not been published yet.

## Files

| File | What it is |
|---|---|
| `catalogue.json` | The static clinic: 3 sites, 12 doctors, specialties, appointment types, plans, restriction ids and `plan_rules` (insurer authorisations and annual allowances). Goes into `meta.catalogue`. |
| `recovered_patients.json` | 138 people from the Prosper world: the 33 the published cases reference, the 100 full charts, and others with a complete identity. Only identity, date of birth, phone, sex, plan, referrals, note and `has_visited_before`. |
| `realism.py` | The tables behind generated people and the diary. Includes INE name and surname frequencies by birth cohort, DNI/NIE helpers, phone and email rules, insurer weights and the holidays. Also: congress dates, absence and occupancy plans, hand-shaped families, the four-way "Rosario Sanz" namesake cluster, caller-handling hints, and the identities that must or must not exist. |
| `validate.py` | The independent checker and the stats report. It reads only the SQLite file. |
| `build_recovered.py` | A one-off that rebuilt `recovered_patients.json` from the data-recovery sweep. Kept for provenance. |

## Provenance and privacy

Every person in the database is synthetic.

- **Recovered people.** They come from the generated clinic world of the HackSpain 2026 Prosper platform. They were recovered read-only from the team's own logs, case files and git history. The case identities keep their platform ids, names, DNIs, dates of birth, phones and plans, so the published cases still make sense.
- **Everyone else.** They are generated from `realism.py`.

Never included:

- call data or caller numbers from call logs (recovered phones that came only from caller ID are replaced);
- local registrations;
- the four registration personas and the Studio new-patient persona (99887766P / 699887766).

Emails use only `example.com`, `example.org` and `example.net`. Children share a guardian's phone.

Model-visible facts go in `note`: a visit summary rebuilt from the seeded rows, family links with
patient ids, preferred language, "known as", and caller-handling hints. The platform's own notes
mixed stale visit history with those hints. Only the hints and referral sentences are kept.

Demo personas:

- **Josefa (P00001) and Lucas (P00003):** light diaries.
- **Ignacio (P00005):** exactly one upcoming appointment, `A001101`. It is a dermatology review with PR05 at Arenal Sur, at 12:00 on the first Tuesday at least 14 days after the anchor.
- **Amelia Williams Williams (X8148593S):** on file, so the privacy case has someone real to protect.
