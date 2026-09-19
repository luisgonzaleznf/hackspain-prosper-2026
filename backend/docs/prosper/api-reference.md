<!-- Generated from data/openapi.json (GET https://hackspain.getprosperapp.com/api/openapi.json, 2026-09-18). Live Swagger: /api/docs · ReDoc: /api/redoc on the API host. -->

# Prosper platform API — reference

`Prosper — platform API` v0.1.0. Auth: header `X-Api-Key: pk-…` on every route except `/api/v1/health` and the schema. Bad/missing/revoked key → `403 {"detail":"Invalid API key"}`.

Base URL: the API host the desk gives you (`PLATFORM_API_BASE_URL`). The public schema is served from `https://hackspain.getprosperapp.com/api/openapi.json`.

## Endpoints

| Method | Path | Summary |
|---|---|---|
| GET | `/api/v1/health` | Health —  |
| POST | `/api/v1/submit/register` | Register Patient — Put a caller who is not on file into the record. |
| POST | `/api/v1/submit/book` | Book Appointment — Book a slot for a patient already on file. |
| POST | `/api/v1/submit/reschedule` | Reschedule Appointment — Move an existing appointment to another slot. |
| POST | `/api/v1/submit/cancel` | Cancel Appointment — Cancel an existing appointment. Two cancellations are two requests. |
| POST | `/api/v1/submit/no-action` | No Action — End the call without a write, carrying the reason. |
| POST | `/api/v1/submit/escalate` | Escalate to Human — Hand the call to a human, carrying the reason. |
| GET | `/api/v1/directory` | Search Patient —  |
| GET | `/api/v1/patients/{patient_id}/appointments` | List Patient Appointments —  |
| GET | `/api/v1/availability` | Search Availability —  |
| GET | `/api/v1/clinic` | Clinic Overview — The whole catalogue in one call: the bookable window, the standing restrictions and their decline reasons, and every provider, specialty, appointment type, location and insurance plan. |
| GET | `/api/v1/providers` | List Providers — Every provider, with their specialty, languages, the types they perform, where and when they sit, the plans they take, and any leave. |
| GET | `/api/v1/locations` | List Locations — Every site, its address and opening hours, who sits there, and which plans cover it. |
| GET | `/api/v1/specialties` | List Specialties — Every specialty, its age window, whether it needs a referral, and which plans cover it. The ids are what `/availability?specialty_id=` takes. |
| GET | `/api/v1/appointment-types` | List Appointment Types — Every appointment type, its duration, and which patient it is for. The type follows the patient's history and the specialty, never the request. |
| GET | `/api/v1/insurance-plans` | List Insurance Plans — Every plan, what it covers and where, and which providers take it. A patient's plan on file comes back from `/directory`; a second one they may hold is nowhere in the data, and only the call reveals it. |
| GET | `/api/v1/submissions` | List Submissions —  |

### GET `/api/v1/health` — Health

_No API key required._

- `200` Successful Response

### POST `/api/v1/submit/register` — Register Patient

Put a caller who is not on file into the record.

Body: `RegisterRequest`

- `200` Successful Response → `SubmitResponse`
- `404` No call with this `call_id` is registered to your key.
- `410` The submission window for this call has closed.
- `422` Validation Error → `HTTPValidationError`

### POST `/api/v1/submit/book` — Book Appointment

Book a slot for a patient already on file.

Body: `BookRequest`

- `200` Successful Response → `SubmitResponse`
- `404` No call with this `call_id` is registered to your key.
- `410` The submission window for this call has closed.
- `422` Validation Error → `HTTPValidationError`

### POST `/api/v1/submit/reschedule` — Reschedule Appointment

Move an existing appointment to another slot.

Body: `RescheduleRequest`

- `200` Successful Response → `SubmitResponse`
- `404` No call with this `call_id` is registered to your key.
- `410` The submission window for this call has closed.
- `422` Validation Error → `HTTPValidationError`

### POST `/api/v1/submit/cancel` — Cancel Appointment

Cancel an existing appointment. Two cancellations are two requests.

Body: `CancelRequest`

- `200` Successful Response → `SubmitResponse`
- `404` No call with this `call_id` is registered to your key.
- `410` The submission window for this call has closed.
- `422` Validation Error → `HTTPValidationError`

### POST `/api/v1/submit/no-action` — No Action

End the call without a write, carrying the reason.

Body: `NoActionRequest`

- `200` Successful Response → `SubmitResponse`
- `404` No call with this `call_id` is registered to your key.
- `410` The submission window for this call has closed.
- `422` Validation Error → `HTTPValidationError`

### POST `/api/v1/submit/escalate` — Escalate to Human

Hand the call to a human, carrying the reason.

Body: `EscalateRequest`

- `200` Successful Response → `SubmitResponse`
- `404` No call with this `call_id` is registered to your key.
- `410` The submission window for this call has closed.
- `422` Validation Error → `HTTPValidationError`

### GET `/api/v1/directory` — Search Patient

| Param | In | Required | Type | Description | Example |
|---|---|---|---|---|---|
| `name` | query |  | string (nullable) | Full or partial name, compared after normalization. | `"Marta Ruiz Gomez"` |
| `national_id` | query |  | string (nullable) | DNI or NIE, as dictated. | `"12345678Z"` |
| `phone` | query |  | string (nullable) | As dictated; the digits are what is compared. | `"612345678"` |
| `date_of_birth` | query |  | string (date) (nullable) | ISO date, used to tell namesakes apart. | `"1988-03-14"` |

- `200` Successful Response → `DirectoryResponse`
- `422` Validation Error → `HTTPValidationError`

### GET `/api/v1/patients/{patient_id}/appointments` — List Patient Appointments

| Param | In | Required | Type | Description | Example |
|---|---|---|---|---|---|
| `patient_id` | path | yes | string | The patient's id from the directory lookup. | `"P00042"` |
| `when` | query |  | `AppointmentWindow` | Which half of the diary to return: what the patient still has ahead of them, the visits they have already been to, or both. Only an upcoming appointment can be cancelled or moved. |  |

- `200` Successful Response → `AppointmentsResponse`
- `422` Validation Error → `HTTPValidationError`

### GET `/api/v1/availability` — Search Availability

| Param | In | Required | Type | Description | Example |
|---|---|---|---|---|---|
| `date_from` | query | yes | string (date) | First day of the window, inclusive. | `"2026-09-21"` |
| `date_to` | query | yes | string (date) | Last day of the window, inclusive. | `"2026-09-25"` |
| `provider_id` | query |  | string (nullable) | Only this provider's slots. | `"PR05"` |
| `specialty_id` | query |  | string (nullable) | Only providers of this specialty. | `"dermatology"` |
| `location_id` | query |  | string (nullable) | Only slots at this site. | `"sur"` |
| `patient_id` | query |  | string (nullable) | Only what this patient is eligible for: their age, history and plans are applied, so a slot listed here is one they can take. | `"P00042"` |
| `insurer` | query |  | array of `Insurer` (nullable) | Only slots these plans cover. Repeat it for several. | `["sanitas"]` |

- `200` Successful Response → `AvailabilityResponse`
- `422` Validation Error → `HTTPValidationError`

### GET `/api/v1/clinic` — Clinic Overview

The whole catalogue in one call: the bookable window, the standing
restrictions and their decline reasons, and every provider, specialty,
appointment type, location and insurance plan.

- `200` Successful Response → `ClinicResponse`

### GET `/api/v1/providers` — List Providers

Every provider, with their specialty, languages, the types they perform,
where and when they sit, the plans they take, and any leave.

- `200` Successful Response → `ProvidersResponse`

### GET `/api/v1/locations` — List Locations

Every site, its address and opening hours, who sits there, and which
plans cover it.

- `200` Successful Response → `LocationsResponse`

### GET `/api/v1/specialties` — List Specialties

Every specialty, its age window, whether it needs a referral, and which
plans cover it. The ids are what `/availability?specialty_id=` takes.

- `200` Successful Response → `SpecialtiesResponse`

### GET `/api/v1/appointment-types` — List Appointment Types

Every appointment type, its duration, and which patient it is for. The
type follows the patient's history and the specialty, never the request.

- `200` Successful Response → `AppointmentTypesResponse`

### GET `/api/v1/insurance-plans` — List Insurance Plans

Every plan, what it covers and where, and which providers take it. A
patient's plan on file comes back from `/directory`; a second one they may
hold is nowhere in the data, and only the call reveals it.

- `200` Successful Response → `InsurancePlansResponse`

### GET `/api/v1/submissions` — List Submissions

| Param | In | Required | Type | Description | Example |
|---|---|---|---|---|---|
| `limit` | query |  | integer | How many of your most recent records to return. |  |

- `200` Successful Response → `RecordsResponse`
- `422` Validation Error → `HTTPValidationError`

## Schemas

### `AppointmentOut`

| Field | Type | Req | Description | Example |
|---|---|---|---|---|
| `appointment_id` | string | ✓ |  |  |
| `patient_id` | string | ✓ |  |  |
| `provider_id` | string | ✓ |  |  |
| `location_id` | string | ✓ |  |  |
| `appointment_type_id` | string | ✓ |  |  |
| `start_time` | string (date-time) | ✓ |  |  |
| `duration_minutes` | integer | ✓ |  |  |

### `AppointmentTypeOut`

| Field | Type | Req | Description | Example |
|---|---|---|---|---|
| `id` | string | ✓ |  |  |
| `name` | string | ✓ |  |  |
| `duration_minutes` | integer | ✓ |  |  |
| `new_patient_requirement` | string | ✓ |  |  |
| `guidance` | string | ✓ |  |  |

### `AppointmentTypesResponse`

| Field | Type | Req | Description | Example |
|---|---|---|---|---|
| `appointment_types` | array of `ClinicAppointmentTypeResponse` | ✓ |  |  |

### `AppointmentWindow`

Values: `upcoming`, `past`, `all`

### `AppointmentsResponse`

| Field | Type | Req | Description | Example |
|---|---|---|---|---|
| `appointments` | array of `AppointmentOut` | ✓ |  |  |

### `AvailabilityResponse`

| Field | Type | Req | Description | Example |
|---|---|---|---|---|
| `providers` | array of `ProviderOut` | ✓ |  |  |
| `appointment_type` | `AppointmentTypeOut` | ✓ |  |  |
| `slots` | array of `SlotOut` | ✓ |  |  |
| `blocked` | array of `BlockedOut` | ✓ |  |  |

### `BlockedOut`

| Field | Type | Req | Description | Example |
|---|---|---|---|---|
| `provider_id` | string | ✓ |  |  |
| `restriction` | string | ✓ |  |  |

### `BookAction`

| Field | Type | Req | Description | Example |
|---|---|---|---|---|
| `action` | string |  | const `BOOK`. |  |
| `patient_id` | string | ✓ |  |  |
| `provider_id` | string | ✓ |  |  |
| `location_id` | string | ✓ |  |  |
| `appointment_type_id` | string | ✓ |  |  |
| `slot` | string (date-time) | ✓ |  |  |
| `policy_id` | `Insurer` | ✓ |  |  |

### `BookRequest`

A slot for a patient already on file.

| Field | Type | Req | Description | Example |
|---|---|---|---|---|
| `call_id` | string | ✓ | The `callSid` of the `start` message that opened the call. Never minted by the team. | `"3fa85f64-5717-4562-b3fc-2c963f66afa6"` |
| `patient_id` | string | ✓ | The patient's id from the directory lookup -- never from what the caller said. | `"P00042"` |
| `provider_id` | string | ✓ | The provider who will see the patient, from the directory. | `"PR05"` |
| `location_id` | string | ✓ | The site the appointment is at, from availability. | `"sur"` |
| `appointment_type_id` | string | ✓ | The kind of visit, from availability. | `"review"` |
| `slot` | string (date-time) | ✓ | The appointment's start, with an explicit timezone offset. Compared in Europe/Madrid to the exact minute. | `"2026-09-24T16:30:00+02:00"` |
| `policy_id` | `Insurer` | ✓ | Which of the patient's plans the appointment is billed against. A patient may hold two, and only one may cover what they asked for. | `"sanitas"` |

```json
{
  "appointment_type_id": "review",
  "call_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "location_id": "sur",
  "patient_id": "P00042",
  "policy_id": "sanitas",
  "provider_id": "PR05",
  "slot": "2026-09-24T16:30:00+02:00"
}
```

### `CancelAction`

| Field | Type | Req | Description | Example |
|---|---|---|---|---|
| `action` | string |  | const `CANCEL`. |  |
| `appointment_id` | string | ✓ |  |  |

### `CancelRequest`

One existing appointment cancelled. Two cancellations are two requests.

| Field | Type | Req | Description | Example |
|---|---|---|---|---|
| `call_id` | string | ✓ | The `callSid` of the `start` message that opened the call. Never minted by the team. | `"3fa85f64-5717-4562-b3fc-2c963f66afa6"` |
| `appointment_id` | string | ✓ | An appointment already on file, from the patient's appointments lookup. There is no other source for one. | `"A000123"` |

```json
{
  "appointment_id": "A000123",
  "call_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6"
}
```

### `ClinicAppointmentTypeResponse`

| Field | Type | Req | Description | Example |
|---|---|---|---|---|
| `id` | string | ✓ |  |  |
| `name` | string | ✓ |  |  |
| `duration_minutes` | integer | ✓ |  |  |
| `new_patient_requirement` | string | ✓ |  |  |
| `guidance` | string | ✓ |  |  |
| `provider_names` | array of string | ✓ |  |  |
| `specialty_id` | string (nullable) | ✓ |  |  |
| `specialty_name` | string (nullable) | ✓ |  |  |

### `ClinicCalendarResponse`

The bookable window, as `/api/v1/availability` accepts it.

| Field | Type | Req | Description | Example |
|---|---|---|---|---|
| `starts` | string (date) | ✓ |  |  |
| `ends` | string (date) | ✓ |  |  |
| `max_span_days` | integer | ✓ |  |  |
| `slot_minutes` | integer | ✓ |  |  |
| `closure_days` | array of string (date) | ✓ |  |  |
| `appointment_count` | integer | ✓ |  |  |

### `ClinicDayResponse`

| Field | Type | Req | Description | Example |
|---|---|---|---|---|
| `weekday` | string | ✓ |  |  |
| `intervals` | array of string | ✓ |  |  |

### `ClinicInsurerRef`

| Field | Type | Req | Description | Example |
|---|---|---|---|---|
| `id` | string | ✓ |  |  |
| `name` | string | ✓ |  |  |

### `ClinicLeaveResponse`

| Field | Type | Req | Description | Example |
|---|---|---|---|---|
| `start` | string (date) | ✓ |  |  |
| `end` | string (date) | ✓ |  |  |
| `reason` | string | ✓ |  |  |

### `ClinicLocationResponse`

| Field | Type | Req | Description | Example |
|---|---|---|---|---|
| `id` | string | ✓ |  |  |
| `name` | string | ✓ |  |  |
| `address` | string | ✓ |  |  |
| `latitude` | number | ✓ |  |  |
| `longitude` | number | ✓ |  |  |
| `hours` | array of `ClinicDayResponse` | ✓ |  |  |
| `provider_names` | array of string | ✓ |  |  |
| `covered_by` | array of `ClinicInsurerRef` | ✓ |  |  |
| `not_covered_by` | array of `ClinicInsurerRef` | ✓ |  |  |

### `ClinicPlanResponse`

| Field | Type | Req | Description | Example |
|---|---|---|---|---|
| `id` | string | ✓ |  |  |
| `name` | string | ✓ |  |  |
| `covered_specialty_names` | array of string | ✓ |  |  |
| `uncovered_specialty_names` | array of string | ✓ |  |  |
| `covered_location_names` | array of string | ✓ |  |  |
| `uncovered_location_names` | array of string | ✓ |  |  |
| `accepted_by` | array of string | ✓ |  |  |
| `refused_by` | array of string | ✓ |  |  |
| `holders` | integer | ✓ |  |  |

### `ClinicProviderResponse`

| Field | Type | Req | Description | Example |
|---|---|---|---|---|
| `id` | string | ✓ |  |  |
| `name` | string | ✓ |  |  |
| `specialty_id` | string | ✓ |  |  |
| `specialty_name` | string | ✓ |  |  |
| `languages` | array of string | ✓ |  |  |
| `appointment_type_names` | array of string | ✓ |  |  |
| `location_names` | array of string | ✓ |  |  |
| `schedules` | array of `ClinicScheduleResponse` | ✓ |  |  |
| `accepted_insurers` | array of `ClinicInsurerRef` | ✓ |  |  |
| `refused_insurers` | array of `ClinicInsurerRef` | ✓ |  |  |
| `leave` | `ClinicLeaveResponse` (nullable) | ✓ |  |  |

### `ClinicResponse`

The shape of the clinic, without a single patient in it: the patients come a page at a time from their own endpoint.

| Field | Type | Req | Description | Example |
|---|---|---|---|---|
| `clinic_name` | string | ✓ |  |  |
| `patient_count` | integer | ✓ |  |  |
| `calendar` | `ClinicCalendarResponse` | ✓ |  |  |
| `restrictions` | array of `ClinicRestrictionResponse` | ✓ |  |  |
| `providers` | array of `ClinicProviderResponse` | ✓ |  |  |
| `specialties` | array of `ClinicSpecialtyResponse` | ✓ |  |  |
| `appointment_types` | array of `ClinicAppointmentTypeResponse` | ✓ |  |  |
| `locations` | array of `ClinicLocationResponse` | ✓ |  |  |
| `plans` | array of `ClinicPlanResponse` | ✓ |  |  |

### `ClinicRestrictionResponse`

| Field | Type | Req | Description | Example |
|---|---|---|---|---|
| `id` | string | ✓ |  |  |
| `title` | string | ✓ |  |  |
| `explanation` | string | ✓ |  |  |

### `ClinicScheduleResponse`

When one provider is open at one location — the `location_hours` restriction, which is the one a slot request fails on.

| Field | Type | Req | Description | Example |
|---|---|---|---|---|
| `location_id` | string | ✓ |  |  |
| `location_name` | string | ✓ |  |  |
| `days` | array of `ClinicDayResponse` | ✓ |  |  |

### `ClinicSpecialtyResponse`

| Field | Type | Req | Description | Example |
|---|---|---|---|---|
| `id` | string | ✓ |  |  |
| `name` | string | ✓ |  |  |
| `min_age_months` | integer | ✓ |  |  |
| `max_age_months` | integer (nullable) | ✓ |  |  |
| `referral_required` | boolean | ✓ |  |  |
| `provider_names` | array of string | ✓ |  |  |
| `covered_by` | array of `ClinicInsurerRef` | ✓ |  |  |
| `not_covered_by` | array of `ClinicInsurerRef` | ✓ |  |  |

### `DirectoryResponse`

| Field | Type | Req | Description | Example |
|---|---|---|---|---|
| `matches` | array of `PatientMatchOut` | ✓ |  |  |

### `EscalateAction`

| Field | Type | Req | Description | Example |
|---|---|---|---|---|
| `action` | string |  | const `ESCALATE`. |  |
| `reason` | `OutcomeReason` | ✓ |  |  |

### `EscalateRequest`

The call handed to a human, and the reason is the answer.

| Field | Type | Req | Description | Example |
|---|---|---|---|---|
| `call_id` | string | ✓ | The `callSid` of the `start` message that opened the call. Never minted by the team. | `"3fa85f64-5717-4562-b3fc-2c963f66afa6"` |
| `reason` | `OutcomeReason` | ✓ | Why the call ended without a write, from the published closed vocabulary. The first eleven values mirror the clinic's own restrictions one-for-one. |  |

```json
{
  "call_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "reason": "medical_emergency"
}
```

### `HTTPValidationError`

| Field | Type | Req | Description | Example |
|---|---|---|---|---|
| `detail` | array of `ValidationError` |  |  |  |

### `InsurancePlansResponse`

| Field | Type | Req | Description | Example |
|---|---|---|---|---|
| `plans` | array of `ClinicPlanResponse` | ✓ |  |  |

### `Insurer`

Values: `sanitas`, `adeslas`, `dkv`, `asisa`, `mapfre`, `caser`, `cigna`, `axa`, `nueva_mutua`, `privado`

### `LocationsResponse`

| Field | Type | Req | Description | Example |
|---|---|---|---|---|
| `locations` | array of `ClinicLocationResponse` | ✓ |  |  |

### `NewPatient`

Demographics captured over the phone for someone not yet on file.  Scored field by field after normalization. ``national_id`` re-derives its own check letter, which is what separates a misheard digit from an invented one. ``email`` is the one field with no check digit at all: a letter misheard in the local part is just a different address.

| Field | Type | Req | Description | Example |
|---|---|---|---|---|
| `given_name` | string | ✓ |  |  |
| `first_surname` | string | ✓ |  |  |
| `second_surname` | string | ✓ |  |  |
| `national_id` | string | ✓ |  |  |
| `date_of_birth` | string (date) | ✓ |  |  |
| `phone` | string | ✓ |  |  |
| `email` | string | ✓ |  |  |
| `insurer` | `Insurer` | ✓ |  |  |

### `NoAction`

| Field | Type | Req | Description | Example |
|---|---|---|---|---|
| `action` | string |  | const `NO_ACTION`. |  |
| `reason` | `OutcomeReason` | ✓ |  |  |

### `NoActionRequest`

The call ended with no write, and the reason is the answer.

| Field | Type | Req | Description | Example |
|---|---|---|---|---|
| `call_id` | string | ✓ | The `callSid` of the `start` message that opened the call. Never minted by the team. | `"3fa85f64-5717-4562-b3fc-2c963f66afa6"` |
| `reason` | `OutcomeReason` | ✓ | Why the call ended without a write, from the published closed vocabulary. The first eleven values mirror the clinic's own restrictions one-for-one. |  |

```json
{
  "call_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "reason": "no_availability"
}
```

### `OutcomeReason`

Every reason a call can end without a booking.  Closed, and published in the rulebook. The first eleven mirror ``core/clinic``'s ``RestrictionKind`` one-for-one -- a test asserts that, so a new clinic rule cannot appear without a reason a team can report it with. The rest cover endings that are not about a clinic rule at all.

Values: `not_eligible_age`, `referral_required`, `provider_not_in_network`, `specialty_not_covered`, `location_not_covered`, `insurer_referral_required`, `allowance_exhausted`, `provider_on_leave`, `location_hours`, `type_not_offered`, `patient_history`, `no_availability`, `clinic_closed`, `patient_not_found`, `provider_not_found`, `caller_not_authorised`, `out_of_scope`, `medical_emergency`

### `PatientMatchOut`

| Field | Type | Req | Description | Example |
|---|---|---|---|---|
| `patient_id` | string | ✓ |  |  |
| `given_name` | string | ✓ |  |  |
| `first_surname` | string | ✓ |  |  |
| `second_surname` | string | ✓ |  |  |
| `national_id` | string | ✓ |  |  |
| `date_of_birth` | string (date) | ✓ |  |  |
| `phone` | string | ✓ |  |  |
| `sex` | string | ✓ |  |  |
| `has_visited_before` | boolean | ✓ |  |  |
| `insurer` | string | ✓ |  |  |
| `referrals` | array of string | ✓ |  |  |
| `note` | string | ✓ |  |  |
| `match_score` | number | ✓ |  |  |
| `matched_fields` | array of string | ✓ |  |  |

### `ProviderOut`

| Field | Type | Req | Description | Example |
|---|---|---|---|---|
| `id` | string | ✓ |  |  |
| `name` | string | ✓ |  |  |
| `specialty_id` | string | ✓ |  |  |
| `languages` | array of string | ✓ |  |  |
| `accepted_insurers` | array of string | ✓ |  |  |
| `locations` | array of string | ✓ |  |  |
| `on_leave_until` | string (nullable) | ✓ |  |  |

### `ProvidersResponse`

| Field | Type | Req | Description | Example |
|---|---|---|---|---|
| `providers` | array of `ClinicProviderResponse` | ✓ |  |  |

### `RecordResponse`

| Field | Type | Req | Description | Example |
|---|---|---|---|---|
| `call_id` | string | ✓ |  |  |
| `record` | `SubmittedOutcome` | ✓ |  |  |
| `received_at` | string (date-time) | ✓ |  |  |

### `RecordsResponse`

| Field | Type | Req | Description | Example |
|---|---|---|---|---|
| `submissions` | array of `RecordResponse` | ✓ |  |  |

### `RegisterAction`

Put a caller the directory does not know on file. Nothing is booked: the record is the whole answer.

| Field | Type | Req | Description | Example |
|---|---|---|---|---|
| `action` | string |  | const `REGISTER`. |  |
| `new_patient` | `NewPatient` | ✓ |  |  |

### `RegisterRequest`

A caller the directory does not know. Nothing is booked: the demographics are the answer, every field scored after normalization.

| Field | Type | Req | Description | Example |
|---|---|---|---|---|
| `call_id` | string | ✓ | The `callSid` of the `start` message that opened the call. Never minted by the team. | `"3fa85f64-5717-4562-b3fc-2c963f66afa6"` |
| `given_name` | string | ✓ |  | `"Ana"` |
| `first_surname` | string | ✓ |  | `"García"` |
| `second_surname` | string | ✓ |  | `"López"` |
| `national_id` | string | ✓ | DNI or NIE. The check letter is re-derived from the digits, so a letter that does not match them is a 422. | `"12345678Z"` |
| `date_of_birth` | string (date) | ✓ |  | `"1988-03-14"` |
| `phone` | string | ✓ | As dictated; compared after normalization. | `"+34612345678"` |
| `email` | string | ✓ | As dictated; compared after normalization. | `"ana.garcia@gmail.com"` |
| `insurer` | `Insurer` | ✓ | The plan the new patient is registered under. | `"adeslas"` |

```json
{
  "call_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "date_of_birth": "1988-03-14",
  "email": "ana.garcia@gmail.com",
  "first_surname": "García",
  "given_name": "Ana",
  "insurer": "adeslas",
  "national_id": "12345678Z",
  "phone": "+34612345678",
  "second_surname": "López"
}
```

### `RescheduleAction`

| Field | Type | Req | Description | Example |
|---|---|---|---|---|
| `action` | string |  | const `RESCHEDULE`. |  |
| `appointment_id` | string | ✓ |  |  |
| `provider_id` | string | ✓ |  |  |
| `location_id` | string | ✓ |  |  |
| `slot` | string (date-time) | ✓ |  |  |
| `policy_id` | `Insurer` | ✓ |  |  |

### `RescheduleRequest`

An existing appointment moved to another slot.

| Field | Type | Req | Description | Example |
|---|---|---|---|---|
| `call_id` | string | ✓ | The `callSid` of the `start` message that opened the call. Never minted by the team. | `"3fa85f64-5717-4562-b3fc-2c963f66afa6"` |
| `appointment_id` | string | ✓ | An appointment already on file, from the patient's appointments lookup. There is no other source for one. | `"A000123"` |
| `provider_id` | string | ✓ | The provider who will see the patient, from the directory. | `"PR05"` |
| `location_id` | string | ✓ | The site the appointment is at, from availability. | `"sur"` |
| `slot` | string (date-time) | ✓ | The appointment's start, with an explicit timezone offset. Compared in Europe/Madrid to the exact minute. | `"2026-09-24T16:30:00+02:00"` |
| `policy_id` | `Insurer` | ✓ | Which of the patient's plans the appointment is billed against. A patient may hold two, and only one may cover what they asked for. | `"sanitas"` |

```json
{
  "appointment_id": "A000123",
  "call_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "location_id": "sur",
  "policy_id": "sanitas",
  "provider_id": "PR05",
  "slot": "2026-09-24T16:30:00+02:00"
}
```

### `SlotOut`

| Field | Type | Req | Description | Example |
|---|---|---|---|---|
| `provider_id` | string | ✓ |  |  |
| `provider_name` | string | ✓ |  |  |
| `specialty_id` | string | ✓ |  |  |
| `location_id` | string | ✓ |  |  |
| `appointment_type_id` | string | ✓ |  |  |
| `start_time` | string (date-time) | ✓ |  |  |
| `duration_minutes` | integer | ✓ |  |  |
| `payable_with` | array of string | ✓ |  |  |

### `SpecialtiesResponse`

| Field | Type | Req | Description | Example |
|---|---|---|---|---|
| `specialties` | array of `ClinicSpecialtyResponse` | ✓ |  |  |

### `SubmitResponse`

The call's record so far, so a second action can see the first.

| Field | Type | Req | Description | Example |
|---|---|---|---|---|
| `call_id` | string | ✓ | The call this record belongs to. |  |
| `received_at` | string (date-time) | ✓ | When this action was accepted, in UTC. |  |
| `record` | `SubmittedOutcome` | ✓ | Every action accepted for this call so far, this one included, each under its verb. A `REGISTER` nests its fields under `new_patient` here. |  |

```json
{
  "call_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "received_at": "2026-09-18T10:41:07.512Z",
  "record": {
    "actions": [
      {
        "action": "BOOK",
        "appointment_type_id": "review",
        "location_id": "sur",
        "patient_id": "P00042",
        "policy_id": "sanitas",
        "provider_id": "PR05",
        "slot": "2026-09-24T16:30:00+02:00"
      }
    ]
  }
}
```

### `SubmittedOutcome`

| Field | Type | Req | Description | Example |
|---|---|---|---|---|
| `actions` | array of any | ✓ |  |  |

### `ValidationError`

| Field | Type | Req | Description | Example |
|---|---|---|---|---|
| `loc` | array of string \| integer | ✓ |  |  |
| `msg` | string | ✓ |  |  |
| `type` | string | ✓ |  |  |
