// Shared primitives. Machine text (ids, tool names, reason codes) is plain mono
// in the text ladder, never a chip. State is shown with an icon and text.

import { Select } from "@base-ui/react/select";
import { clsx } from "clsx";
import type { Icon } from "@phosphor-icons/react";
import { WarningIcon } from "@phosphor-icons/react/dist/csr/Warning";
import { ProhibitIcon } from "@phosphor-icons/react/dist/csr/Prohibit";
import { CalendarCheckIcon } from "@phosphor-icons/react/dist/csr/CalendarCheck";
import { CalendarXIcon } from "@phosphor-icons/react/dist/csr/CalendarX";
import { CheckIcon } from "@phosphor-icons/react/dist/csr/Check";
import { CaretDownIcon } from "@phosphor-icons/react/dist/csr/CaretDown";
import { CopyIcon } from "@phosphor-icons/react/dist/csr/Copy";
import { PhoneTransferIcon } from "@phosphor-icons/react/dist/csr/PhoneTransfer";
import { ArrowsClockwiseIcon } from "@phosphor-icons/react/dist/csr/ArrowsClockwise";
import { UserPlusIcon } from "@phosphor-icons/react/dist/csr/UserPlus";
import { useEffect, useState, type ReactNode } from "react";
import { REASON_GLOSS, TOOL_GLOSS } from "@/lib/timeline";

/** Inline machine text: an id, a tool name, a slot. */
export function Mono({ children, className, dim, title }: { children: ReactNode; className?: string; dim?: boolean; title?: string }) {
  return (
    <span className={clsx("mono text-[12px] tabular", dim ? "text-fg-3" : "text-fg-2", className)} title={title}>
      {children}
    </span>
  );
}

/** Reason code verbatim in mono, its gloss beside it. Never rephrased. */
export function ReasonCode({ code, className }: { code: string; className?: string }) {
  const gloss = REASON_GLOSS[code];
  return (
    <span className={clsx("inline-flex flex-wrap items-baseline gap-x-2 gap-y-0.5", className)}>
      <span className="mono text-[12px] text-accent-ink">{code}</span>
      <span className="text-[13px] text-fg-2">{gloss ?? "reason outside the vocabulary"}</span>
    </span>
  );
}

export function ToolName({ name }: { name: string }) {
  const gloss = TOOL_GLOSS[name];
  return (
    <span className="inline-flex flex-wrap items-baseline gap-x-2 gap-y-0.5">
      <span className="mono text-[12px] text-fg">{name}</span>
      {gloss ? <span className="text-[13px] text-fg-2">{gloss}</span> : null}
    </span>
  );
}

const OUTCOME_ICON: Record<string, Icon> = { BOOK: CalendarCheckIcon, RESCHEDULE: ArrowsClockwiseIcon, CANCEL: CalendarXIcon, REGISTER: UserPlusIcon, NO_ACTION: ProhibitIcon, ESCALATE: PhoneTransferIcon };
export const OUTCOME_LABEL: Record<string, string> = { BOOK: "Booked", RESCHEDULE: "Moved", CANCEL: "Cancelled", REGISTER: "Registered", NO_ACTION: "Declined", ESCALATE: "Escalated" };

/** Outcome as icon + word; the reason code follows in mono when there is one. A failed write reads as such. */
export function Outcome({ verb, reason, failed = false, size = "md", className }: { verb: string; reason?: string | null; failed?: boolean; size?: "sm" | "md"; className?: string }) {
  const Icon = failed ? WarningIcon : OUTCOME_ICON[verb] ?? WarningIcon;
  const attention = failed || verb === "NO_ACTION" || verb === "ESCALATE";
  return (
    <span className={clsx("inline-flex min-w-0 items-center gap-2", size === "sm" ? "text-[13px]" : "text-[14px]", className)} title={failed ? `Write failed while trying: ${OUTCOME_LABEL[verb] ?? verb}` : undefined}>
      <Icon size={size === "sm" ? 14 : 16} className={clsx("shrink-0", attention ? "text-accent-ink" : "text-fg-2")} />
      <span className={clsx("truncate", failed ? "text-accent-ink" : "text-fg")}>
        {failed ? "Write failed" : OUTCOME_LABEL[verb] ?? verb}
      </span>
      {reason && !failed ? <span className="mono hidden truncate text-[12px] text-fg-3 md:inline">{reason}</span> : null}
    </span>
  );
}

export function CopyButton({ value, label = "Copy" }: { value: string; label?: string }) {
  const [copied, setCopied] = useState(false);
  useEffect(() => {
    if (!copied) return;
    const timer = window.setTimeout(() => setCopied(false), 1500);
    return () => window.clearTimeout(timer);
  }, [copied]);
  return (
    <button
      type="button"
      className="pill pill-quiet pill-sm pill-icon"
      aria-label={copied ? "Copied" : label}
      title={copied ? "Copied" : label}
      onClick={() => {
        void navigator.clipboard?.writeText(value).then(() => setCopied(true));
      }}
    >
      {copied ? <CheckIcon size={14} /> : <CopyIcon size={14} />}
    </button>
  );
}

export function Empty({ children }: { children: ReactNode }) {
  return <p className="px-1 py-6 text-[14px] text-fg-2">{children}</p>;
}

/** Column headers and key labels in mono uppercase grey. */
export function Label({ children, className }: { children: ReactNode; className?: string }) {
  return <span className={clsx("t-mono-xs uppercase text-fg-3", className)}>{children}</span>;
}

/** Status text that fades and slides 8px when it changes (200ms). */
export function SwapText({ text, className }: { text: string; className?: string }) {
  return (
    <span key={text} className={clsx("swap-enter inline-block min-w-0 max-w-full", className)}>
      {text}
    </span>
  );
}

export function KeyValue({ rows, className }: { rows: [string, string][]; className?: string }) {
  if (rows.length === 0) return null;
  return (
    <dl className={clsx("grid grid-cols-[minmax(96px,max-content)_1fr] gap-x-4 gap-y-1.5 text-[12px]", className)}>
      {rows.map(([k, v], i) => (
        <div key={`${k}-${i}`} className="contents">
          <dt className="mono truncate text-fg-3" title={k}>
            {k}
          </dt>
          <dd className="mono m-0 break-words text-fg">{v}</dd>
        </div>
      ))}
    </dl>
  );
}

/** Styled select on Base UI. */
export function PillSelect<T extends string>({ value, onChange, options, label, className }: { value: T; onChange: (v: T) => void; options: { value: T; label: string; hint?: string }[]; label: string; className?: string }) {
  return (
    <Select.Root value={value} onValueChange={(v) => v != null && onChange(v as T)}>
      <Select.Trigger className={clsx("select-trigger", className)} aria-label={label}>
        <Select.Value>{(v: T) => options.find((o) => o.value === v)?.label ?? String(v)}</Select.Value>
        <Select.Icon>
          <CaretDownIcon size={14} />
        </Select.Icon>
      </Select.Trigger>
      <Select.Portal>
        <Select.Positioner sideOffset={6} align="start" alignItemWithTrigger={false} className="z-50">
          <Select.Popup className="select-popup">
            <Select.List>
              {options.map((o) => (
                <Select.Item key={o.value} value={o.value} className="select-item">
                  <Select.ItemIndicator className="select-item-check" keepMounted>
                    <CheckIcon size={14} />
                  </Select.ItemIndicator>
                  <Select.ItemText>{o.label}</Select.ItemText>
                  {o.hint ? <span className="mono ml-auto text-[11px] text-fg-3">{o.hint}</span> : null}
                </Select.Item>
              ))}
            </Select.List>
          </Select.Popup>
        </Select.Positioner>
      </Select.Portal>
    </Select.Root>
  );
}
