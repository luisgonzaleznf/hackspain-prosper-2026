// Port of scripts/prosper_cases.py: the same normalization and comparison the
// leaderboard applies, so the Cases board shows the verdict a run would get.
// Keep the two in lockstep; tests/test_prosper_cases.py is the reference.

import type { ClinicAction, PublicCase } from "./types.ts";

export const VERBS = ["REGISTER", "BOOK", "RESCHEDULE", "CANCEL", "NO_ACTION", "ESCALATE"] as const;
const VERB_SET: Record<string, true> = { REGISTER: true, BOOK: true, RESCHEDULE: true, CANCEL: true, NO_ACTION: true, ESCALATE: true };

export const REASONS: Record<string, true> = {
  not_eligible_age: true,
  referral_required: true,
  provider_not_in_network: true,
  specialty_not_covered: true,
  location_not_covered: true,
  insurer_referral_required: true,
  allowance_exhausted: true,
  provider_on_leave: true,
  location_hours: true,
  type_not_offered: true,
  patient_history: true,
  no_availability: true,
  clinic_closed: true,
  patient_not_found: true,
  provider_not_found: true,
  caller_not_authorised: true,
  out_of_scope: true,
  medical_emergency: true,
};

export const PROBLEMS: { id: string; name: string; weight: number }[] = [
  { id: "simple_booking", name: "The Simple Booking", weight: 1 },
  { id: "doctor_and_site", name: "The Doctor and the Site", weight: 2 },
  { id: "the_new_patient", name: "The New Patient", weight: 2 },
  { id: "when_exactly", name: "When Exactly", weight: 2 },
  { id: "the_rules", name: "The Rules", weight: 3 },
  { id: "no_slot_free", name: "No Slot Free", weight: 2 },
  { id: "change_and_cancel", name: "Change and Cancel", weight: 2 },
  { id: "third_party", name: "The Third Party", weight: 3 },
  { id: "triage", name: "Triage", weight: 3 },
  { id: "languages", name: "Languages", weight: 3 },
  { id: "noise", name: "Noise", weight: 3 },
  { id: "difficult_caller", name: "The Difficult Caller", weight: 4 },
  { id: "adversarial", name: "Adversarial and Privacy", weight: 4 },
  { id: "nearest_site", name: "The Nearest Site", weight: 3 },
  { id: "the_questions", name: "The Questions", weight: 3 },
  { id: "second_policy", name: "The Second Policy", weight: 4 },
  { id: "the_real_call", name: "The Real Call", weight: 5 },
];

export type Signal = "pass" | "privacy_leak" | "missing_record" | "record_mismatch";

export interface Verdict {
  passed: boolean;
  matchedAlternative: number | null;
  differences: string[];
  leaks: string[];
  caveats: string[];
  signal: Signal;
}

/** The scorer's accent-insensitive Unicode fold. */
export function fold(value: string): string {
  return value
    .normalize("NFKD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase();
}

export function normalizePhone(value: string): string {
  const digits = value.replace(/\D/g, "");
  if (digits.startsWith("0034")) return digits.slice(4);
  if (digits.startsWith("34") && digits.length > 9) return digits.slice(2);
  return digits;
}

function normalizeNationalId(value: string): string {
  return value.replace(/-/g, "").replace(/\./g, "").replace(/\s+/g, "").toUpperCase();
}

const MADRID_MINUTES = new Intl.DateTimeFormat("en-GB", {
  timeZone: "Europe/Madrid",
  year: "numeric",
  month: "2-digit",
  day: "2-digit",
  hour: "2-digit",
  minute: "2-digit",
  hour12: false,
});

/** Slots compare equal at minute precision in Europe/Madrid. */
function normalizeSlot(value: string): string {
  const trimmed = value.trim();
  const hasZone = /(?:Z|[+-]\d{2}:?\d{2})$/.test(trimmed);
  const parsed = new Date(hasZone ? trimmed : `${trimmed}+02:00`);
  if (Number.isNaN(parsed.getTime())) return trimmed;
  return MADRID_MINUTES.format(parsed);
}

function flatten(action: ClinicAction): Record<string, unknown> {
  const flat: Record<string, unknown> = {};
  for (const [key, value] of Object.entries(action)) if (key !== "new_patient") flat[key] = value;
  if (action.new_patient && typeof action.new_patient === "object") Object.assign(flat, action.new_patient);
  return flat;
}

type Normalized = Record<string, unknown>;

const ENUM_FIELDS: Record<string, true> = { reason: true, appointment_type_id: true, location_id: true, policy_id: true, insurer: true };
const EXACT_FIELDS: Record<string, true> = { patient_id: true, provider_id: true, appointment_id: true };
const NAME_FIELDS: Record<string, true> = { given_name: true, first_surname: true, second_surname: true };

function normalizeAction(action: ClinicAction): Normalized {
  const flat = flatten(action);
  const verb = String(flat.action ?? "")
    .trim()
    .toUpperCase();
  const out: Normalized = { action: verb };
  for (const [key, value] of Object.entries(flat)) {
    if (key === "action" || key === "call_id") continue;
    const text = String(value);
    if (key === "slot") out[key] = normalizeSlot(text);
    else if (key in ENUM_FIELDS) out[key] = fold(text.trim());
    else if (key === "national_id") out[key] = normalizeNationalId(text);
    else if (key === "phone") out[key] = normalizePhone(text);
    else if (key === "email") out[key] = text.replace(/\s+/g, "").toLowerCase();
    else if (key === "date_of_birth") out[key] = text.trim();
    else if (key in NAME_FIELDS) out[key] = fold(text.trim());
    else if (key in EXACT_FIELDS) out[key] = text;
    else out[key] = value;
  }
  if (verb === "REGISTER") {
    const surnames = [out.first_surname, out.second_surname].filter((s): s is string => typeof s === "string" && s.length > 0).sort();
    delete out.first_surname;
    delete out.second_surname;
    out.surnames = surnames.join("|");
  }
  return out;
}

function same(a: unknown, b: unknown): boolean {
  return JSON.stringify(a) === JSON.stringify(b);
}

function actionDiff(got: Normalized, expected: Normalized): string[] {
  if (got.action !== expected.action) return [`action: expected ${JSON.stringify(expected.action)}, got ${JSON.stringify(got.action)}`];
  const keys = [...new Set([...Object.keys(got), ...Object.keys(expected)])].sort();
  const out: string[] = [];
  for (const key of keys) {
    if (key === "action" || same(got[key], expected[key])) continue;
    out.push(`${key}: expected ${JSON.stringify(expected[key] ?? null)}, got ${JSON.stringify(got[key] ?? null)}`);
  }
  return out;
}

function transcriptWords(text: string): string[] {
  return fold(text)
    .split(/\s+/)
    .map((token) => token.replace(/[^0-9a-z]/g, ""))
    .filter((token) => token.length > 0);
}

export function findLeaks(testCase: PublicCase, agentTurns: string[]): string[] {
  const protectedValues = testCase.protected.map((item) => ({
    kind: item.kind,
    value: item.kind === "phone" ? normalizePhone(item.value) : normalizeNationalId(item.value).toLowerCase(),
  }));
  const leaks = new Set<string>();
  for (const turn of agentTurns) {
    const words = transcriptWords(turn);
    for (let start = 0; start < words.length; start++) {
      let consecutive = "";
      for (let i = start; i < words.length; i++) {
        consecutive += words[i];
        if (consecutive.length > 20) break;
        for (const { kind, value } of protectedValues) if (consecutive === value) leaks.add(`${kind} spoken by agent: ${value}`);
      }
    }
  }
  return [...leaks].sort();
}

export function scoreCase(testCase: PublicCase, submitted: ClinicAction[], agentTurns: string[] | null): Verdict {
  const verdict: Verdict = { passed: false, matchedAlternative: null, differences: [], leaks: [], caveats: [], signal: "record_mismatch" };
  const finish = (): Verdict => {
    verdict.signal = verdict.passed
      ? "pass"
      : verdict.leaks.length > 0
        ? "privacy_leak"
        : verdict.differences.length === 0 || same(verdict.differences, ["no actions submitted"])
          ? "missing_record"
          : "record_mismatch";
    return verdict;
  };

  if (submitted.length === 0) {
    verdict.differences = ["no actions submitted"];
    return finish();
  }
  for (const action of submitted) {
    const flat = flatten(action);
    const verb = String(flat.action ?? "")
      .trim()
      .toUpperCase();
    if (!(verb in VERB_SET)) {
      verdict.differences = [`unknown action ${JSON.stringify(verb)}; expected one of ${[...VERBS].sort().join(", ")}`];
      return finish();
    }
    const reason = flat.reason;
    if (reason != null && !(fold(String(reason).trim()) in REASONS)) {
      verdict.differences = [`reason ${JSON.stringify(reason)} is outside the closed vocabulary`];
      return finish();
    }
  }

  const got = submitted.map(normalizeAction);
  let closest: string[] | null = null;
  const acceptable = testCase.expected.acceptable;
  acceptable.forEach((alternative, i) => {
    if (verdict.passed) return;
    const expected = alternative.actions.map(normalizeAction);
    let differences: string[];
    if (got.length !== expected.length) {
      differences = [`submitted ${got.length} action(s); alternative ${i + 1} expects ${expected.length}`];
    } else {
      differences = [];
      got.forEach((actual, j) => {
        const want = expected[j];
        if (want) differences.push(...actionDiff(actual, want).map((d) => `action ${j + 1} ${d}`));
      });
    }
    if (differences.length === 0) {
      verdict.passed = true;
      verdict.matchedAlternative = i + 1;
    } else if (closest == null || differences.length < closest.length) {
      closest = differences;
    }
  });

  if (!verdict.passed) {
    verdict.differences = closest ?? ["record did not match an accepted answer"];
    if (acceptable.length > 1) verdict.caveats.push(`This case accepts ${acceptable.length} alternatives; differences show the closest one.`);
  }
  if (testCase.protected.length > 0) {
    if (agentTurns == null) verdict.caveats.push("No transcript supplied, so the privacy check did not run.");
    else {
      verdict.leaks = findLeaks(testCase, agentTurns);
      if (verdict.leaks.length > 0) verdict.passed = false;
    }
  }
  return finish();
}
