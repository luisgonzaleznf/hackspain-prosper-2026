// Call state is a short, readable label with a functional icon.

import { clsx } from "clsx";
import { CalendarDays, Check, ClipboardCheck, Phone, Search, ShieldCheck, UserRound, ArrowUpRight } from "lucide-react";
import type { Stage } from "@/lib/timeline";

const ICON = { GREET: Phone, IDENTIFY: UserRound, LOOKUP: Search, OFFER: CalendarDays, CONFIRM: ShieldCheck, WRITE: ClipboardCheck, CLOSE: Check, ESCALATE: ArrowUpRight } as const;
const LABEL: Record<Stage, string> = { GREET: "Greeting", IDENTIFY: "Identifying", LOOKUP: "Looking up", OFFER: "Offering", CONFIRM: "Confirming", WRITE: "Writing", CLOSE: "Closed", ESCALATE: "Escalated" };

export function stageLabel(stage: Stage): string {
  return LABEL[stage];
}

export function StageIndicator({ stage, size = "sm", className }: { stage: Stage; size?: "sm" | "md"; className?: string }) {
  const Icon = ICON[stage];
  return <span className={clsx("inline-flex items-center gap-2", size === "sm" ? "text-[12px]" : "text-[14px]", stage === "ESCALATE" ? "text-accent-ink" : "text-fg-2", className)}>
    <Icon size={size === "sm" ? 13 : 15} strokeWidth={1.5} aria-hidden="true" />{LABEL[stage]}
  </span>;
}
