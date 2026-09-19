// The 18 problems and their public cases, joined with the calls the backend
// has recorded for them. A call is attributed to a case by the run reference
// the backend writes (`summary.run.case_id`); calls without one are matched by
// caller number when exactly one case in the roster uses that persona phone.

import roster from "@/data/public-cases.json";
import { normalizePhone, PROBLEMS, scoreCase, type Verdict } from "./score.ts";
import type { Timeline } from "./timeline.ts";
import type { CallDetail, CallSummary, PublicCase } from "./types.ts";

export const CASES: PublicCase[] = (roster as { cases: PublicCase[] }).cases;

const CASE_BY_ID: Record<string, PublicCase> = {};
for (const c of CASES) CASE_BY_ID[c.id] = c;

const CASES_BY_PHONE: Record<string, PublicCase[]> = {};
for (const c of CASES) {
  const key = normalizePhone(c.persona.phone);
  (CASES_BY_PHONE[key] ??= []).push(c);
}

export function caseById(id: string | null | undefined): PublicCase | null {
  return id ? (CASE_BY_ID[id] ?? null) : null;
}

export function problemOf(id: string): { id: string; name: string; weight: number } {
  return PROBLEMS.find((p) => p.id === id) ?? { id, name: id, weight: 1 };
}

/** Case a call belongs to: the run reference first, else a unique persona phone. */
export function attribute(summary: CallSummary, timeline: Timeline | null): { testCase: PublicCase; via: "run" | "phone" } | null {
  const fromRun = caseById(summary.run?.case_id);
  if (fromRun) return { testCase: fromRun, via: "run" };
  if (!timeline?.fromNumber) return null;
  const candidates = CASES_BY_PHONE[normalizePhone(timeline.fromNumber)];
  const only = candidates?.length === 1 ? candidates[0] : undefined;
  return only ? { testCase: only, via: "phone" } : null;
}

export function verdictFor(testCase: PublicCase, detail: CallDetail): Verdict {
  const submitted = detail.submissions.map((s) => s.action);
  const agentTurns = detail.transcript.filter((t) => t.role === "agent").map((t) => t.text);
  return scoreCase(testCase, submitted, agentTurns);
}

export const LANGUAGE_LABEL: Record<string, string> = { es: "Español", ca: "Català", gl: "Galego", eu: "Euskara", en: "English" };
