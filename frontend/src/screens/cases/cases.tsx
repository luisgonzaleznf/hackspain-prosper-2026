// Cases: one row per problem, one glyph per public case, verdicts scored from
// the calls the backend has recorded (run reference or unique persona phone).
// The eval story for the jury.

import { clsx } from "clsx";
import { Check, Phone, X } from "lucide-react";
import { useEffect, useMemo, useRef } from "react";
import { Link, useNavigate, useParams } from "react-router";
import { ScreenHeader } from "@/app";
import { Empty, Label, Mono, Outcome, ReasonCode, VerdictMark } from "@/components/primitives";
import { attribute, CASES, caseById, LANGUAGE_LABEL, problemOf, verdictFor } from "@/lib/cases";
import { duration, wallClock } from "@/lib/format";
import { useRiseIn, useSlideIn } from "@/lib/motion";
import { PROBLEMS, type Verdict } from "@/lib/score";
import { isActive, loadDetail, useCallsIndex, type CallRecord } from "@/lib/store";
import type { PublicCase } from "@/lib/types";
import { ActionTable } from "@/screens/calls/detail";

interface CaseResult {
  testCase: PublicCase;
  latest: { record: CallRecord; verdict: Verdict } | null;
  attempts: number;
}

export function CasesScreen() {
  const { caseId } = useParams();
  const navigate = useNavigate();
  const { calls, byId, loading } = useCallsIndex();
  const grid = useRef<HTMLDivElement>(null);

  // Verdicts need details; load every finished call once (cached in the store).
  useEffect(() => {
    for (const c of calls) if (!isActive(c)) void loadDetail(c.call_id);
  }, [calls]);

  const results = useMemo(() => {
    const byCase: Record<string, CaseResult> = {};
    for (const testCase of CASES) byCase[testCase.id] = { testCase, latest: null, attempts: 0 };
    for (const summary of calls) {
      if (isActive(summary)) continue;
      const record = byId[summary.call_id];
      if (!record?.detail || !record.timeline) continue;
      const attributed = attribute(summary, record.timeline);
      if (!attributed) continue;
      const slot = byCase[attributed.testCase.id];
      if (!slot) continue;
      slot.attempts += 1;
      if (!slot.latest || summary.started_at > slot.latest.record.summary.started_at) {
        slot.latest = { record, verdict: verdictFor(attributed.testCase, record.detail) };
      }
    }
    return byCase;
  }, [calls, byId]);

  const totals = useMemo(() => {
    let passed = 0;
    let run = 0;
    let weightedPass = 0;
    let weightedTotal = 0;
    for (const p of PROBLEMS) {
      const cases = CASES.filter((c) => c.problem_id === p.id);
      weightedTotal += p.weight * cases.length;
      for (const c of cases) {
        const r = results[c.id];
        if (r?.latest) {
          run += 1;
          if (r.latest.verdict.passed) {
            passed += 1;
            weightedPass += p.weight;
          }
        }
      }
    }
    return { passed, run, total: CASES.length, weightedPass, weightedTotal };
  }, [results]);

  const lastRun = useMemo(() => {
    let latest = 0;
    for (const r of Object.values(results)) if (r.latest && r.latest.record.summary.started_at > latest) latest = r.latest.record.summary.started_at;
    return latest;
  }, [results]);

  useRiseIn(grid, "[data-row]", [loading]);
  const selected = caseById(caseId);

  return (
    <div className={clsx("flex min-h-0 flex-1 flex-col", selected && "lg:grid lg:grid-cols-[minmax(480px,6fr)_minmax(460px,6fr)]")}>
      <div className={clsx("flex min-h-0 flex-1 flex-col", selected && "hidden lg:flex")}>
        <ScreenHeader
          title="Cases"
          lede={`${PROBLEMS.length} problems · ${CASES.length} public cases · Scored offline with leaderboard rules`}
          action={
            <button type="button" className="pill pill-primary on-primary" disabled title="Run All needs the backend's POST /api/runs; not available yet">
              Run All
            </button>
          }
        >
          <div className="mt-3 flex flex-wrap items-center gap-x-5 gap-y-1 text-[12px] text-fg-2">
            <span>
              <span className="mono text-fg tabular">
                {totals.passed}/{totals.run}
              </span>{" "}
              recorded cases passed
            </span>
            <span>
              <span className="mono text-fg tabular">
                {totals.weightedPass}/{totals.weightedTotal}
              </span>{" "}
              weighted points
            </span>
            {lastRun > 0 ? (
              <span>
                last run <span className="mono text-fg tabular">{wallClock(lastRun)}</span>
              </span>
            ) : null}
          </div>
        </ScreenHeader>

        <div ref={grid} className="scroll-y flex-1 px-2 pb-24 pt-2 md:px-8 md:pb-8">
          <div className="measure">
            <div className="hidden grid-cols-[32px_1.6fr_40px_1fr_120px_1fr] gap-3 px-3 pb-2 md:grid" aria-hidden="true">
              <Label>#</Label>
              <Label>problem</Label>
              <Label>w</Label>
              <Label>public cases</Label>
              <Label>last run</Label>
              <Label>failure signal</Label>
            </div>
            <ol className="m-0 grid list-none gap-0.5 p-0">
              {PROBLEMS.map((p, i) => {
                const cases = CASES.filter((c) => c.problem_id === p.id);
                const run = cases.filter((c) => results[c.id]?.latest);
                const passed = run.filter((c) => results[c.id]?.latest?.verdict.passed);
                const signals = [...new Set(run.map((c) => results[c.id]?.latest?.verdict.signal).filter((s): s is Verdict["signal"] => !!s && s !== "pass"))];
                return (
                  <li key={p.id} data-row className="row px-3 py-2.5">
                    <div className="grid grid-cols-[24px_1fr] items-center gap-x-3 gap-y-2 md:grid-cols-[32px_1.6fr_40px_1fr_120px_1fr]">
                      <span className="mono text-[12px] text-fg-3 tabular">{i + 1}</span>
                      <span className="min-w-0">
                        <span className="text-[14px] text-fg">{p.name}</span>
                        <span className="mono ml-2 hidden text-[11px] text-fg-3 xl:inline">{p.id}</span>
                      </span>
                      <span className="mono hidden text-[12px] text-fg-2 tabular md:block">{p.weight}</span>
                      <span className="col-span-2 flex flex-wrap items-center gap-1.5 md:col-span-1">
                        {cases.map((c) => (
                          <CaseGlyph key={c.id} result={results[c.id]} selected={c.id === caseId} onClick={() => navigate(`/cases/${c.id}`)} />
                        ))}
                      </span>
                      <span className="mono col-span-2 text-[12px] text-fg-2 tabular md:col-span-1">
                        {run.length > 0 ? `${passed.length}/${run.length}` : "\u2013"}
                        <span className="ml-2 text-fg-3 md:hidden">w{p.weight}</span>
                      </span>
                      <span className="col-span-2 flex flex-wrap gap-1.5 md:col-span-1">
                        {signals.map((s) => (
                          <span key={s} className="mono text-[12px] text-accent-ink">
                            {s}
                          </span>
                        ))}
                      </span>
                    </div>
                  </li>
                );
              })}
            </ol>
          </div>
        </div>
      </div>

      {selected ? (
        <div className="fixed inset-0 z-30 min-h-0 bg-bg lg:static lg:sticky lg:top-0 lg:z-auto lg:h-full">
          <CaseDrawer key={selected.id} testCase={selected} result={results[selected.id] ?? null} onClose={() => navigate("/cases")} />
        </div>
      ) : null}
    </div>
  );
}

function CaseGlyph({ result, selected, onClick }: { result: CaseResult | undefined; selected: boolean; onClick: () => void }) {
  const verdict = result?.latest?.verdict;
  const label = result ? `${result.testCase.id}: ${verdict ? (verdict.passed ? "pass" : verdict.signal) : "not run"}` : "case";
  return (
    <button
      type="button"
      onClick={onClick}
      className={clsx("grid size-7 place-items-center rounded-[8px] border transition-colors", selected ? "border-accent-ink" : "border-line-1 hover:border-line-2", verdict?.passed && "bg-surface-1")}
      aria-label={label}
      title={label}
    >
      {verdict ? (
        verdict.passed ? (
          <Check size={14} strokeWidth={2} className="text-accent-ink" />
        ) : (
          <X size={14} strokeWidth={2} className="text-fg-3" />
        )
      ) : (
        <span className="text-[12px] text-fg-3" aria-hidden="true">–</span>
      )}
    </button>
  );
}

function CaseDrawer({ testCase, result, onClose }: { testCase: PublicCase; result: CaseResult | null; onClose: () => void }) {
  const panel = useRef<HTMLElement>(null);
  useSlideIn(panel, window.matchMedia("(min-width: 1024px)").matches ? "x" : "y");
  const problem = problemOf(testCase.problem_id);
  const latest = result?.latest ?? null;
  const expected = testCase.expected.acceptable;
  return (
    <section ref={panel} className="flex h-full min-h-0 flex-col bg-bg lg:border-l lg:border-line-1" aria-label={`Case ${testCase.id}`}>
      <header className="flex flex-wrap items-center gap-2 border-b border-line-1 px-4 py-3 md:px-6">
        <div className="min-w-0 flex-1">
          <h2 className="truncate text-[18px] font-light text-fg">{problem.name}</h2>
          <p className="flex flex-wrap items-center gap-x-3 text-[12px] text-fg-3">
            <Mono dim className="truncate">
              {testCase.id}
            </Mono>
            <span>weight {problem.weight}</span>
            <span>{LANGUAGE_LABEL[testCase.language] ?? testCase.language}</span>
            {testCase.audio.background !== "silence" ? <span title="Background noise in the persona's audio">{testCase.audio.background} in the background</span> : null}
          </p>
        </div>
        <div className="ml-auto flex items-center gap-2">
          <button type="button" className="pill pill-quiet pill-sm" disabled title="Practice call needs the backend's POST /api/cases/{id}/call; not available yet">
            <Phone size={14} strokeWidth={1.75} /> Call
          </button>
          <button type="button" className="pill pill-quiet pill-sm pill-icon" onClick={onClose} aria-label="Close">
            <X size={14} strokeWidth={1.75} />
          </button>
        </div>
      </header>

      <div className="scroll-y min-h-0 flex-1 px-4 pb-8 pt-4 md:px-6">
        <section>
          <h2 className="text-[20px] font-light text-fg">{testCase.persona.name}</h2>
          <p className="mt-1 text-[14px] leading-[1.6] text-fg-2">{testCase.persona.description}</p>
          {testCase.summary ? <p className="mt-2 text-[14px] leading-[1.6] text-fg">{testCase.summary}</p> : null}
          <p className="mt-3 flex flex-wrap items-center gap-x-4 gap-y-1 text-[12px] text-fg-3">
            <Mono dim title="persona phone">
              {testCase.persona.phone}
            </Mono>
            <span>{testCase.persona.voice} voice</span>
            {testCase.protected.map((p) => (
              <span key={`${p.kind}-${p.value}`} className="text-accent-ink" title="Protected: must never be spoken by ROSARIO">
                protected {p.kind.replace("_", " ")}
              </span>
            ))}
          </p>
          {testCase.persona.objectives && testCase.persona.objectives.length > 0 ? (
            <details className="mt-3">
              <summary className="cursor-pointer text-[12px] text-fg-2">Persona objectives ({testCase.persona.objectives.length})</summary>
              <ul className="mt-2 grid list-disc gap-1.5 pl-5 text-[13px] leading-[1.5] text-fg-2">
                {testCase.persona.objectives.map((o, i) => (
                  <li key={i}>{o}</li>
                ))}
              </ul>
            </details>
          ) : null}
        </section>

        <section className="mt-6">
          <h3 className="text-[16px] font-light text-fg">Accepted answers</h3>
          <div className="mt-2 grid gap-2">
            {expected.map((alt, i) => (
              <div key={i} className="tile px-4 py-3">
                {expected.length > 1 ? <Label>alternative {i + 1}</Label> : null}
                {alt.actions.map((a, j) => (
                  <div key={j} className={j > 0 ? "mt-3 border-t border-line-1 pt-3" : ""}>
                    <div className="flex flex-wrap items-center gap-3">
                      <Outcome verb={a.action} size="sm" />
                      {a.reason ? <ReasonCode code={a.reason} /> : null}
                    </div>
                    <ActionTable action={a} className="mt-2" />
                  </div>
                ))}
              </div>
            ))}
          </div>
        </section>

        <section className="mt-6">
          <h3 className="text-[16px] font-light text-fg">Last run</h3>
          {!latest ? <Empty>No recorded call is attributed to this case yet.</Empty> : null}
          {latest ? (
            <div className="tile mt-2 px-4 py-3">
              <div className="flex flex-wrap items-center gap-2">
                <VerdictMark passed={latest.verdict.passed} signal={latest.verdict.signal} />
                <span className="mono ml-auto text-[12px] text-fg-3 tabular">
                  {wallClock(latest.record.summary.started_at)} · {duration(latest.record.summary.duration_seconds)}
                </span>
              </div>
              {latest.verdict.differences.length > 0 ? (
                <ul className="mono mt-3 grid list-none gap-1 p-0 text-[12px] text-fg-2">
                  {latest.verdict.differences.map((d) => (
                    <li key={d}>{d}</li>
                  ))}
                </ul>
              ) : null}
              {latest.verdict.leaks.map((l) => (
                <p key={l} className="mono mt-2 text-[12px] text-accent-ink">
                  {l}
                </p>
              ))}
              {latest.record.detail && latest.record.detail.submissions.length > 0 ? (
                <div className="mt-3 border-t border-line-1 pt-3">
                  <Label>submitted</Label>
                  {latest.record.detail.submissions.map((s, i) => (
                    <ActionTable key={i} action={s.action} className="mt-2" />
                  ))}
                </div>
              ) : null}
              <div className="mt-3 flex flex-wrap items-center gap-2">
                <Link to={`/calls/${latest.record.summary.call_id}`} className="pill pill-ghost pill-sm">
                  Open transcript
                </Link>
                {result && result.attempts > 1 ? <span className="text-[12px] text-fg-3">{result.attempts} recorded attempts; showing the latest.</span> : null}
              </div>
            </div>
          ) : null}
        </section>
      </div>
    </section>
  );
}
