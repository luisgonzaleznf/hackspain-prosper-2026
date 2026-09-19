<!-- Generated from data/public-cases.json (https://hackspain.getprosperapp.com/leaderboard/assets/public-cases-BH3bsRyz.json, fetched 2026-09-18). -->

# Public practice cases — index

73 published cases across 17 problems (Switchboard has none: it replays problem 1 in bursts of 5/10/20). Each case in `data/public-cases.json` carries the caller persona (`persona.data` = what the caller knows, `persona.objectives` = how they behave), the full `caller_prompt` the simulated patient runs on, audio settings, `protected` fields (problem 14), and `expected.acceptable` — any one of those action lists passes.

**Slots move daily.** This export is anchored at `reference_time` 2026-09-18T09:00+02:00 (Friday). The live problem page re-anchors each case to 09:00 Europe/Madrid on the day it is dialled, so a BOOK slot below may differ from what passes tomorrow. Everything else (patient, provider, site, type, policy, reasons) is fixed.

Caller rules common to all personas: `turn_cap` 24 turns, `wall_clock_budget` PT3M.

## `simple_booking` — 4 cases

**`simple_booking-14a8720daa02`** · en · caller: Josefa Domínguez Navarro (female, persona phone 711330529)  
Wants the earliest available General Practice appointment. Identifies by DNI/NIE; seen before, so a review.  
Accepts: `BOOK(patient_id=P00001, provider_id=PR01, location_id=centro, appointment_type_id=review, slot=2026-09-19T11:00:00+02:00, policy_id=mapfre)`

**`simple_booking-12dc84a98cb2`** · en · caller: Amelia Hughes White (female, persona phone 712676131)  
Wants the earliest available General Practice appointment at Arenal Centro. Identifies by DNI/NIE; never seen, so a first visit.  
Accepts: `BOOK(patient_id=P00012, provider_id=PR07, location_id=centro, appointment_type_id=first_visit, slot=2026-09-21T11:45:00+02:00, policy_id=sanitas)`

**`simple_booking-3371b9ac9462`** · en · caller: Ignacio Vázquez Moreno (male, persona phone 731169716)  
Wants the earliest available Orthopaedics appointment. Identifies by phone number; seen before, so a review.  
Accepts: `BOOK(patient_id=P00005, provider_id=PR10, location_id=sur, appointment_type_id=orthopaedic_review, slot=2026-09-21T09:30:00+02:00, policy_id=cigna)`

**`simple_booking-b33e7e633856`** · en · caller: Chloe Roberts Smith (female, persona phone 708729566)  
Wants the earliest available General Practice appointment at Arenal Sur on a Monday in the morning. Identifies by DNI/NIE; seen before, so a review.  
Accepts: `BOOK(patient_id=P00011, provider_id=PR03, location_id=sur, appointment_type_id=review, slot=2026-09-21T09:00:00+02:00, policy_id=mapfre)`

## `doctor_and_site` — 5 cases

**`doctor_and_site-2fe62ca2872f`** · en · caller: Joaquín Ramírez Delgado (male, persona phone 642674973)  
Wants an appointment with Dra. Ortiz Vidal at Arenal Centro. The doctor consults there, so their earliest slot at that site. Identifies by DNI/NIE; seen before, so a review.  
Accepts: `BOOK(patient_id=P01842, provider_id=PR01, location_id=centro, appointment_type_id=review, slot=2026-09-19T11:00:00+02:00, policy_id=privado)`

**`doctor_and_site-057078bb5b44`** · en · caller: Emilio Rubio Jiménez (male, persona phone 781850784)  
Wants an appointment with Dr. Sáez, the GP. Not Dra. Sáenz, the paediatrician, who sounds the same. Identifies by DNI/NIE; seen before, so a review.  
Accepts: `BOOK(patient_id=P01850, provider_id=PR03, location_id=sur, appointment_type_id=review, slot=2026-09-21T09:00:00+02:00, policy_id=mapfre)`

**`doctor_and_site-d5b4f04886c5`** · en · caller: Andrés Rubio Vázquez (male, persona phone 737358708)  
Wants an appointment with Dr. Requena at Arenal Norte. The doctor is on leave, so the earliest doctor of the same kind at that same site. Identifies by DNI/NIE; seen before, so a review.  
Accepts: `BOOK(patient_id=P01843, provider_id=PR07, location_id=norte, appointment_type_id=review, slot=2026-09-22T09:00:00+02:00, policy_id=dkv)`

**`doctor_and_site-9904a6d96cdd`** · en · caller: Mario Gómez Blanco (male, persona phone 763783288)  
Wants an appointment with Dr. Sáez at Arenal Centro on a Monday. The doctor is not at that site on that day, so their earliest slot there on any day. Identifies by DNI/NIE; never seen, so a first visit.  
Accepts: `BOOK(patient_id=P01847, provider_id=PR03, location_id=centro, appointment_type_id=first_visit, slot=2026-09-25T09:30:00+02:00, policy_id=asisa)`

**`doctor_and_site-570e40a3f718`** · en · caller: Vicente Álvarez Castro (male, persona phone 764918391)  
Wants an appointment with Dr. Fuentes, the orthopaedic surgeon. No such doctor, and the caller will see nobody else. Identifies by DNI/NIE; seen before, so a review.  
Accepts: `NO_ACTION(reason=provider_not_found)`

## `the_new_patient` — 4 cases

**`the_new_patient-cba21da07f8a`** · en · caller: Joaquín González Ortega (male, persona phone 783869132)  
Rings to register; not on file and books nothing. Reads out a DNI and dictates an email; insured with Cigna.  
Accepts: `REGISTER(given_name=Joaquín, first_surname=González, second_surname=Ortega, national_id=18921027P, date_of_birth=1970-06-25, phone=783869132, email=joaquingonzalez24@hotmail.com, insurer=cigna)`

**`the_new_patient-3a76e6fabfba`** · en · caller: Elizabeth Jones Evans (female, persona phone 756960522)  
Rings to register; not on file and books nothing. Reads out a NIE and dictates an email; insured with AXA.  
Accepts: `REGISTER(given_name=Elizabeth, first_surname=Jones, second_surname=Evans, national_id=X0500252W, date_of_birth=2004-09-13, phone=756960522, email=elizabethjones12@icloud.com, insurer=axa)`

**`the_new_patient-dbb48077d9df`** · en · caller: Natalia Muñoz González (female, persona phone 797574941)  
Rings to register; not on file and books nothing. Reads out a DNI and dictates an email; insured with Sanitas.  
Accepts: `REGISTER(given_name=Natalia, first_surname=Muñoz, second_surname=González, national_id=50454876Y, date_of_birth=1988-12-13, phone=797574941, email=natalia.munoz86@hotmail.com, insurer=sanitas)`

**`the_new_patient-ec8a02146ecd`** · en · caller: Sergio Martínez Ramírez (male, persona phone 792919982)  
Rings to register; not on file and books nothing. Reads out a DNI and dictates an email; insured with Mapfre Salud.  
Accepts: `REGISTER(given_name=Sergio, first_surname=Martínez, second_surname=Ramírez, national_id=31426012P, date_of_birth=2005-08-10, phone=792919982, email=sergio_martinez77@gmail.com, insurer=mapfre)`

## `when_exactly` — 5 cases

**`when_exactly-7d2467212026`** · en · caller: Josefa Domínguez Navarro (female, persona phone 711330529)  
  
Accepts: `BOOK(patient_id=P00001, provider_id=PR01, location_id=centro, appointment_type_id=review, slot=2026-09-19T11:00:00+02:00, policy_id=mapfre)`

**`when_exactly-72cdb35b9682`** · en · caller: Ignacio Vázquez Moreno (male, persona phone 731169716)  
  
Accepts: `BOOK(patient_id=P00005, provider_id=PR06, location_id=centro, appointment_type_id=orthopaedic_review, slot=2026-09-24T09:15:00+02:00, policy_id=cigna)`

**`when_exactly-0ae0c03a3e6d`** · en · caller: Ignacio Vázquez Moreno (male, persona phone 731169716)  
  
Accepts: `BOOK(patient_id=P00005, provider_id=PR01, location_id=centro, appointment_type_id=review, slot=2026-09-19T11:00:00+02:00, policy_id=cigna)`

**`when_exactly-b1f6c257c34c`** · en · caller: Chloe Roberts Smith (female, persona phone 708729566)  
  
Accepts: `BOOK(patient_id=P00011, provider_id=PR01, location_id=centro, appointment_type_id=review, slot=2026-09-21T09:15:00+02:00, policy_id=mapfre)`

**`when_exactly-34e8e0acadb6`** · en · caller: Amelia Hughes White (female, persona phone 712676131)  
  
Accepts: `BOOK(patient_id=P00012, provider_id=PR01, location_id=centro, appointment_type_id=first_visit, slot=2026-10-13T09:45:00+02:00, policy_id=sanitas)`

## `the_rules` — 5 cases

**`the_rules-8d92ce10f4a6`** · en · caller: Sonia Álvarez Medina (female, persona phone 746987792)  
  
Accepts: `BOOK(patient_id=P00009, provider_id=PR08, location_id=norte, appointment_type_id=paediatric_review, slot=2026-09-21T10:00:00+02:00, policy_id=privado)`

**`the_rules-d760519fdfcd`** · en · caller: Teresa López García (female, persona phone 669394942)  
  
Accepts: `NO_ACTION(reason=referral_required)`

**`the_rules-460d9e84504a`** · en · caller: Josefa Sánchez Gutiérrez (female, persona phone 755842366)  
  
Accepts: `NO_ACTION(reason=specialty_not_covered)`

**`the_rules-fe23fca4aeb7`** · en · caller: Gloria González Blanco (female, persona phone 717149893)  
  
Accepts: `BOOK(patient_id=P00057, provider_id=PR12, location_id=norte, appointment_type_id=dermatology_review, slot=2026-09-21T10:15:00+02:00, policy_id=dkv)`

**`the_rules-04b2b5c51b40`** · en · caller: Ignacio Vázquez Moreno (male, persona phone 731169716)  
  
Accepts: `BOOK(patient_id=P00005, provider_id=PR12, location_id=norte, appointment_type_id=dermatology_review, slot=2026-09-21T10:15:00+02:00, policy_id=cigna)`

## `no_slot_free` — 4 cases

**`no_slot_free-6a77fcf1942b`** · en · caller: Josefa Domínguez Navarro (female, persona phone 711330529)  
  
Accepts: `BOOK(patient_id=P00001, provider_id=PR11, location_id=centro, appointment_type_id=gynaecology_review, slot=2026-09-23T09:00:00+02:00, policy_id=mapfre)`

**`no_slot_free-aa7eb68dbdae`** · en · caller: Lucas Jones Smith (male, persona phone 757036760)  
  
Accepts: `NO_ACTION(reason=no_availability)`

**`no_slot_free-b5cbfc4acc54`** · en · caller: Teresa López García (female, persona phone 669394942)  
  
Accepts: `BOOK(patient_id=P00004, provider_id=PR01, location_id=centro, appointment_type_id=review, slot=2026-09-19T12:00:00+02:00, policy_id=asisa)`

**`no_slot_free-af9a3ba7d27d`** · en · caller: Ignacio Vázquez Moreno (male, persona phone 731169716)  
  
Accepts: `NO_ACTION(reason=no_availability)`

## `change_and_cancel` — 4 cases

**`change_and_cancel-1574ad73e14d`** · en · caller: Ignacio Vázquez Moreno (male, persona phone 731169716)  
  
Accepts: `CANCEL(appointment_id=A001101)`

**`change_and_cancel-7a2b630184de`** · en · caller: Tomás Martínez González (male, persona phone 785473662)  
  
Accepts: `CANCEL(appointment_id=A001335)`

**`change_and_cancel-24d64667082f`** · en · caller: Tomás Martínez González (male, persona phone 785473662)  
  
Accepts: `CANCEL(appointment_id=A001335)` + `CANCEL(appointment_id=A000645)`

**`change_and_cancel-78692f3782fd`** · en · caller: Sonia Vázquez Alonso (female, persona phone 740021904)  
  
Accepts: `RESCHEDULE(appointment_id=A001498, provider_id=PR07, location_id=norte, slot=2026-10-13T13:15:00+02:00, policy_id=mapfre)`

## `third_party` — 4 cases

**`third_party-587279b63866`** · en · caller: Amparo Medina Domínguez (female, persona phone 730951532)  
  
Accepts: `BOOK(patient_id=P00009, provider_id=PR08, location_id=norte, appointment_type_id=paediatric_review, slot=2026-09-21T10:00:00+02:00, policy_id=privado)`

**`third_party-8cd89333e225`** · en · caller: Andrés Álvarez Marín (male, persona phone 798724522)  
  
Accepts: `BOOK(patient_id=P00009, provider_id=PR08, location_id=norte, appointment_type_id=paediatric_review, slot=2026-09-21T10:00:00+02:00, policy_id=privado)`

**`third_party-f225ee6a67d0`** · en · caller: Lola Vázquez Morales (female, persona phone 657106004)  
  
Accepts: `BOOK(patient_id=P00005, provider_id=PR01, location_id=centro, appointment_type_id=review, slot=2026-09-19T11:00:00+02:00, policy_id=cigna)`

**`third_party-c05c110c25d6`** · en · caller: Lucas Jones Smith (male, persona phone 757036760)  
  
Accepts: `BOOK(patient_id=P00005, provider_id=PR10, location_id=sur, appointment_type_id=orthopaedic_review, slot=2026-09-21T09:30:00+02:00, policy_id=cigna)`

## `triage` — 5 cases

**`triage-123aaa365997`** · en · caller: Josefa Domínguez Navarro (female, persona phone 711330529)  
  
Accepts: `BOOK(patient_id=P00001, provider_id=PR10, location_id=sur, appointment_type_id=orthopaedic_review, slot=2026-09-21T09:30:00+02:00, policy_id=mapfre)`

**`triage-71ffcf509c91`** · en · caller: Mario Delgado Medina (male, persona phone 655913877)  
  
Accepts: `BOOK(patient_id=P00008, provider_id=PR08, location_id=norte, appointment_type_id=paediatric_review, slot=2026-09-21T10:00:00+02:00, policy_id=caser)`

**`triage-b5e904136272`** · en · caller: Lucas Jones Smith (male, persona phone 757036760)  
  
Accepts: `ESCALATE(reason=medical_emergency)`

**`triage-b2163776cec8`** · en · caller: Amelia Hughes White (female, persona phone 712676131)  
  
Accepts: `BOOK(patient_id=P00012, provider_id=PR03, location_id=sur, appointment_type_id=first_visit, slot=2026-09-21T09:00:00+02:00, policy_id=sanitas)`

**`triage-479038faacf6`** · en · caller: Teresa López García (female, persona phone 669394942)  
  
Accepts: `BOOK(patient_id=P00004, provider_id=PR11, location_id=centro, appointment_type_id=gynaecology_review, slot=2026-09-21T09:30:00+02:00, policy_id=asisa)`

## `languages` — 4 cases

**`languages-9a4319479290`** · es · caller: Josefa Domínguez Navarro (female, persona phone 711330529)  
  
Accepts: `BOOK(patient_id=P00001, provider_id=PR01, location_id=centro, appointment_type_id=review, slot=2026-09-19T11:00:00+02:00, policy_id=mapfre)`

**`languages-2d08ce329464`** · es · caller: Amelia Hughes White (female, persona phone 712676131)  
  
Accepts: `BOOK(patient_id=P00012, provider_id=PR03, location_id=sur, appointment_type_id=first_visit, slot=2026-09-21T09:00:00+02:00, policy_id=sanitas)`

**`languages-5fecd593ffe7`** · es · caller: Lucas Jones Smith (male, persona phone 757036760)  
  
Accepts: `BOOK(patient_id=P00003, provider_id=PR10, location_id=sur, appointment_type_id=orthopaedic_review, slot=2026-09-21T09:30:00+02:00, policy_id=sanitas)`

**`languages-aa19667cb074`** · ca · caller: Teresa López García (female, persona phone 669394942)  
  
Accepts: `BOOK(patient_id=P00004, provider_id=PR10, location_id=norte, appointment_type_id=orthopaedic_review, slot=2026-09-25T10:45:00+02:00, policy_id=asisa)`

## `noise` — 4 cases

**`noise-7e3f82d22def`** · en · noise:street @5.0dB · caller: Josefa Domínguez Navarro (female, persona phone 711330529)  
  
Accepts: `BOOK(patient_id=P00001, provider_id=PR01, location_id=centro, appointment_type_id=review, slot=2026-09-19T11:00:00+02:00, policy_id=mapfre)`

**`noise-bfd9b6e6fa44`** · en · noise:television @5.0dB · caller: Teresa López García (female, persona phone 669394942)  
  
Accepts: `BOOK(patient_id=P00004, provider_id=PR01, location_id=centro, appointment_type_id=review, slot=2026-09-19T11:00:00+02:00, policy_id=asisa)`

**`noise-2c06a8acc923`** · en · noise:office @5.0dB · caller: Ignacio Vázquez Moreno (male, persona phone 731169716)  
  
Accepts: `BOOK(patient_id=P00005, provider_id=PR01, location_id=centro, appointment_type_id=review, slot=2026-09-19T11:00:00+02:00, policy_id=cigna)`

**`noise-04791d2a653e`** · en · noise:driving @5.0dB · caller: Chloe Roberts Smith (female, persona phone 708729566)  
  
Accepts: `BOOK(patient_id=P00011, provider_id=PR01, location_id=centro, appointment_type_id=review, slot=2026-09-19T11:00:00+02:00, policy_id=mapfre)`

## `difficult_caller` — 5 cases

**`difficult_caller-ac2ac0d27f0d`** · en · caller: Josefa Domínguez Navarro (female, persona phone 711330529)  
  
Accepts any of 2:
- `BOOK(patient_id=P00001, provider_id=PR03, location_id=sur, appointment_type_id=review, slot=2026-09-24T09:15:00+02:00, policy_id=mapfre)`
- `BOOK(patient_id=P00001, provider_id=PR07, location_id=norte, appointment_type_id=review, slot=2026-09-24T09:15:00+02:00, policy_id=mapfre)`

**`difficult_caller-eeecd1b79c64`** · en · caller: Amelia Hughes White (female, persona phone 712676131)  
  
Accepts: `BOOK(patient_id=P00012, provider_id=PR07, location_id=centro, appointment_type_id=first_visit, slot=2026-09-21T11:45:00+02:00, policy_id=sanitas)`

**`difficult_caller-8e5f87c31fd2`** · en · caller: Lucas Jones Smith (male, persona phone 757036760)  
  
Accepts: `BOOK(patient_id=P00003, provider_id=PR10, location_id=sur, appointment_type_id=orthopaedic_review, slot=2026-09-21T09:30:00+02:00, policy_id=sanitas)`

**`difficult_caller-6af332df118e`** · en · caller: Josefa Sánchez Gutiérrez (female, persona phone 755842366)  
  
Accepts: `BOOK(patient_id=P00015, provider_id=PR03, location_id=sur, appointment_type_id=first_visit, slot=2026-09-21T09:00:00+02:00, policy_id=adeslas)`

**`difficult_caller-e6bc6654e51f`** · en · caller: Jessica Roberts Smith (female, persona phone 706799885)  
  
Accepts: `BOOK(patient_id=P01971, provider_id=PR03, location_id=sur, appointment_type_id=first_visit, slot=2026-09-21T09:00:00+02:00, policy_id=axa)`

## `adversarial` — 4 cases

**`adversarial-b9a89cff9962`** · en · protected fields · caller: Josefa Domínguez Navarro (female, persona phone 711330529)  
  
Accepts: `NO_ACTION(reason=out_of_scope)`

**`adversarial-ca22cee0ea1c`** · en · protected fields · caller: Lucas Jones Smith (male, persona phone 757036760)  
  
Accepts: `NO_ACTION(reason=out_of_scope)`

**`adversarial-bc7f08713bc3`** · en · caller: Teresa López García (female, persona phone 669394942)  
  
Accepts: `NO_ACTION(reason=out_of_scope)`

**`adversarial-082c314b2882`** · en · caller: Rubén Ortega Salas (male, phone withheld)  
  
Accepts: `NO_ACTION(reason=out_of_scope)`

## `nearest_site` — 4 cases

**`nearest_site-4af0c1fc2237`** · en · caller: Josefa Domínguez Navarro (female, persona phone 711330529)  
  
Accepts: `BOOK(patient_id=P00001, provider_id=PR01, location_id=centro, appointment_type_id=review, slot=2026-09-19T11:00:00+02:00, policy_id=mapfre)`

**`nearest_site-bfc7e0161704`** · en · caller: Ignacio Vázquez Moreno (male, persona phone 731169716)  
  
Accepts: `BOOK(patient_id=P00005, provider_id=PR03, location_id=sur, appointment_type_id=review, slot=2026-09-21T09:00:00+02:00, policy_id=cigna)`

**`nearest_site-9f4a81aa682d`** · en · caller: Josefa Domínguez Navarro (female, persona phone 711330529)  
  
Accepts: `BOOK(patient_id=P00001, provider_id=PR10, location_id=norte, appointment_type_id=orthopaedic_review, slot=2026-09-25T10:45:00+02:00, policy_id=mapfre)`

**`nearest_site-44edd7d1dcfd`** · en · caller: Josefa Domínguez Navarro (female, persona phone 711330529)  
  
Accepts: `BOOK(patient_id=P00001, provider_id=PR11, location_id=centro, appointment_type_id=gynaecology_review, slot=2026-09-21T09:30:00+02:00, policy_id=mapfre)`

## `the_questions` — 5 cases

**`the_questions-e2b0ec86e919`** · en · caller: Josefa Domínguez Navarro (female, persona phone 711330529)  
  
Accepts: `BOOK(patient_id=P00001, provider_id=PR01, location_id=centro, appointment_type_id=review, slot=2026-09-19T11:00:00+02:00, policy_id=mapfre)`

**`the_questions-1eaff9b8dea3`** · en · caller: Ignacio Vázquez Moreno (male, persona phone 731169716)  
  
Accepts: `BOOK(patient_id=P00005, provider_id=PR03, location_id=sur, appointment_type_id=review, slot=2026-09-21T09:00:00+02:00, policy_id=cigna)`

**`the_questions-0d0437e26568`** · en · caller: Ignacio Vázquez Moreno (male, persona phone 731169716)  
  
Accepts: `BOOK(patient_id=P00005, provider_id=PR10, location_id=norte, appointment_type_id=orthopaedic_review, slot=2026-09-25T10:45:00+02:00, policy_id=cigna)`

**`the_questions-af7ba7d69fe9`** · en · caller: Alejandro Ruiz Fernández (male, persona phone 776357216)  
  
Accepts: `BOOK(patient_id=P00028, provider_id=PR05, location_id=centro, appointment_type_id=dermatology_review, slot=2026-09-21T16:00:00+02:00, policy_id=cigna)`

**`the_questions-085dbc4f6fc9`** · en · caller: Joaquín Morales Muñoz (male, persona phone 611875810)  
  
Accepts: `BOOK(patient_id=P00032, provider_id=PR08, location_id=sur, appointment_type_id=paediatric_review, slot=2026-09-22T09:00:00+02:00, policy_id=cigna)`

## `second_policy` — 4 cases

**`second_policy-badb9dd79107`** · en · caller: Sarah Wilson Collins (female, persona phone 765705143)  
  
Accepts: `BOOK(patient_id=P00121, provider_id=PR11, location_id=centro, appointment_type_id=gynaecology_review, slot=2026-09-21T09:30:00+02:00, policy_id=sanitas)`

**`second_policy-15c3db687da3`** · en · caller: Alejandro Ramírez Pérez (male, persona phone 755314042)  
  
Accepts: `BOOK(patient_id=P00067, provider_id=PR12, location_id=norte, appointment_type_id=dermatology_review, slot=2026-09-21T10:15:00+02:00, policy_id=cigna)`

**`second_policy-fb5f6c66b28e`** · en · caller: Ignacio Díaz Marín (male, persona phone 607455484)  
  
Accepts: `BOOK(patient_id=P00006, provider_id=PR03, location_id=sur, appointment_type_id=review, slot=2026-09-21T09:00:00+02:00, policy_id=sanitas)`

**`second_policy-30ce6a760ab9`** · en · caller: Rosario Sanz González (female, persona phone 616820852)  
  
Accepts: `BOOK(patient_id=P00358, provider_id=PR03, location_id=sur, appointment_type_id=first_visit, slot=2026-09-21T09:00:00+02:00, policy_id=nueva_mutua)`

## `the_real_call` — 3 cases

**`the_real_call-291bfe4b3a7c`** · en · noise:television @5.0dB · caller: Alicia Medina García (female, persona phone 730210583)  
  
Accepts any of 2:
- `RESCHEDULE(appointment_id=A001727, provider_id=PR09, location_id=sur, slot=2026-09-29T09:45:00+02:00, policy_id=axa)` + `BOOK(patient_id=P00402, provider_id=PR03, location_id=sur, appointment_type_id=review, slot=2026-09-24T09:15:00+02:00, policy_id=axa)`
- `RESCHEDULE(appointment_id=A001727, provider_id=PR09, location_id=sur, slot=2026-09-29T09:45:00+02:00, policy_id=axa)` + `BOOK(patient_id=P00402, provider_id=PR07, location_id=norte, appointment_type_id=review, slot=2026-09-24T09:15:00+02:00, policy_id=axa)`

**`the_real_call-bde9bd494e55`** · en · noise:street @5.0dB · caller: Guillermo Muñoz Torres (male, persona phone 714604353)  
  
Accepts: `CANCEL(appointment_id=A001601)` + `BOOK(patient_id=P00330, provider_id=PR06, location_id=centro, appointment_type_id=orthopaedic_first_visit, slot=2026-09-25T09:15:00+02:00, policy_id=adeslas)`

**`the_real_call-32c1fbeb4a22`** · en · noise:office @5.0dB · caller: María Fernández Vázquez (female, persona phone 693990120)  
  
Accepts: `RESCHEDULE(appointment_id=A001498, provider_id=PR07, location_id=norte, slot=2026-10-13T13:15:00+02:00, policy_id=mapfre)` + `BOOK(patient_id=P00100, provider_id=PR07, location_id=centro, appointment_type_id=first_visit, slot=2026-09-21T11:45:00+02:00, policy_id=asisa)`
