import { X } from "lucide-react";

export function LoadingRows({ label, rows = 6, compact = false, live = false }: { label: string; rows?: number; compact?: boolean; live?: boolean }) {
  return <div role="status" aria-label={label} className={`loading-rows ${compact ? "loading-rows-compact" : ""} ${live ? "loading-rows-live" : ""}`}>
    <span className="sr-only">{label}</span>
    <div className="loading-table-head" aria-hidden="true"><span className="loading-skeleton loading-row-title" /></div>
    {!live ? <div className="loading-group" aria-hidden="true"><span className="loading-skeleton loading-row-subtitle" /></div> : null}
    {Array.from({ length: rows }, (_, index) => <div key={index} className="loading-row" aria-hidden="true">
      {live ? <span className="loading-skeleton loading-row-orb" /> : null}
      <span className="loading-skeleton loading-row-time" />
      <div><span className="loading-skeleton loading-row-title" /><span className="loading-skeleton loading-row-subtitle" /></div>
      <span className="loading-skeleton loading-row-strip" />
      <span className="loading-skeleton loading-row-outcome" />
      {!compact && !live ? <span className="loading-skeleton loading-row-duration" /> : null}
      <span className="loading-skeleton loading-row-value" />
    </div>)}
  </div>;
}

export function LoadingConversation({ search = false }: { search?: boolean }) {
  return <div role="status" aria-label="Loading conversation" className="loading-conversation">
    <span className="sr-only">Loading conversation</span>
    {search ? <div className="loading-conversation-toolbar" aria-hidden="true"><span className="loading-skeleton" /><span className="loading-skeleton" /></div> : null}
    {["agent", "caller", "agent", "caller"].map((speaker, index) => <div key={index} className={`loading-message loading-message-${speaker}`} aria-hidden="true">
      <span className="loading-skeleton loading-message-label" />
      <div className="loading-message-bubble"><span className="loading-skeleton" /><span className="loading-skeleton" /></div>
    </div>)}
  </div>;
}

export function LoadingTimeline() {
  return <div className="loading-timeline" aria-hidden="true">
    <div className="loading-timeline-markers"><span className="loading-skeleton" /><span className="loading-skeleton" /><span className="loading-skeleton" /></div>
    <div className="loading-timeline-track"><span className="loading-skeleton" /><span className="loading-skeleton" /></div>
    <span className="loading-skeleton" />
    <div className="loading-timeline-ruler"><span className="loading-skeleton" /><span className="loading-skeleton" /></div>
    <div className="loading-timeline-controls"><span className="loading-skeleton" /><span className="loading-skeleton" /></div>
  </div>;
}

export function ProgressStrip({ label, value, max }: { label: string; value: number; max: number }) {
  const completed = Math.min(max, Math.max(0, value));
  return <div className="loading-progress">
    <span>{label}</span>
    <div className="loading-progress-track" role="progressbar" aria-label={label} aria-valuemin={0} aria-valuemax={Math.max(1, max)} aria-valuenow={max > 0 ? completed : undefined}>
      <span style={{ transform: `scaleX(${max > 0 ? completed / max : 0})` }} />
    </div>
    {max > 0 ? <span className="mono tabular">{completed}/{max}</span> : null}
  </div>;
}

export function LoadingCall({ onClose }: { onClose: () => void }) {
  return <section className="flex h-full flex-col bg-bg" aria-label="Loading call">
    <header className="flex min-h-[70px] items-center justify-between border-b border-line-1 px-4 py-3 md:px-6">
      <h2 className="text-[18px] font-light text-fg">Loading call</h2>
      <button type="button" className="pill pill-quiet pill-sm pill-icon" onClick={onClose} aria-label="Close call"><X size={14} strokeWidth={1.75} /></button>
    </header>
    <div className="border-y border-line-1 px-4 py-3 md:px-6"><LoadingTimeline /></div>
    <div className="loading-call-tabs px-4 md:px-6" aria-hidden="true"><span className="loading-skeleton" /><span className="loading-skeleton" /><span className="loading-skeleton" /></div>
    <div className="px-4 md:px-6"><LoadingConversation search /></div>
  </section>;
}
