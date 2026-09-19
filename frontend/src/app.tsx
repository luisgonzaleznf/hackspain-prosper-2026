import { clsx } from "clsx";
import { Activity, ArrowLeft, ArrowUpRight, CalendarDays, ChartNoAxesCombined, PanelLeftClose, PanelLeftOpen, Phone, Search } from "lucide-react";
import { useState, type ReactNode } from "react";
import { Link, NavLink, Outlet, useLocation } from "react-router";
import { isActive, useCallsIndex, usePolling } from "@/lib/store";
import { SelectionIndicator } from "@/components/selection-indicator";
import { ThemeToggle } from "@/components/theme-toggle";

const NAV = [
  { to: "/metrics", label: "Overview", icon: ChartNoAxesCombined },
  { to: "/calls", label: "Calls", icon: Phone },
  { to: "/calendar", label: "Calendar", icon: CalendarDays },
  { to: "/live", label: "Live", icon: Activity },
] as const;

export function Shell() {
  usePolling();
  const { calls, error, loadedAt } = useCallsIndex();
  const active = calls.filter(isActive).length;
  const [railOpen, setRailOpen] = useState(true);
  const { pathname } = useLocation();

  return (
    <div className="h-dvh overflow-hidden md:grid md:grid-cols-[auto_1fr]">
      <aside className={clsx("dashboard-rail hidden border-r border-line-1 md:flex md:h-dvh md:flex-col md:py-6", railOpen ? "md:w-[208px] md:px-4" : "md:w-[72px] md:px-3")} aria-label="Dashboard sidebar">
        <div className="flex items-center justify-between gap-2 px-2">
          <a href="/" className="flex min-h-11 items-center gap-3" aria-label="ROSARIO home">
            <Mark className="size-7 shrink-0 text-accent-ink" />
            {railOpen ? <span className="text-[23px] font-light tracking-tight text-fg">rosario</span> : null}
          </a>
          {railOpen ? <button type="button" className="rail-collapse" onClick={() => setRailOpen(false)} aria-label="Collapse navigation"><PanelLeftClose size={15} /></button> : null}
        </div>
        <nav className="relative isolate mt-10 grid gap-1" aria-label="Dashboard navigation">
          <SelectionIndicator activeKey={pathname} />
          {NAV.map(({ to, label, icon: Icon }) => (
            <NavLink key={to} to={to} title={label} className={({ isActive: on }) => clsx("sliding-tab flex min-h-12 items-center gap-3 rounded-tags px-3 text-[14px]", on ? "text-fg" : "text-fg-2 hover:text-fg", !railOpen && "justify-center")}>
              <Icon size={18} strokeWidth={1.5} />
              {railOpen ? <span>{label}</span> : <span className="sr-only">{label}</span>}
              {to === "/live" && active > 0 && railOpen ? <span className="mono ml-auto text-[12px] text-fg-2">{active}</span> : null}
            </NavLink>
          ))}
        </nav>
        <footer className="mt-auto grid gap-5">
          {railOpen ? <div className="px-3 text-[12px] leading-relaxed text-fg-3">
            <span className="flex items-center gap-2"><Activity size={14} />{error ? "Connection interrupted" : loadedAt ? active > 0 ? `${active} calls in progress` : "Recorded calls" : "Loading recordings"}</span>
          </div> : <button className="rail-collapse mx-auto" onClick={() => setRailOpen(true)} aria-label="Expand navigation"><PanelLeftOpen size={18} /></button>}
          <div className={clsx("grid gap-3 border-t border-line-1 pt-4", !railOpen && "justify-items-center")}>
            <ThemeToggle compact={!railOpen} />
            {railOpen ? <a href="/" className="flex min-h-9 items-center justify-between px-3 text-[12px] text-fg-3 hover:text-fg">About ROSARIO<ArrowUpRight size={13} /></a> : null}
          </div>
        </footer>
      </aside>
      <div className="flex h-full min-h-0 min-w-0 flex-col overflow-hidden"><Outlet /></div>
      <nav className="safe-b fixed inset-x-0 bottom-0 z-20 border-t border-line-1 bg-bg p-1.5 md:hidden" aria-label="Dashboard navigation">
        <div className="relative isolate grid grid-cols-4">
          <SelectionIndicator activeKey={pathname} />
          {NAV.map(({ to, label, icon: Icon }) => (
            <NavLink key={to} to={to} className={({ isActive: on }) => clsx("sliding-tab flex flex-col items-center gap-1 rounded-tags py-2 text-[11px]", on ? "text-fg" : "text-fg-3")}>
              <Icon size={18} strokeWidth={1.5} />{label}
              {to === "/live" && active > 0 ? <span className="sr-only">{active} active</span> : null}
            </NavLink>
          ))}
        </div>
      </nav>
    </div>
  );
}

/** Secondary tools intentionally live outside the clinic dashboard. */
export function ToolsShell() {
  usePolling();
  return <div className="flex h-dvh flex-col overflow-hidden">
    <header className="flex shrink-0 items-center justify-between gap-3 border-b border-line-1 px-4 py-3 md:px-8">
      <Link to="/metrics" className="flex min-h-9 items-center gap-2 text-[13px] text-fg-2 hover:text-fg"><ArrowLeft size={15} />Dashboard</Link>
      <nav className="flex items-center gap-4 text-[12px] text-fg-3" aria-label="Secondary tools">
        <NavLink to="/cases" className={({ isActive }) => isActive ? "text-fg" : "hover:text-fg"}>Rehearsal</NavLink>
        <NavLink to="/talk" className={({ isActive }) => isActive ? "text-fg" : "hover:text-fg"}>Voice demo</NavLink>
        <ThemeToggle compact />
      </nav>
    </header>
    <div className="flex min-h-0 flex-1 flex-col overflow-hidden"><Outlet /></div>
  </div>;
}

export function Mark({ className }: { className?: string }) {
  return (
    <svg viewBox="-21.7 -14.7 1054.4 1054.4" className={className} fill="currentColor" aria-hidden="true">
      <ellipse cx="505.5" cy="512.5" rx="446.5" ry="454.5" />
      <g fill="var(--bg)">
        <ellipse cx="505.5" cy="182.8" rx="78.2" ry="78.2" />
        <ellipse cx="699.3" cy="245.8" rx="78.2" ry="78.2" />
        <ellipse cx="819.0" cy="410.6" rx="78.2" ry="78.2" />
        <ellipse cx="819.0" cy="614.4" rx="78.2" ry="78.2" />
        <ellipse cx="699.3" cy="779.2" rx="78.2" ry="78.2" />
        <ellipse cx="505.5" cy="842.2" rx="78.2" ry="78.2" />
        <ellipse cx="311.7" cy="779.2" rx="78.2" ry="78.2" />
        <ellipse cx="192.0" cy="614.4" rx="78.2" ry="78.2" />
        <ellipse cx="192.0" cy="410.6" rx="78.2" ry="78.2" />
        <ellipse cx="311.7" cy="245.8" rx="78.2" ry="78.2" />
        <path d="m695.5 531c-15.5-67-58.5-115-115.5-134-60-21-121-6-163 34-29 28-43 62-38.5 103 3.5 40 26.5 72 64.5 86 36 13 75 3 99-25 20-23 28-55 13-79-11-18-31-28-50-26-18 1-30 12-34 30.5 18-3.5 32 8.5 34.5 21 4.5 19.5-11.5 33.5-29.5 35-25 2.5-47-15.5-53-38.5-7-25 3-54 22-73 25-24 59-32 92-22 51 15 85 58 91 105 6 46-17 93-52 120-38 29-87 36-128 26-60-13-106-58-126-113-19-52-11-109 15-156 32-57 90-94 152-99 69-7 133 25 172 78 25 35 38 79 34.5 127z" />
      </g>
    </svg>
  );
}

/** Screen header: title, optional lede, search, the one primary action. */
export function ScreenHeader({
  title,
  lede,
  action,
  search,
  children,
}: {
  title: string;
  lede?: string;
  action?: ReactNode;
  search?: { placeholder: string; value: string; onChange: (v: string) => void };
  children?: ReactNode;
}) {
  return (
    <header className="relative z-10 shrink-0 border-b border-line-1 bg-bg px-4 pb-3 pt-4 md:px-8 md:pt-6">
      <div className="absolute right-4 top-2 md:hidden"><ThemeToggle compact /></div>
      <div className="measure">
        <div className="flex flex-wrap items-end justify-between gap-3">
          <div className="min-w-0">
            <a href="/" className="flex min-h-8 items-center gap-3 md:hidden" aria-label="ROSARIO home">
              <Mark className="size-5 text-accent-ink" />
              <span className="text-[14px] text-fg-2">rosario</span>
            </a>
            <h1 className="t-title mt-3 text-fg md:mt-0">{title}</h1>
            {lede ? <p className="mt-1 max-w-[60ch] text-[14px] text-fg-2">{lede}</p> : null}
          </div>
          {search || action ? <div className={search ? "flex w-full flex-wrap items-center gap-2 sm:w-auto" : "flex flex-wrap items-center gap-2"}>
            {search ? (
              <label className="relative flex-1 sm:w-[260px] sm:flex-none">
                <Search size={14} strokeWidth={1.5} className="pointer-events-none absolute left-4 top-1/2 -translate-y-1/2 text-fg-3" />
                <input className="input pl-10" placeholder={search.placeholder} value={search.value} onChange={(e) => search.onChange(e.target.value)} type="search" aria-label={search.placeholder} />
              </label>
            ) : null}
            {action}
          </div> : null}
        </div>
        {children}
      </div>
    </header>
  );
}
