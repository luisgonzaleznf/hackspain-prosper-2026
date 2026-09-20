// Call state is a short, readable label with a functional icon.

import { clsx } from "clsx";
import { CalendarDotsIcon } from "@phosphor-icons/react/dist/csr/CalendarDots";
import { CheckIcon } from "@phosphor-icons/react/dist/csr/Check";
import { ClipboardTextIcon } from "@phosphor-icons/react/dist/csr/ClipboardText";
import { PhoneIcon } from "@phosphor-icons/react/dist/csr/Phone";
import { MagnifyingGlassIcon } from "@phosphor-icons/react/dist/csr/MagnifyingGlass";
import { ShieldCheckIcon } from "@phosphor-icons/react/dist/csr/ShieldCheck";
import { UserIcon } from "@phosphor-icons/react/dist/csr/User";
import { ArrowUpRightIcon } from "@phosphor-icons/react/dist/csr/ArrowUpRight";
import type { Stage } from "@/lib/timeline";

const ICON = { GREET: PhoneIcon, IDENTIFY: UserIcon, LOOKUP: MagnifyingGlassIcon, OFFER: CalendarDotsIcon, CONFIRM: ShieldCheckIcon, WRITE: ClipboardTextIcon, CLOSE: CheckIcon, ESCALATE: ArrowUpRightIcon } as const;
const LABEL: Record<Stage, string> = { GREET: "Greeting", IDENTIFY: "Identifying", LOOKUP: "Looking up", OFFER: "Offering", CONFIRM: "Confirming", WRITE: "Writing", CLOSE: "Closed", ESCALATE: "Escalated" };

export function stageLabel(stage: Stage): string {
  return LABEL[stage];
}

export function StageIndicator({ stage, size = "sm", className }: { stage: Stage; size?: "sm" | "md"; className?: string }) {
  const Icon = ICON[stage];
  return <span className={clsx("inline-flex items-center gap-2", size === "sm" ? "text-[12px]" : "text-[14px]", stage === "ESCALATE" ? "text-accent-ink" : "text-fg-2", className)}>
    <Icon size={size === "sm" ? 13 : 15} aria-hidden="true" />{LABEL[stage]}
  </span>;
}
