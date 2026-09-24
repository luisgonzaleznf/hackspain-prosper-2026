"""The tools the voice model calls, model-agnostic.

    TOOLS                          flat JSON-schema function specs: {"name","description","parameters"}
    await call_tool(session, name, args) -> dict      never raises; errors come back as {"error": ...}
    register_pipecat_tools(llm, session) -> ToolsSchema   convenience for pipecat LLM services

Lookups hit the live clinic API. The record_* tools only STAGE an outcome (see session.py), and
only after checking it against what this call actually looked up: a patient from find_patient,
a slot from search_availability, an appointment from list_appointments. That is the
"check before any write" invariant: the model cannot report something the clinic never offered.
"""

import re
import unicodedata
from datetime import date, datetime, timedelta
from difflib import SequenceMatcher
from math import asin, cos, isfinite, radians, sin, sqrt
from typing import Any

from app import appointment_email, clinic, customer_accounts, directions, prosper
from app.session import CallSession

REASONS = [
    # the clinic's own restrictions, one-for-one
    "not_eligible_age",
    "referral_required",
    "provider_not_in_network",
    "specialty_not_covered",
    "location_not_covered",
    "insurer_referral_required",
    "allowance_exhausted",
    "provider_on_leave",
    "location_hours",
    "type_not_offered",
    "patient_history",
    # endings that are not about a clinic rule
    "no_availability",
    "clinic_closed",
    "patient_not_found",
    "provider_not_found",
    "caller_not_authorised",
    "out_of_scope",
    "medical_emergency",
]
INSURERS = [
    "sanitas",
    "adeslas",
    "dkv",
    "asisa",
    "mapfre",
    "caser",
    "cigna",
    "axa",
    "nueva_mutua",
    "privado",
]
SPECIALTIES = [
    "general_practice",
    "paediatrics",
    "dermatology",
    "orthopaedics",
    "gynaecology",
    "physiotherapy",
]
LOCATIONS = ["centro", "norte", "sur"]
# Languages a doctor may speak (catalogue codes). Every provider speaks Spanish; only four
# speak Catalan (problem 11: "the provider you book has to speak their language").
LANGUAGE_NAMES = {
    "es": "Spanish",
    "ca": "Catalan",
    "en": "English",
    "eu": "Basque",
    "gl": "Galician",
}
# Languages the filter actually means something for. English and Spanish are no-ops (every
# doctor speaks Spanish; 69 of 73 public cases are English callers, and a realtime model does
# not enforce the schema's enum) so a model passing language="en" just because the call is in
# English must not hide every doctor who doesn't happen to list "en".
LANGUAGES = ["ca", "eu", "gl"]
REGISTER_FIELDS = [
    "given_name",
    "first_surname",
    "second_surname",
    "national_id",
    "date_of_birth",
    "phone",
    "email",
    "insurer",
]
MAX_SLOTS_SHOWN = 8
_NAME_TITLES = {"d", "dr", "dra", "doctor", "doctora"}


def _str(desc: str, **extra: Any) -> dict:
    return {"type": "string", "description": desc, **extra}


_SLOT = _str(
    "The slot's start exactly as search_availability returned it, e.g. 2026-09-21T09:30:00+02:00."
)
_POLICY = _str(
    "The plan this is billed against: the patient's plan on file, or a second plan the caller "
    "told you about. It must be in the slot's payable_with.",
    enum=INSURERS,
)

EMAIL_TOOLS: list[dict] = [
    {
        "name": "set_appointment_email",
        "description": (
            "Only when an identified patient has no usable email on file, capture the caller's "
            "dictated email for that patient's booking or move. Otherwise the backend automatically "
            "uses the patient record and ignores any supplied replacement address. "
            "Read the returned address back and wait for explicit confirmation before calling "
            "confirm_appointment_email. Every correction resets confirmation. Pass an empty "
            "email to withdraw consent. This does not send anything or update the patient record."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "patient_id": _str("Identified patient whose booking or move this email covers."),
                "email": _str(
                    "Exact dictated address using @ and dots; empty string to decline email."
                ),
            },
            "required": ["patient_id", "email"],
        },
    },
    {
        "name": "confirm_appointment_email",
        "description": (
            "Only for a patient with no usable email on file. Use after reading back the full "
            "address from set_appointment_email and hearing "
            "the caller explicitly confirm it. Pass that exact address. Sending waits until the "
            "call ends and uses only the final successful booking or move. Never claim it is sent yet."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "patient_id": _str("The patient specified in set_appointment_email."),
                "email": _str("The exact address the caller just confirmed after the read-back."),
            },
            "required": ["patient_id", "email"],
        },
    },
]

TOOLS: list[dict] = [
    {
        "name": "get_site_directions",
        "description": (
            "Get a live driving/car or taxi route overview to a known clinic site. Estimate "
            "origin coordinates from the caller's Madrid street, landmark, district or town, "
            "as with rank_sites_by_distance; never ask for numeric coordinates. Clarify an "
            "ambiguous origin first. Give the returned roads, approximate duration and verified "
            "destination address. Estimates exclude live traffic and are not walking or "
            "public transport directions. Never invent an entrance, floor or parking. "
            "If routing is unavailable, give the destination address for maps or a taxi; "
            "never read the URL aloud or claim to send a link. "
            "preserve the appointment."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "latitude": {"type": "number", "minimum": -90, "maximum": 90},
                "longitude": {"type": "number", "minimum": -180, "maximum": 180},
                "location_id": _str("Destination clinic site.", enum=LOCATIONS),
            },
            "required": ["latitude", "longitude", "location_id"],
        },
    },
    {
        "name": "rank_sites_by_distance",
        "description": (
            "Rank sites offering a specialty by straight-line distance from approximate "
            "coordinates you estimate using your knowledge of the caller's Madrid street, "
            "landmark, district or nearby town. Never ask the caller for numeric coordinates. "
            "Clarify an unknown or ambiguous place with a landmark or district; describe "
            "proximity as rough, never a measured distance. This does "
            "not check patient eligibility or slots; search_availability at each candidate site."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "latitude": {"type": "number", "minimum": -90, "maximum": 90},
                "longitude": {"type": "number", "minimum": -180, "maximum": 180},
                "specialty_id": _str("Requested specialty.", enum=SPECIALTIES),
            },
            "required": ["latitude", "longitude", "specialty_id"],
        },
    },
    {
        "name": "resolve_names",
        "description": (
            "Resolve a caller's possibly misheard doctor and/or site against the clinic catalogue. "
            "Accent- and case-insensitive, and matches fragments such as a partial surname. Call "
            "this before searching when the caller's wording is not an exact catalogue name. If "
            "`confident` is false, ask the caller the returned `question` and wait for their choice; "
            "never search or book on a guess."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "doctor": _str("The doctor's name exactly as heard, including any fragments."),
                "site": _str("The site's name exactly as heard, including any fragments."),
            },
            "required": [],
        },
    },
    {
        "name": "find_patient",
        "description": (
            "Look the patient up in the clinic records. Pass everything the caller gave you. "
            "`name` alone is a fuzzy search that returns look-alikes; national_id, phone and "
            "date_of_birth must match exactly, so a wrong one returns nothing. Always confirm "
            "identity on a second field before acting on a record."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "name": _str("Full or partial name as the caller said it."),
                "national_id": _str("DNI or NIE, e.g. 12345678Z or X1234567L."),
                "phone": _str("Phone number, any format."),
                "date_of_birth": _str("ISO date YYYY-MM-DD."),
            },
            "required": [],
        },
    },
    {
        "name": "list_appointments",
        "description": (
            "The patient's diary. 'upcoming' (default) is what can still be moved or cancelled "
            "and the only source of an appointment_id; 'past' is visit history to read back."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "patient_id": _str("From find_patient."),
                "when": _str("Which half of the diary.", enum=["upcoming", "past", "all"]),
            },
            "required": ["patient_id"],
        },
    },
    {
        "name": "search_availability",
        "description": (
            "Real free slots, earliest first. Give specialty_id or provider_id, and always "
            "patient_id once you know the patient: it applies their age, history, referrals and "
            "plan, so what comes back is what they can take. The response names the one "
            "appointment_type that fits and, in `blocked`, the rule that stopped any provider. "
            "Today is never bookable; windows are capped at 14 days."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "date_from": _str("First day, YYYY-MM-DD (inclusive). Tomorrow at the earliest."),
                "date_to": _str(
                    "Last day, YYYY-MM-DD (inclusive). At most 13 days after date_from."
                ),
                "after": _str(
                    "Only include slots starting after this ISO datetime; for a reschedule, use "
                    "the existing appointment's start time."
                ),
                "specialty_id": _str("Which specialty.", enum=SPECIALTIES),
                "provider_id": _str("A specific provider, e.g. PR03."),
                "location_id": _str("Only this site.", enum=LOCATIONS),
                "patient_id": _str("The patient being booked, from find_patient."),
                "insurers": {
                    "type": "array",
                    "items": {"type": "string", "enum": INSURERS},
                    "description": "Price against these plans instead of the plan on file, e.g. a second plan the caller holds.",
                },
                "part_of_day": _str(
                    "Only morning (before 14:00) or afternoon (14:00 on) slots.",
                    enum=["morning", "afternoon"],
                ),
                "language": _str(
                    "Only doctors who speak Catalan, Basque or Galician. Use it ONLY when the "
                    "caller asks for a doctor who speaks one of those specifically, and then on "
                    "every search. Never for English or Spanish (every doctor speaks Spanish), "
                    "and never just because the caller speaks it. It is about the DOCTOR, not "
                    "this call.",
                    enum=LANGUAGES,
                ),
            },
            "required": ["date_from", "date_to"],
        },
    },
    {
        "name": "record_booking",
        "description": (
            "Record the booking to report when the call ends, after the caller has agreed to the "
            "exact slot. It replaces any earlier booking recorded for the same patient."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "patient_id": _str("From find_patient: the patient the appointment is for."),
                "provider_id": _str("From the slot."),
                "location_id": _str("From the slot.", enum=LOCATIONS),
                "appointment_type_id": _str("From the slot."),
                "slot": _SLOT,
                "policy_id": _POLICY,
            },
            "required": [
                "patient_id",
                "provider_id",
                "location_id",
                "appointment_type_id",
                "slot",
                "policy_id",
            ],
        },
    },
    {
        "name": "record_reschedule",
        "description": "Record moving an existing upcoming appointment to a new offered slot.",
        "parameters": {
            "type": "object",
            "properties": {
                "appointment_id": _str("From list_appointments (upcoming)."),
                "provider_id": _str("From the new slot."),
                "location_id": _str("From the new slot.", enum=LOCATIONS),
                "slot": _SLOT,
                "policy_id": _POLICY,
            },
            "required": ["appointment_id", "provider_id", "location_id", "slot", "policy_id"],
        },
    },
    {
        "name": "record_cancellation",
        "description": "Record cancelling one upcoming appointment. Two cancellations are two calls to this tool.",
        "parameters": {
            "type": "object",
            "properties": {"appointment_id": _str("From list_appointments (upcoming).")},
            "required": ["appointment_id"],
        },
    },
    {
        "name": "record_registration",
        "description": (
            "Record putting a caller who is NOT on file into the records. Nothing is booked for "
            "them. Call it as soon as every field is present; it validates and stages silently "
            "before the read-back. A later call with a corrected field replaces the staged "
            "registration. Every field must be exactly right."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "given_name": _str("First name."),
                "first_surname": _str("First surname."),
                "second_surname": _str("Second surname."),
                "national_id": _str("DNI or NIE including the check letter."),
                "date_of_birth": _str("YYYY-MM-DD."),
                "phone": _str("As dictated."),
                "email": _str("As dictated, e.g. ana.garcia@gmail.com."),
                "insurer": _str("Their plan.", enum=INSURERS),
            },
            "required": REGISTER_FIELDS,
        },
    },
    {
        "name": "record_no_action",
        "description": (
            "Record that the call ends without any booking, with the one reason that applies. "
            "Use the restriction id from search_availability's `blocked` when a rule stopped it. "
            "Replaces anything recorded before."
        ),
        "parameters": {
            "type": "object",
            "properties": {"reason": _str("Why nothing was booked.", enum=REASONS)},
            "required": ["reason"],
        },
    },
    {
        "name": "record_escalation",
        "description": (
            "Record handing the caller to a human, e.g. medical_emergency for a red-flag "
            "symptom. Replaces anything recorded before."
        ),
        "parameters": {
            "type": "object",
            "properties": {"reason": _str("Why.", enum=REASONS)},
            "required": ["reason"],
        },
    },
    {
        "name": "clear_recorded_actions",
        "description": (
            "Forget a withdrawn staged booking by patient_id, or a staged move/cancellation by "
            "appointment_id. Omit both only when the caller withdraws EVERYTHING. This does not "
            "cancel an existing clinic appointment; use record_cancellation for that."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "patient_id": _str("Remove only this patient's staged BOOK."),
                "appointment_id": _str("Remove only this appointment's staged RESCHEDULE/CANCEL."),
            },
            "required": [],
        },
    },
]


CUSTOMER_TOOLS = [
    {
        "name": "prepare_customer_account",
        "description": "Human demos only: capture the caller's name and dictated email for a local customer account. Read the returned values back and wait for explicit consent before confirm_customer_account. Corrections reset consent. An empty email withdraws the request. This is not clinic patient registration.",
        "parameters": {
            "type": "object",
            "properties": {
                "name": _str("Caller-provided name."),
                "email": _str("Spelled email using @ and dots, or empty to withdraw."),
            },
            "required": ["name", "email"],
        },
    },
    {
        "name": "confirm_customer_account",
        "description": "Only after reading back the name and entire email from prepare_customer_account and hearing explicit consent in a later turn, confirm creation of the local demo customer account and its welcome email after hang-up.",
        "parameters": {
            "type": "object",
            "properties": {"email": _str("Exact email the caller just confirmed.")},
            "required": ["email"],
        },
    },
]


def tools_for_session(session: CallSession) -> list[dict]:
    if session.demo_mode and appointment_email.enabled():
        return [*TOOLS, *EMAIL_TOOLS, *CUSTOMER_TOOLS]
    return TOOLS


# ── helpers ─────────────────────────────────────────────────────────


def _age(dob: str, today: date) -> int:
    b = date.fromisoformat(dob)
    return today.year - b.year - ((today.month, today.day) < (b.month, b.day))


def _spoken(dt: datetime) -> str:
    return f"{dt:%A} {dt.day} {dt:%B} at {dt:%H:%M}"


def patient_view(p: dict, today: date) -> dict:
    """What the model sees about a patient. Ids and phone are masked so they are never read out."""
    view = {
        "patient_id": p["patient_id"],
        "name": f"{p['given_name']} {p['first_surname']} {p['second_surname']}",
        "date_of_birth": p["date_of_birth"],
        # A local name-only registration has no date of birth, DNI/NIE or phone yet.
        "age": _age(p["date_of_birth"], today) if p["date_of_birth"] else None,
        "has_visited_before": p["has_visited_before"],
        "plan_on_file": p["insurer"],
        "referrals": p["referrals"],
        "note": p["note"],
        "national_id_ends": (p["national_id"] or "")[-3:],
        "phone_ends": (p["phone"] or "")[-3:],
        "matched_on": p.get("matched_fields", []),
    }
    if p.get("registration_pending"):
        view["registration_pending"] = True
    return view


def _speakers(cat: dict | None, language: str) -> set[str] | None:
    """Providers who speak `language` (the catalogue's per-provider list). None means "don't
    filter": the catalogue is not loaded, or nobody at the clinic speaks it (Basque, Galician),
    where an empty list would only hide the doctors the caller can still see."""
    if not cat:
        return None
    speakers = {p["id"] for p in cat["providers"] if language in p.get("languages", [])}
    return speakers or None


def _names(cat: dict | None) -> dict[str, str]:
    if not cat:
        return {}
    return {p["id"]: p["name"] for p in cat["providers"]} | {
        loc["id"]: loc["name"] for loc in cat["locations"]
    }


def _name_tokens(text: str) -> list[str]:
    plain = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().lower()
    return [token for token in re.findall(r"[a-z]+", plain) if token not in _NAME_TITLES]


def _name_match(heard: str, entries: list[dict[str, str]]) -> dict[str, Any]:
    """Rank catalogue names by the best heard/candidate token similarity."""
    heard_tokens = _name_tokens(heard)
    heard_folded = " ".join(heard_tokens)
    # A word every candidate carries ("Arenal") says nothing about which one was meant: score on
    # the rest ("Arenal Nort" -> Norte), unless it is all the caller said ("Arenal" -> ask which).
    token_sets = [set(_name_tokens(entry["name"])) for entry in entries]
    shared = set.intersection(*token_sets) if len(token_sets) > 1 else set()
    heard_tokens = [token for token in heard_tokens if token not in shared] or heard_tokens
    ranked = []
    for order, entry in enumerate(entries):
        candidate_tokens = _name_tokens(entry["name"])
        folded = " ".join(candidate_tokens)
        score = max(
            (
                SequenceMatcher(None, heard_token, candidate_token, autojunk=False).ratio()
                for heard_token in heard_tokens
                for candidate_token in candidate_tokens
            ),
            default=0.0,
        )
        ranked.append(
            {
                "id": entry["id"],
                "name": entry["name"],
                "score": score,
                "order": order,
                "exact": bool(heard_folded and heard_folded == folded),
                "detail": entry.get("detail", ""),
            }
        )
    ranked.sort(key=lambda match: (not match["exact"], -match["score"], match["order"]))
    top = ranked[0]["score"] if ranked else 0.0
    runner_up = ranked[1]["score"] if len(ranked) > 1 else 0.0
    confident = bool(ranked and ranked[0]["exact"]) or (top >= 0.65 and top - runner_up >= 0.30)
    visible = ranked[:3]
    if len(visible) > 2 and visible[2]["score"] < top - 0.05:
        visible = visible[:2]
    matches = [
        {"id": match["id"], "name": match["name"], "score": round(match["score"], 3)}
        | ({"specialty": match["detail"]} if match["detail"] else {})
        for match in visible
    ]
    result: dict[str, Any] = {
        "matches": matches,
        "confident": confident,
        "confidence": "high" if confident else "ambiguous",
    }
    if confident:
        result["selected_id"] = ranked[0]["id"]
        result["selected_name"] = ranked[0]["name"]
    else:
        # Say what tells the candidates apart ("Dr. Martín Sáez, general practice, or ...").
        choices = [
            f"{match['name']}, {match['detail'].lower()}," if match["detail"] else match["name"]
            for match in visible
        ]
        choices[-1] = choices[-1].rstrip(",")
        if len(choices) == 1:
            question = f"Did you mean {choices[0]}?"
        elif len(choices) == 2:
            question = f"Did you mean {choices[0]} or {choices[1]}?"
        else:
            question = f"Did you mean {', '.join(choices[:-1])} or {choices[-1]}?"
        result["question"] = question
        result["instruction"] = (
            "If the caller already said which specialty they want and exactly one of these has "
            "it, use that one without asking. Otherwise ask this question before searching; "
            "do not guess."
        )
    return result


def _check_slot(session: CallSession, provider_id: str, location_id: str, slot: str) -> dict | str:
    """The offered slot matching these fields, or an error message for the model."""
    try:
        when = datetime.fromisoformat(slot)
    except ValueError:
        return f"'{slot}' is not an ISO datetime; pass the slot exactly as search_availability returned it."
    if when.tzinfo is None:
        return "The slot needs its timezone offset, exactly as search_availability returned it."
    offered = session.slots.get((provider_id, location_id, when))
    if offered is None:
        return (
            "That slot was not offered by search_availability in this call for that provider and "
            "site. Search again and use a slot from the results; never invent one."
        )
    if when.astimezone(session.started_at.tzinfo).date() <= session.started_at.date():
        return "Nothing is booked for the same day as the call. Offer a slot from tomorrow on."
    return offered


def _check_policy(offered: dict, policy_id: str) -> str | None:
    if offered.get("payable_with") and policy_id not in offered["payable_with"]:
        return (
            f"That slot is not payable with {policy_id}; it is payable with "
            f"{', '.join(offered['payable_with'])}. If the caller holds another plan, search "
            "availability again with insurers=[that plan] and bill that plan."
        )
    return None


def _normalize_phone(raw: str) -> str:
    """Strip everything but digits, then a leading +34/0034 country code."""
    digits = re.sub(r"\D", "", raw)
    if digits.startswith("0034"):
        digits = digits[4:]
    elif digits.startswith("34") and len(digits) > 9:
        digits = digits[2:]
    return digits


def _one_digit_off(a: str, b: str) -> bool:
    """Whether a and b differ by exactly one substituted, missing or extra digit."""
    if a == b:
        return False
    if len(a) == len(b):
        return sum(x != y for x, y in zip(a, b, strict=True)) == 1
    if abs(len(a) - len(b)) != 1:
        return False
    short, long_ = (a, b) if len(a) < len(b) else (b, a)
    i = j = skips = 0
    while i < len(short) and j < len(long_):
        if short[i] == long_[j]:
            i += 1
            j += 1
        else:
            skips += 1
            if skips > 1:
                return False
            j += 1
    return True


def _check_phone(session: CallSession, raw: str) -> dict | str:
    """The dictated phone as 9 digits, or an {"error": ...} for the model to act on.

    Flags a mismatch against the caller-ID number at most once per call: `phone_mismatch_flagged`
    stops a loop if the caller repeats the same (or another) number after being asked about it.
    """
    digits = _normalize_phone(raw)
    if len(digits) != 9:
        return {
            "error": (
                f"That phone number has {len(digits)} digits; Spanish numbers have 9. Ask the "
                "caller to say the whole number again, slowly."
            )
        }
    caller_id = _normalize_phone(session.from_number or "")
    if (
        not session.phone_mismatch_flagged
        and len(caller_id) == 9
        and _one_digit_off(digits, caller_id)
    ):
        session.phone_mismatch_flagged = True
        national = " ".join(caller_id[i : i + 3] for i in range(0, 9, 3))
        return {
            "error": (
                f"That differs by one digit from the number they are calling from ({national}). "
                "Ask: 'Is your phone number the one you are calling from?' and use it if they "
                "say yes."
            )
        }
    return digits


def _staged(session: CallSession, action: dict) -> dict:
    staged = session.stage(action)
    session.log("action_staged", action=action, all_staged=staged)
    result: dict[str, Any] = {
        "recorded": action,
        "everything_recorded": staged,
        "note": "Recorded. It is reported when the call ends; confirm it to the caller.",
    }
    patient_id = appointment_email.patient_for_action(session, action)
    if (
        session.demo_mode
        and appointment_email.enabled()
        and patient_id is not None
        and patient_id in session.patients
    ):
        recipient = session.appointment_emails.get(patient_id)
        if recipient is not None and not recipient.address:
            status = "declined"
        elif appointment_email.address_on_file(session, patient_id):
            status = "on_file"
        elif recipient and recipient.confirmed:
            status = "confirmed"
        else:
            status = "needs_address"
        result["appointment_email"] = {"patient_id": patient_id, "status": status}
    return result


# ── handlers ────────────────────────────────────────────────────────


async def _resolve_names(session: CallSession, args: dict) -> dict:
    cat = clinic.cached()
    if not cat:
        return {"error": "The clinic catalogue is unavailable; do not guess a doctor or site."}
    if not args.get("doctor") and not args.get("site"):
        return {"error": "Give the heard doctor name, site name, or both."}
    result: dict[str, Any] = {}
    if args.get("doctor"):
        result["doctor"] = _name_match(
            str(args["doctor"]),
            [
                {"id": p["id"], "name": p["name"], "detail": p.get("specialty_name", "")}
                for p in cat["providers"]
            ],
        )
        if result["doctor"].get("confident"):
            result["doctor"]["provider_id"] = result["doctor"]["selected_id"]
    if args.get("site"):
        result["site"] = _name_match(
            str(args["site"]), [{"id": loc["id"], "name": loc["name"]} for loc in cat["locations"]]
        )
        if result["site"].get("confident"):
            result["site"]["location_id"] = result["site"]["selected_id"]
    return result


async def _find_patient(session: CallSession, args: dict) -> dict:
    query: dict[str, str] = {
        k: str(args[k]) for k in ("name", "national_id", "phone", "date_of_birth") if args.get(k)
    }
    if not query:
        return {"error": "Give at least one of name, national_id, phone, date_of_birth."}
    if "national_id" in query:
        query["national_id"] = clinic.normalize_national_id(query["national_id"])
    if _id_decides(query):
        matches = await _by_national_id(session, query)
    else:
        matches = await session.clinic_client.directory(**query)
        session.log("lookup", path="directory")
    session.remember_patients(matches)
    today = session.started_at.date()
    shown = [patient_view(m, today) for m in matches[:5]]
    result: dict[str, Any] = {"matches": shown, "count": len(matches)}
    if "name" in query and matches and not any(_same_person(query["name"], m) for m in matches):
        on_file = shown[0]["name"]
        result["note"] = (
            f"The ID belongs to {on_file}, not the name the caller gave: confirm who the patient "
            "is before using this record."
        )
        return result
    if not matches:
        result["note"] = (
            "Nobody matches. An exact field (id, phone, date of birth) that is wrong excludes the "
            "right person: re-confirm it with the caller. If they are genuinely new, they must be "
            "registered, not booked."
        )
    elif len(matches) > 1:
        result["note"] = "Several people match: ask for a second identifier to tell them apart."
    return result


def _id_decides(query: dict[str, str]) -> bool:
    """A DNI/NIE belongs to one person, so it alone finds them. The fuzzy name search is what
    makes /directory slow (~450 ms with a name, ~140 ms without, warm connection)."""
    if "national_id" not in query or "phone" in query:
        return False  # phone matching is Prosper's own digit rule: leave it to /directory
    dob = query.get("date_of_birth")
    if dob:
        try:
            date.fromisoformat(dob)
        except ValueError:
            return False  # let /directory reject a malformed date the way it always has
    return True


async def _by_national_id(session: CallSession, query: dict[str, str]) -> list[dict]:
    """Patients with this DNI/NIE: one this call already holds (caller ID, an earlier lookup),
    else /directory asked for the ID alone. A given date of birth still excludes, exactly as
    /directory applies it; the spoken name never filters (see _same_person)."""
    nid = query["national_id"]
    held = [
        p
        for p in session.patients.values()
        if clinic.normalize_national_id(p["national_id"] or "") == nid
    ]
    matches = held or await session.clinic_client.directory(national_id=nid)
    session.log("lookup", path="held" if held else "national_id_only")
    fields = ["national_id"]
    if query.get("date_of_birth"):
        matches = [m for m in matches if m["date_of_birth"] == query["date_of_birth"]]
        fields.append("date_of_birth")
    return [{**m, "matched_fields": fields} for m in matches]


def _words(text: str) -> set[str]:
    plain = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().lower()
    return set(re.findall(r"[a-z]{2,}", plain))


def _same_person(spoken: str, patient: dict) -> bool:
    """Whether a spoken name could be this patient's: any name word in common, accents ignored.
    Loose on purpose: speech recognition mangles names; this only flags a clear mismatch."""
    on_file = f"{patient['given_name']} {patient['first_surname']} {patient['second_surname']}"
    return bool(_words(spoken) & _words(on_file))


async def _list_appointments(session: CallSession, args: dict) -> dict:
    patient_id = args["patient_id"]
    if patient_id not in session.patients:
        return {"error": "Unknown patient_id: look the patient up with find_patient first."}
    when = args.get("when") or "upcoming"
    appointments = await session.clinic_client.appointments(patient_id, when)
    upcoming = [
        a for a in appointments if datetime.fromisoformat(a["start_time"]) > session.started_at
    ]
    session.remember_appointments(upcoming)
    names = _names(clinic.cached())
    return {
        "appointments": [
            {
                **a,
                "provider_name": names.get(a["provider_id"], a["provider_id"]),
                "site": names.get(a["location_id"], a["location_id"]),
                "spoken": _spoken(datetime.fromisoformat(a["start_time"])),
                "can_change": a in upcoming,
            }
            for a in appointments
        ]
    }


async def _get_site_directions(session: CallSession, args: dict) -> dict:
    cat = clinic.cached()
    if not cat:
        return {"error": "The clinic catalogue is unavailable."}
    location = next((site for site in cat["locations"] if site["id"] == args["location_id"]), None)
    if location is None:
        return {"error": "Unknown location_id: choose a site from the clinic catalogue."}
    return await directions.get_site_directions(args["latitude"], args["longitude"], location)


async def _rank_sites_by_distance(session: CallSession, args: dict) -> dict:
    cat = clinic.cached()
    if not cat:
        return {"error": "The clinic catalogue is unavailable."}
    lat, lon = args["latitude"], args["longitude"]
    if (
        isinstance(lat, bool)
        or isinstance(lon, bool)
        or not isinstance(lat, (int, float))
        or not isinstance(lon, (int, float))
        or not isfinite(lat)
        or not isfinite(lon)
        or not -90 <= lat <= 90
        or not -180 <= lon <= 180
    ):
        return {"error": "Give finite latitude (-90 to 90) and longitude (-180 to 180)."}
    if args["specialty_id"] not in SPECIALTIES:
        return {"error": "Unknown specialty_id."}
    eligible = {
        schedule["location_id"]
        for provider in cat["providers"]
        if provider["specialty_id"] == args["specialty_id"]
        for schedule in provider["schedules"]
    }
    sites = []
    for loc in cat["locations"]:
        if loc["id"] not in eligible:
            continue
        if "latitude" not in loc or "longitude" not in loc:
            return {"error": "Site coordinates are missing from the catalogue."}
        dlat, dlon = radians(loc["latitude"] - lat), radians(loc["longitude"] - lon)
        hav = (
            sin(dlat / 2) ** 2
            + cos(radians(lat)) * cos(radians(loc["latitude"])) * sin(dlon / 2) ** 2
        )
        sites.append(
            {
                "location_id": loc["id"],
                "name": loc["name"],
                "distance_km": 6371 * 2 * asin(sqrt(min(1.0, max(0.0, hav)))),
            }
        )
    sites.sort(key=lambda site: site["distance_km"])
    return {
        "sites": sites,
        "note": "Check real availability and coverage in this order; distance is not travel time.",
    }


async def _search_availability(session: CallSession, args: dict) -> dict:
    if not args.get("specialty_id") and not args.get("provider_id"):
        return {"error": "Give specialty_id or provider_id."}
    notes = []
    tomorrow = session.started_at.date() + timedelta(days=1)
    after = None
    if args.get("after"):
        try:
            after = datetime.fromisoformat(str(args["after"]))
        except ValueError:
            return {"error": "after must be an ISO datetime."}
        if after.tzinfo is None:
            return {"error": "after needs its timezone offset."}
    try:
        date_from = max(date.fromisoformat(args["date_from"]), tomorrow)
        date_to = date.fromisoformat(args["date_to"])
    except ValueError:
        return {"error": "Dates must be YYYY-MM-DD."}
    if date.fromisoformat(args["date_from"]) < tomorrow:
        notes.append(f"Nothing is booked today, so the search starts {date_from.isoformat()}.")
    if date_to < date_from:
        date_to = date_from
    if (date_to - date_from).days > 13:
        date_to = date_from + timedelta(days=13)
        notes.append(f"Windows are capped at 14 days, so this one ends {date_to.isoformat()}.")
    try:
        data = await session.clinic_client.availability(
            date_from.isoformat(),
            date_to.isoformat(),
            specialty_id=args.get("specialty_id"),
            provider_id=args.get("provider_id"),
            location_id=args.get("location_id"),
            patient_id=args.get("patient_id"),
            insurers=args.get("insurers"),
        )
    except prosper.ProsperError as e:
        return {"error": f"The clinic system refused the search ({e.status}): {e.detail}"}
    slots = sorted(data["slots"], key=lambda s: datetime.fromisoformat(s["start_time"]))
    if after is not None:
        slots = [s for s in slots if datetime.fromisoformat(s["start_time"]) > after]
    session.remember_slots(slots)
    part = args.get("part_of_day")
    if part:
        slots = [
            s
            for s in slots
            if (datetime.fromisoformat(s["start_time"]).hour < 14) == (part == "morning")
        ]
    # Case-normalise, then ignore anything the filter doesn't apply to (English, Spanish, empty,
    # junk a model invents) rather than erroring: an over-eager model must not empty a search by
    # passing a language nobody asked to filter on.
    language = str(args.get("language") or "").strip().lower()
    if language not in LANGUAGES:
        # English is deliberately not filterable: 21 published English-language cases accept a
        # doctor who speaks no English (PR07, PR08, PR09, PR10), so filtering on "en" would hide
        # the expected answer across ten problems. A caller who genuinely asks for an
        # English-speaking doctor is answered from THE CLINIC catalogue instead, which lists every
        # provider's languages -- say so rather than dropping the request in silence.
        if language == "en":
            who = _speakers(clinic.cached(), "en")
            names = ", ".join(sorted(who)) if who else "see THE CLINIC"
            notes.append(
                "Not filtered by English: an English-speaking caller can see any doctor. If they "
                f"actually asked for a doctor who speaks English, choose one of {names} from the "
                "catalogue rather than filtering, and say so if none is free."
            )
        language = ""
    spoken = LANGUAGE_NAMES.get(language, language)
    speakers = _speakers(clinic.cached(), language) if language else None
    before_language = slots  # the real (unfiltered) picture, for the "diary is full" note below
    if speakers is not None:
        slots = [s for s in slots if s["provider_id"] in speakers]
        if slots:
            notes.append(f"Only doctors who speak {spoken} are listed.")
        elif before_language:
            notes.append(
                f"{len(before_language)} slot(s) exist in this window, but none with a doctor "
                f"who speaks {spoken}: try a later window, or ask whether another doctor is "
                "acceptable."
            )
    elif language and clinic.cached():
        notes.append(f"No doctor at the clinic speaks {spoken}; all doctors are listed.")
    session.record_search(len(slots), [b["restriction"] for b in data["blocked"]])
    names = _names(clinic.cached())
    result: dict[str, Any] = {
        "window": [date_from.isoformat(), date_to.isoformat()],
        "appointment_type": {
            "id": data["appointment_type"]["id"],
            "name": data["appointment_type"]["name"],
            "guidance": data["appointment_type"]["guidance"],
        },
        "slots_found": len(slots),
        "earliest_slots": [
            {
                "slot": s["start_time"],
                "spoken": _spoken(datetime.fromisoformat(s["start_time"])),
                "provider_id": s["provider_id"],
                "provider_name": s["provider_name"],
                "location_id": s["location_id"],
                "site": names.get(s["location_id"], s["location_id"]),
                "appointment_type_id": s["appointment_type_id"],
                "payable_with": s["payable_with"],
            }
            for s in slots[:MAX_SLOTS_SHOWN]
        ],
        "blocked": [
            {**b, "provider_name": names.get(b["provider_id"], b["provider_id"])}
            for b in data["blocked"]
        ],
    }
    # Decided on the unfiltered list: if the language filter is what emptied `slots`, the note
    # above already explains that, and the diary is not actually full or blocked.
    if not before_language and not data["blocked"]:
        notes.append(
            "No free slot in this window and no rule blocked anyone: the diary is simply full. "
            "Try a later window, or report no_availability if the caller accepts nothing else."
        )
    elif not before_language:
        notes.append(
            "No slot: `blocked` names the rule that stopped each provider. Explain it to the caller; "
            "for an insurance restriction, ask about another plan before a final refusal. "
            "If they hold one, repeat the search with insurers=[that plan]. "
            "Offer another provider or site if the rule allows, otherwise record_no_action with "
            "that restriction id."
        )
    # A provider on leave can still return slots after the leave ends, with `blocked` empty.
    # Doctor & Site wants the same specialty at the same site, so say so on the result.
    pid = args.get("provider_id")
    prov = next((p for p in (clinic.cached() or {}).get("providers", []) if p["id"] == pid), None)
    leave = prov and prov.get("leave")
    if leave and date.fromisoformat(leave["end"]) >= date_from:
        sites = ", ".join(sorted({s["location_id"] for s in prov["schedules"]}))
        result["provider_on_leave"] = {**leave, "provider_id": pid, "provider_name": prov["name"]}
        notes.append(
            f"{prov['name']} is on leave until {leave['end']} ({leave['reason']}). Tell the caller, "
            f"then search specialty_id={prov['specialty_id']} at the site they asked for (his: {sites}) "
            "without provider_id, and offer the earliest slot with another doctor there. Book him "
            "after his leave only if the caller refuses everyone else; if they will see nobody, "
            "record_no_action(provider_on_leave)."
        )
    if notes:
        result["notes"] = notes
    return result


async def _record_booking(session: CallSession, args: dict) -> dict:
    if args["patient_id"] not in session.patients:
        return {"error": "Unknown patient_id: find the patient with find_patient first."}
    offered = _check_slot(session, args["provider_id"], args["location_id"], args["slot"])
    if isinstance(offered, str):
        return {"error": offered}
    problem = _check_policy(offered, args["policy_id"])
    if problem:
        return {"error": problem}
    action = {
        "action": "BOOK",
        "patient_id": args["patient_id"],
        "provider_id": offered["provider_id"],
        "location_id": offered["location_id"],
        # The type follows the record and the specialty; the clinic named it on the slot.
        "appointment_type_id": offered["appointment_type_id"],
        "slot": offered["start_time"],
        "policy_id": args["policy_id"],
    }
    return _staged(session, action)


async def _record_reschedule(session: CallSession, args: dict) -> dict:
    if args["appointment_id"] not in session.appointments:
        return {"error": "Unknown appointment_id: get it from list_appointments (upcoming) first."}
    offered = _check_slot(session, args["provider_id"], args["location_id"], args["slot"])
    if isinstance(offered, str):
        return {"error": offered}
    problem = _check_policy(offered, args["policy_id"])
    if problem:
        return {"error": problem}
    action = {
        "action": "RESCHEDULE",
        "appointment_id": args["appointment_id"],
        "provider_id": offered["provider_id"],
        "location_id": offered["location_id"],
        "slot": offered["start_time"],
        "policy_id": args["policy_id"],
    }
    return _staged(session, action)


async def _record_cancellation(session: CallSession, args: dict) -> dict:
    if args["appointment_id"] not in session.appointments:
        return {"error": "Unknown appointment_id: get it from list_appointments (upcoming) first."}
    return _staged(session, {"action": "CANCEL", "appointment_id": args["appointment_id"]})


async def _record_registration(session: CallSession, args: dict) -> dict:
    missing = [k for k in REGISTER_FIELDS if not str(args.get(k) or "").strip()]
    if missing:
        return {"error": f"Still missing: {', '.join(missing)}. Ask the caller."}
    national_id = clinic.normalize_national_id(args["national_id"])
    if not clinic.national_id_valid(national_id):
        return {
            "error": (
                f"{national_id} is not a valid DNI/NIE: the check letter does not match the "
                "digits, so a digit or the letter was misheard. Ask the caller to repeat it slowly."
            )
        }
    try:
        date.fromisoformat(args["date_of_birth"])
    except ValueError:
        return {"error": "date_of_birth must be YYYY-MM-DD."}
    checked_phone = _check_phone(session, args["phone"])
    if isinstance(checked_phone, dict):
        return checked_phone
    if "@" not in args["email"]:
        return {"error": "That email has no @; ask the caller to spell it again."}
    if args["insurer"] not in INSURERS:
        return {"error": f"insurer must be one of {', '.join(INSURERS)}."}
    action = {
        "action": "REGISTER",
        "given_name": args["given_name"].strip(),
        "first_surname": args["first_surname"].strip(),
        "second_surname": args["second_surname"].strip(),
        "national_id": national_id,
        "date_of_birth": args["date_of_birth"],
        "phone": checked_phone,
        "email": args["email"].replace(" ", "").lower(),
        "insurer": args["insurer"],
    }
    return _staged(session, action)


async def _record_reason(session: CallSession, args: dict, verb: str) -> dict:
    if args.get("reason") not in REASONS:
        return {"error": f"reason must be one of: {', '.join(REASONS)}."}
    return _staged(session, {"action": verb, "reason": args["reason"]})


async def _record_no_action(session: CallSession, args: dict) -> dict:
    return await _record_reason(session, args, "NO_ACTION")


async def _record_escalation(session: CallSession, args: dict) -> dict:
    return await _record_reason(session, args, "ESCALATE")


async def _clear(session: CallSession, args: dict) -> dict:
    selectors = {k: args[k] for k in ("patient_id", "appointment_id") if k in args}
    if len(selectors) > 1 or any(
        not isinstance(v, str) or not v.strip() for v in selectors.values()
    ):
        return {
            "error": "Give one nonempty patient_id or appointment_id, or omit both to clear all."
        }
    if "patient_id" in selectors:
        session.actions = [
            a
            for a in session.actions
            if not (a["action"] == "BOOK" and a["patient_id"] == selectors["patient_id"])
        ]
    elif "appointment_id" in selectors:
        session.actions = [
            a
            for a in session.actions
            if not (
                a["action"] in ("RESCHEDULE", "CANCEL")
                and a["appointment_id"] == selectors["appointment_id"]
            )
        ]
    else:
        session.clear_actions()
    remaining = {
        appointment_email.patient_for_action(session, action) for action in session.actions
    }
    session.appointment_emails = {
        patient_id: recipient
        for patient_id, recipient in session.appointment_emails.items()
        if patient_id in remaining
    }
    session.log("actions_cleared", **selectors)
    return {"everything_recorded": session.actions}


_HANDLERS = {
    "prepare_customer_account": customer_accounts.prepare,
    "confirm_customer_account": customer_accounts.confirm,
    "get_site_directions": _get_site_directions,
    "set_appointment_email": appointment_email.set_recipient,
    "confirm_appointment_email": appointment_email.confirm_recipient,
    "rank_sites_by_distance": _rank_sites_by_distance,
    "resolve_names": _resolve_names,
    "find_patient": _find_patient,
    "list_appointments": _list_appointments,
    "search_availability": _search_availability,
    "record_booking": _record_booking,
    "record_reschedule": _record_reschedule,
    "record_cancellation": _record_cancellation,
    "record_registration": _record_registration,
    "record_no_action": _record_no_action,
    "record_escalation": _record_escalation,
    "clear_recorded_actions": _clear,
}


async def call_tool(session: CallSession, name: str, args: dict | None) -> dict:
    """Run one tool for this call. Never raises: the model gets {"error": ...} and can recover."""
    args = dict(args or {})
    session.log("tool_started", name=name, args=args)
    handler = _HANDLERS.get(name)
    if handler is None:
        result: dict = {"error": f"Unknown tool {name}."}
    else:
        try:
            result = await session.execute_tool(name, args, handler)
        except KeyError as e:
            result = {"error": f"Missing argument {e}."}
        except prosper.ProsperError as e:
            result = {"error": f"The clinic system answered {e.status}: {e.detail}"}
        except Exception as e:  # network trouble etc.: tell the model, keep the call alive
            session.log("tool_error", name=name, error_type=type(e).__name__, error=str(e))
            result = {
                "error": f"The clinic system is not answering ({type(e).__name__}). Try again."
            }
    session.log("tool", name=name, args=args, result=result)
    return result


def register_pipecat_tools(llm: Any, session: CallSession) -> Any:
    """Register every tool on a pipecat LLMService; returns the ToolsSchema for LLMContext(tools=...)."""
    from pipecat.adapters.schemas.function_schema import FunctionSchema
    from pipecat.adapters.schemas.tools_schema import ToolsSchema

    async def handler(params: Any) -> None:
        await params.result_callback(
            await call_tool(session, params.function_name, dict(params.arguments))
        )

    schemas = []
    for spec in session.tool_specs(tools_for_session(session)):
        llm.register_function(spec["name"], handler)
        schemas.append(
            FunctionSchema(
                name=spec["name"],
                description=spec["description"],
                properties=spec["parameters"]["properties"],
                required=spec["parameters"]["required"],
            )
        )
    return ToolsSchema(standard_tools=schemas)
