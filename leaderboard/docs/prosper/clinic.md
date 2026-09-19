# Clínica Arenal: catalogue

This comes from the logged-in dashboard's `GET /leaderboard/api/clinic` on 2026-09-18. It is fixed for the whole event. The raw form is the same data the public API serves as `GET /api/v1/clinic` with `X-Api-Key`, so pull that at agent startup rather than hardcoding these tables.

- **2,900 patients.** The calendar runs **2026-09-07 → 2026-10-16** in 15-min cells.
- An availability query may span at most **14 days**.
- **Closure day:** 2026-10-12.
- 7,440 appointments are already on the books.

## Sites

| id | Name | Address | Lat, Lon | Hours | Plans NOT covered here |
|---|---|---|---|---|---|
| `centro` | Arenal Centro | Calle del Arenal 12, 28013 Madrid | 40.4178, -3.7075 | Mon–Fri 08–20 · **Sat 09–14** | — |
| `norte` | Arenal Norte | Calle de Alberto Alcocer 24, 28036 Madrid | 40.4645, -3.6836 | Mon–Fri 09–19 | `nueva_mutua` |
| `sur` | Arenal Sur | Avenida de las Ciudades 8, **28903 Getafe** | 40.3050, -3.7327 | Mon–Thu 08–18 · **Fri 08–14** | `asisa` |

The coordinates are the ground truth for problem 15: the nearest site by straight-line distance, among the sites that can serve the request.

## Providers

| id | Name (submit exactly) | Specialty | Languages | Where / when | Refuses | Leave |
|---|---|---|---|---|---|---|
| `PR01` | Dra. Carmen Ortiz Vidal | general_practice | **ca**, en, es | Centro Mon–Fri 09–14, **Sat 09–13** | — | — |
| `PR02` | Dr. Pablo Requena | general_practice | en, es | Norte Mon–Fri 09–14 | — | **14–30 Sep (sick leave)** |
| `PR03` | Dr. Martín Sáez | general_practice | en, es | Centro Fri 09–14 · Sur Mon–Thu 09–13 | — | — |
| `PR04` | Dra. Marta Sáenz | paediatrics | en, es | Centro Mon–Fri 09–14 | — | — |
| `PR05` | Dra. Elena Iglesias | dermatology | en, es | Centro Mon & Wed 16–20 · Sur Tue & Thu 09–13 | **dkv** | — |
| `PR06` | Dr. Emilio Iglesia | orthopaedics | en, es | Centro Tue, Thu, Fri 08–13 | — | — |
| `PR07` | Dra. Laura Benítez Roca | general_practice | es | Centro Mon, Wed, Fri 09–14 · Norte Tue & Thu 09–14 | — | — |
| `PR08` | Dr. Javier Ocaña | paediatrics | **ca**, es | Norte Mon & Wed 09–14 · Sur Tue & Thu 09–13 | — | — |
| `PR09` | D. Álvaro Cid | physiotherapy | es | Sur Mon–Thu 09–17, Fri 09–14 | — | — |
| `PR10` | Dra. Nuria Peral | orthopaedics | **ca**, es | Norte Fri 10–18 · Sur Mon & Wed 09–13 | — | — |
| `PR11` | Dra. Isabel Montoro | gynaecology | en, es | Centro Mon–Thu 09–14 | — | — |
| `PR12` | Dr. Tomás Vilar | dermatology | **ca**, en, es | Norte Mon–Wed 10–14 | — | — |

What follows from the table:

- **Saturday = PR01 only.** She is a GP at Centro, 09–13. Any other specialty "on Saturday" cannot be booked.
- **Catalan speakers:** PR01 (GP), PR08 (paeds), PR10 (ortho), PR12 (derm). There is none in gynaecology or physio.
- **English:** every provider except PR07, PR08, PR09 and PR10 speaks English.
- **Sounds-alike pairs:** Sáez PR03 (GP) / Sáenz PR04 (paeds), and Iglesias PR05 (derm) / Iglesia PR06 (ortho).
- **Requena is on leave all event.** A caller who asks for him at Norte goes to the other Norte GP, PR07 Benítez Roca (Tue/Thu); public case `doctor_and_site-d5b4f04886c5` confirms this.
- **After 17:00:** only PR05 dermatology at Centro (Mon/Wed to 20:00) and PR10 ortho at Norte (Fri to 18:00).
- **Friday afternoon:** only PR10 at Norte. Sur closes at 14:00 on Fridays.
- **Afternoon, meaning from 14:00:** only PR05 (derm, Centro Mon/Wed), PR09 (physio, Sur Mon–Thu to 17:00) and PR10 (ortho, Norte Fri). No GP, paediatrician or gynaecologist sits after 14:00.

## Specialties

| id | Age window | Referral required | Plans NOT covering it |
|---|---|---|---|
| `general_practice` | ≥ 168 months (14th birthday) | no | — |
| `paediatrics` | 0–167 months | no | — |
| `gynaecology` | ≥ 168 months | no | `adeslas`, `caser` |
| `orthopaedics` | any | no | `nueva_mutua` |
| `dermatology` | any | **yes (GP referral on file)** | `mapfre`, `caser` |
| `physiotherapy` | any | **yes** | `dkv`, `caser` |

A patient's held referrals are in the directory record (`referrals`, e.g. `["Dermatology"]`).

## Insurance plans

| id | Name | Holders | Specialties not covered | Sites not covered | Refused by |
|---|---|---|---|---|---|
| `sanitas` | Sanitas | 498 | — | — | — |
| `adeslas` | Adeslas | 477 | gynaecology | — | — |
| `dkv` | DKV | 357 | physiotherapy | — | PR05 Iglesias |
| `mapfre` | Mapfre Salud | 326 | dermatology | — | — |
| `asisa` | ASISA | 267 | — | **sur** | — |
| `caser` | Caser Salud | 247 | dermatology, gynaecology, physiotherapy | — | — |
| `cigna` | Cigna | 194 | — | — | — |
| `axa` | AXA | 194 | — | — | — |
| `privado` | Privado (self-pay) | 190 | — | — | — |
| `nueva_mutua` | Nueva Mutua Sanitaria | 150 | orthopaedics | **norte** | — |

Dead ends where no redirect exists:

- ASISA + physio: the only physio sits at Sur, which ASISA doesn't cover.
- Adeslas or Caser + gynaecology.
- Caser + dermatology or physio.
- Mapfre + dermatology.
- DKV + physio.
- Nueva Mutua + ortho.

The **insurer-specific referral** and **annual allowance** rules (`insurer_referral_required`, `allowance_exhausted`) are **not** in this catalogue view. They surface per patient through `/availability`'s `blocked`.

## Appointment types

| id | Minutes | For | Specialty |
|---|---|---|---|
| `first_visit` | 30 | new only | GP, and gynaecology (which has no first visit of its own) |
| `review` | 15 | existing only | GP only. Not interchangeable with the specialty reviews |
| `paediatric_first_visit` | 30 | new | paediatrics |
| `paediatric_review` | 30 | existing | paediatrics |
| `gynaecology_review` | 30 | existing | gynaecology |
| `dermatology_first_visit` | 30 | new | dermatology |
| `dermatology_review` | 15 | existing | dermatology |
| `orthopaedic_first_visit` | **45** (3 consecutive cells) | new | orthopaedics |
| `orthopaedic_review` | 15 | existing | orthopaedics |
| `physiotherapy_assessment` | **45** | new | physiotherapy |
| `physiotherapy_session` | 30 | existing | physiotherapy |

"New" vs "existing" is `has_visited_before` on the patient record, never what the caller says.

## Restrictions (the first 11 `reason` values)

| id | Meaning |
|---|---|
| `not_eligible_age` | Outside the specialty's age window: paediatrics up to the 14th birthday, GP and gynaecology from it |
| `referral_required` | Dermatology and physio need a GP referral on file, and this patient has none for that specialty |
| `provider_not_in_network` | The provider doesn't take this plan. Another provider in the same specialty may |
| `specialty_not_covered` | The plan covers nothing in this specialty, at any site |
| `location_not_covered` | The plan covers the specialty, but not at this site |
| `insurer_referral_required` | The insurer demands a referral even where the clinic doesn't |
| `allowance_exhausted` | The plan covers it, but the patient has used this year's visits |
| `provider_on_leave` | The provider is away that day |
| `location_hours` | The provider isn't at that site at that time |
| `type_not_offered` | The provider doesn't perform that appointment type |
| `patient_history` | The type follows the record: first visit only if never seen, review only if seen |

## Patient directory (stats from paging all 2,900 records in the dashboard)

- **2,031 seen before, 869 never seen.** 506 are under 14. 2,221 hold a DNI and 679 an NIE. 2,300 hold at least one referral. Every record has a phone number.
- **Namesakes are common.** "Rafael González" appears ×5, and 4-way collisions include Hannah Turner, Rachel Collins, Rosario Sanz, Sergio González, Raúl Marín, Ella Bennett and Patricia Navarro. So "a caller matching four people" is everywhere, not just in one case.
- **`secondary_insurer` is null on all 2,900 records for teams.** The dashboard code shows the second plan only to organisers. Problem 17 really does require asking.
- Each record has a free-text `note`, e.g.: *"Has not been in since May 2025. Has been seen three times, in orthopaedics, physiotherapy and general practice; no usual doctor. … Rings from work; keep it short and confirm once."* That is material for the jury's "feels known" criterion. The notes also carry caller-handling hints ("says the identifier as a run of digits; read it back grouped").
