import { CircleNotchIcon } from "@phosphor-icons/react/dist/csr/CircleNotch";
import "./call-status.css";

export function CallInProgress({ endedAt }: { endedAt?: number | null }) {
  if (endedAt != null) return <span className="text-[13px] text-fg-3">Call ended</span>;
  return (
    <span className="inline-flex items-center gap-2 whitespace-nowrap text-[13px] text-accent-ink">
      <CircleNotchIcon size={14} className="call-status-spinner shrink-0" aria-hidden="true" />
      In progress
    </span>
  );
}
