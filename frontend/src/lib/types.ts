// Shapes read from the call log backend (GET /api/calls, GET /api/calls/{id}).
// Field names are the backend's, verbatim. Everything the screens render is a
// projection of `CallDetail.events`.

export type ActionVerb = "REGISTER" | "BOOK" | "RESCHEDULE" | "CANCEL" | "NO_ACTION" | "ESCALATE";

export interface ClinicAction {
  action: ActionVerb | string;
  patient_id?: string;
  provider_id?: string;
  location_id?: string;
  appointment_type_id?: string;
  appointment_id?: string;
  slot?: string;
  policy_id?: string;
  reason?: string;
  given_name?: string;
  first_surname?: string;
  second_surname?: string;
  national_id?: string;
  date_of_birth?: string;
  phone?: string;
  email?: string;
  insurer?: string;
  new_patient?: Record<string, unknown>;
  [key: string]: unknown;
}

export interface RunRef {
  run_id: string;
  mode: string;
  problem_id: string;
  case_id: string;
  suite_position?: number | null;
  suite_total?: number | null;
}

/** `status` is "in progress", "ended", "saved" (at least one write) or "write failed". */
export type CallStatus = "in progress" | "ended" | "saved" | "write failed";

export interface CallSummary {
  call_id: string;
  started_at: number;
  modified_at: number;
  modified_iso: string | null;
  status: CallStatus | string;
  /** Verbs written, joined with "+" ("REGISTER+BOOK"); else the last staged verb. */
  action: string;
  duration_seconds: number | null;
  warnings: number;
  has_audio: boolean;
  credits: { provider: string; detail: string } | null;
  run: RunRef | null;
}

export interface CallsIndex {
  calls_dir: string;
  calls: CallSummary[];
}

export interface AudioInfo {
  url: string;
  channels: number;
  sample_rate: number;
  sample_width: number | null;
  frames: number;
  duration_seconds: number;
  timeline_clock: string | null;
  /** Epoch seconds at recording position zero, recovered from the recorder clock. */
  timeline_origin_at: number | null;
  caller_carrier_drift_seconds: number | null;
  /** Audio-derived speech endings keyed by the transcript's JSONL line number. */
  transcript_end_seconds?: Record<string, number>;
}

/** One line of the per-call JSONL. `t` is epoch seconds, `_line` the file line. */
export interface RawEvent {
  t: number;
  kind: string;
  _line?: number;
  [key: string]: unknown;
}

export interface TranscriptEvent extends RawEvent {
  kind: "transcript";
  role: "agent" | "user" | string;
  text: string;
}

export interface ToolEvent extends RawEvent {
  kind: "tool";
  name: string;
  args: Record<string, unknown>;
  result: unknown;
}

/** Legacy: call logs written before the clinic database still carry these. */
export interface SubmitEvent extends RawEvent {
  kind: "submit";
  action: ClinicAction;
  status: number;
  response: unknown;
}

/** One committed write to the clinic database (`local_write` in the call log). */
export interface LocalWriteEvent extends RawEvent {
  kind: "local_write";
  action: ClinicAction;
  result: Record<string, unknown> | null;
}

export interface StagedEvent extends RawEvent {
  kind: "action_staged";
  action: ClinicAction;
  all_staged: ClinicAction[];
}

/** A saved write traced back to the staged action and the lookup before it. */
export interface ProvenanceChain {
  lookup: ToolEvent | null;
  recorded: RawEvent | null;
  write: LocalWriteEvent | null;
  action: ClinicAction;
}

export interface CallDetail {
  call_id: string;
  /** Directory name for the logged phone match; not verified patient identity. */
  caller_id?: { patient_id: string; name: string; source: "caller_id" } | null;
  summary: CallSummary;
  run: RunRef | null;
  warnings: string[];
  audio: AudioInfo | null;
  transcript: TranscriptEvent[];
  tools: ToolEvent[];
  staged_actions: StagedEvent[];
  /** Successful writes to the clinic database, in log order. */
  writes: LocalWriteEvent[];
  errors: RawEvent[];
  provenance: ProvenanceChain[];
  events: RawEvent[];
}
