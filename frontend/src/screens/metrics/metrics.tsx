import NumberFlow from "@number-flow/react";
import { ArrowUpRightIcon } from "@phosphor-icons/react/dist/csr/ArrowUpRight";
import { useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import { Link } from "react-router";
import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { ScreenHeader } from "@/app";
import { ProgressStrip } from "@/components/loading";
import { PillSelect } from "@/components/primitives";
import { SelectionIndicator } from "@/components/selection-indicator";
import { dayLabel, duration, wallClock } from "@/lib/format";
import { loadDetail, refreshNow, useCallsIndex } from "@/lib/store";
import { aggregateOverview, currentDetail, detailSample, outcomeLabel, selectCalls, type OverviewRange, type OverviewSeries } from "./overview-data";
import "./overview.css";

const SERIES: { id: OverviewSeries; label: string }[] = [
  { id: "calls", label: "Calls handled" },
  { id: "bookings", label: "Bookings" },
  { id: "duration", label: "Call duration" },
];
const NUMBER_TIMING = { duration: 150, easing: "cubic-bezier(0.23, 1, 0.32, 1)" };

export function MetricsScreen() {
  const { calls, byId, error, loadedAt } = useCallsIndex();
  const [range, setRange] = useState<OverviewRange>("14d");
  const [series, setSeries] = useState<OverviewSeries>("calls");
  const [retryAttempt, setRetryAttempt] = useState(0);
  const [refreshing, setRefreshing] = useState(false);
  const [settledRequest, setSettledRequest] = useState<string | null>(null);
  const latest = useRef({ sample: [] as typeof calls, byId });
  const activeBatch = useRef<Promise<void>>(Promise.resolve());
  const available = loadedAt != null;
  const now = (loadedAt ?? Date.now()) / 1000;
  const scoped = useMemo(() => selectCalls(calls, range, now), [calls, range, now]);
  const sample = useMemo(() => detailSample(scoped), [scoped]);
  const hasDemoHistory = scoped.some((call) => call.call_id.startsWith("demo-metrics-"));
  const sampleKey = JSON.stringify(sample.map((call) => [call.call_id, call.modified_at]));
  const requestKey = `${retryAttempt}:${sampleKey}`;
  const stats = useMemo(() => aggregateOverview(scoped, byId, range, now), [scoped, byId, range, now]);
  const loadedDetails = stats.loaded;
  const failedDetails = sample.filter((call) => !currentDetail(call, byId) && byId[call.call_id]?.detailError).length;
  const incomplete = loadedDetails < sample.length;
  const detailsPending = incomplete && settledRequest !== requestKey;

  useLayoutEffect(() => {
    latest.current = { sample, byId };
  }, [sample, byId]);

  useEffect(() => {
    let cancelled = false;
    const pending = latest.current.sample.filter((call) => {
      const record = latest.current.byId[call.call_id];
      return (!currentDetail(call, latest.current.byId) || record?.detailError) && (!record?.detailError || retryAttempt > 0);
    });
    async function loadSample() {
      await activeBatch.current;
      for (let index = 0; index < pending.length && !cancelled; index += 4) {
        const batch = pending.slice(index, index + 4).filter((call) => !currentDetail(call, latest.current.byId));
        activeBatch.current = Promise.all(batch.map((call) => loadDetail(call.call_id, true))).then(() => {});
        await activeBatch.current;
      }
      if (!cancelled) setSettledRequest(requestKey);
    }
    void loadSample();
    return () => { cancelled = true; };
  }, [requestKey, retryAttempt]);

  const finishedCount = stats.finished.length;
  const totalDescription = !available
    ? error ? "Call records could not be loaded." : "Loading reception activity."
    : series === "calls"
      ? `${finishedCount.toLocaleString("en-GB")} completed calls in this range.`
      : series === "bookings"
        ? stats.bookings == null ? "No booking details are available for this range." : `${stats.bookings.toLocaleString("en-GB")} appointments booked or moved by Rosario in ${stats.loaded} loaded calls.${incomplete ? " Partial sample." : ""}`
        : stats.duration == null ? "No recorded call durations in this range." : `${duration(stats.duration)} average across ${stats.durationCount} calls with a recorded duration.`;
  const chartHasData = series === "calls" ? finishedCount > 0 : series === "bookings" ? stats.loaded > 0 : stats.durationCount > 0;
  const chartPending = !available && !error || series === "bookings" && detailsPending && !chartHasData;
  const chartReady = available && chartHasData;

  return (
    <div className="overview-screen flex min-h-0 flex-1 flex-col">
      <ScreenHeader title="Overview" />
      <div className="scroll-y overview-scroll flex-1">
        <div className="measure overview-content">
          <div className="overview-toolbar">
            <div className="overview-dates">
              <p>{available ? `${dayLabel(stats.start)} to ${dayLabel(now)}` : "Call activity"}</p>
              <span className="overview-timezone">Europe/Madrid{hasDemoHistory ? " · Includes demo history" : ""}</span>
            </div>
            <div className="overview-range">
              <PillSelect value={range} onChange={setRange} label="Time range" options={[{ value: "24h", label: "Last 24 hours" }, { value: "7d", label: "Last 7 days" }, { value: "14d", label: "Last 14 days" }, { value: "all", label: "All recorded calls" }]} />
            </div>
          </div>

          {error ? <div className="overview-notice" role="status"><p>{available ? "Updates paused. Showing the last loaded records." : "Call records could not be loaded."} {error}</p><button type="button" disabled={refreshing} onClick={async () => { setRefreshing(true); try { await refreshNow(); } finally { setRefreshing(false); } }}>{refreshing ? "Retrying…" : "Try again"}</button></div> : null}

          <section className="overview-stats" aria-label="Reception summary">
            <Stat label="Calls handled" value={available ? finishedCount : null} pending={!available && !error} />
            <Stat label="Bookings saved" value={stats.bookings} pending={(!available && !error || detailsPending) && stats.bookings == null} accent />
            <Stat label="Average call" value={available ? stats.duration : null} pending={!available && !error} unit="sec" />
            <Stat label="Median response gap" value={stats.latency == null ? null : stats.latency / 1000} pending={(!available && !error || detailsPending) && stats.latency == null} unit="sec" decimals={1} />
          </section>
          <div className="overview-coverage">
            <div className="overview-sample-status">
              {detailsPending ? <ProgressStrip label="Partial sample" value={loadedDetails + failedDetails} max={sample.length} /> : <span role="status">{!available ? error ? "Call records unavailable" : "Loading call records" : incomplete ? `${loadedDetails}/${sample.length} calls sampled · partial` : `${loadedDetails} calls sampled`}</span>}
              {failedDetails > 0 ? <button type="button" disabled={detailsPending} onClick={() => setRetryAttempt((attempt) => attempt + 1)}>{detailsPending ? `${failedDetails} failed` : `Retry ${failedDetails} failed`}</button> : null}
            </div>
            <p>Bookings sampled · Gap: {stats.latencyCount} call medians<span className="sr-only">. Response gap is the median of these recorded per-call medians.</span></p>
          </div>

          <div className="overview-chart-layout">
            <section className="overview-activity" aria-labelledby="activity-title">
              <div className="overview-section-heading">
                <h2 id="activity-title">Reception activity</h2>
                <span className="overview-chart-unit">{series === "duration" ? "seconds / call" : series === "bookings" ? "bookings saved" : "completed calls"}</span>
              </div>
              <div className="overview-series" role="group" aria-label="Activity series">
                <SelectionIndicator activeKey={series} />
                {SERIES.map((item) => <button key={item.id} type="button" className="sliding-tab" aria-pressed={series === item.id} onClick={() => setSeries(item.id)}>{item.label}</button>)}
              </div>
              <div className="overview-plot" aria-label={totalDescription} role={chartPending ? "status" : "img"}>
                {chartPending ? <div className="overview-plot-skeleton" aria-hidden="true"><div className="overview-plot-grid">{[0, 1, 2, 3].map((row) => <span key={row}><i className="loading-skeleton" /></span>)}</div><div className="overview-plot-ticks">{[0, 1, 2, 3].map((tick) => <span className="loading-skeleton" key={tick} />)}</div></div> : chartReady ? (
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={stats.buckets} margin={{ top: 18, right: 12, bottom: 0, left: -20 }} accessibilityLayer={false}>
                      <CartesianGrid stroke="var(--line-1)" vertical={false} />
                      <XAxis dataKey="time" tickFormatter={(value: number) => stats.step === 3600 ? wallClock(value) : `${dayLabel(value)}${stats.step === 21600 ? ` ${wallClock(value)}` : ""}`} tick={{ fill: "var(--fg-2)", fontSize: 11 }} axisLine={false} tickLine={false} minTickGap={52} />
                      <YAxis tick={{ fill: "var(--fg-2)", fontSize: 11 }} axisLine={false} tickLine={false} allowDecimals={false} />
                      <Tooltip
                        cursor={{ stroke: "var(--fg-3)", strokeWidth: 1 }}
                        content={({ active, payload, label }) => {
                          if (!active || !payload?.length) return null;
                          const value = payload[0]?.value;
                          const bucket = stats.buckets.find((item) => item.time === Number(label));
                          return <div className="overview-tooltip"><p>{dayLabel(Number(label))} {wallClock(Number(label))}</p><strong>{value == null ? "Not available" : series === "duration" ? duration(Number(value)) : `${Number(value).toLocaleString("en-GB")} ${series === "calls" ? "calls" : "bookings"}`}</strong>{series === "bookings" ? <span>{bucket?.loaded ?? 0} of {bucket?.calls ?? 0} call details loaded</span> : null}</div>;
                        }}
                      />
                      <Area type="linear" dataKey={series} stroke="var(--accent-ink)" strokeWidth={2.5} fill="var(--accent-ink)" fillOpacity={0.1} dot={false} activeDot={false} connectNulls={false} isAnimationActive={false} />
                    </AreaChart>
                  </ResponsiveContainer>
                ) : <div className="overview-empty"><h3>{!available ? "Call records unavailable" : finishedCount === 0 ? "No completed calls in this range" : "No measurements available yet"}</h3><p>{!available ? "Use Try again to reload your call records." : finishedCount === 0 ? "Choose a wider range or check calls still in progress." : failedDetails && series === "bookings" ? "Retry the failed details to load bookings." : "Only recorded measurements appear here."}</p></div>}
              </div>
            </section>

            <section className="overview-outcomes" aria-labelledby="outcomes-title">
              <div className="overview-section-heading"><h2 id="outcomes-title">Outcomes</h2></div>
              {!available && !error ? <div className="overview-outcome-list" role="status"><span className="sr-only">Loading outcomes</span>{[0, 1, 2].map((row) => <div className="overview-outcome overview-outcome-skeleton" key={row} aria-hidden="true"><div><span className="loading-skeleton" /><span className="loading-skeleton" /></div><div className="overview-outcome-track" /></div>)}</div> : stats.outcomes.length ? <div className="overview-outcome-list loading-reveal">{stats.outcomes.map((outcome) => (
                <div className="overview-outcome" key={outcome.key}>
                  <div><span>{outcome.label}</span><span><strong>{outcome.count}</strong><small>{Math.round(outcome.count / finishedCount * 100)}%</small></span></div>
                  <div className="overview-outcome-track" aria-hidden="true"><span className={outcome.key === "BOOK" ? "overview-outcome-booked" : undefined} style={{ transform: `scaleX(${outcome.count / finishedCount})` }} /></div>
                </div>
              ))}</div> : <p className="overview-outcome-empty">{available ? "No completed-call outcomes in this range." : "Call outcomes could not be loaded."}</p>}
            </section>
          </div>

          <section className="overview-recent" aria-labelledby="recent-title">
            <div className="overview-section-heading"><h2 id="recent-title">Recent conversations</h2><Link className="overview-text-link" to="/calls">All calls <ArrowUpRightIcon size={16} aria-hidden="true" /></Link></div>
            {!available && !error ? <div className="overview-call-list" role="status"><span className="sr-only">Loading recent conversations</span>{[0, 1, 2, 3].map((row) => <div className="overview-call overview-call-skeleton" key={row} aria-hidden="true"><span className="overview-call-person"><strong className="loading-skeleton" /><span className="loading-skeleton" /></span><span className="overview-call-outcome loading-skeleton" /><span className="overview-call-duration loading-skeleton" /><ArrowUpRightIcon size={17} /></div>)}</div> : stats.finished.length ? <div className="overview-call-list loading-reveal">{stats.finished.slice(0, 4).map((call) => {
              const record = currentDetail(call, byId);
              const name = record?.timeline?.identified?.name;
              return <Link className="overview-call" key={call.call_id} to={`/calls/${encodeURIComponent(call.call_id)}`}>
                <span className="overview-call-person"><strong>{name || (record ? "Unidentified caller" : byId[call.call_id]?.detailError ? "Caller details unavailable" : "Loading caller details")}</strong><span>{dayLabel(call.started_at)} at {wallClock(call.started_at)}</span></span>
                <span className="overview-call-outcome">{outcomeLabel(call)}</span>
                <span className="overview-call-duration">{call.duration_seconds == null ? "Not recorded" : duration(call.duration_seconds)}</span>
                <ArrowUpRightIcon size={17} aria-hidden="true" />
              </Link>;
            })}</div> : <p className="overview-outcome-empty">{available ? "Completed conversations will appear here." : "Recent conversations could not be loaded."}</p>}
          </section>

        </div>
      </div>
    </div>
  );
}

function Stat({ label, value, pending = false, unit, decimals = 0, accent = false }: { label: string; value: number | null; pending?: boolean; unit?: string; decimals?: number; accent?: boolean }) {
  return <div className={`overview-stat${accent ? " overview-stat-accent" : ""}`}><h3>{label}</h3><div className="overview-stat-value">{pending ? <span role="status"><span className="overview-stat-skeleton loading-skeleton" aria-hidden="true" /><span className="sr-only">Loading {label.toLowerCase()}</span></span> : value == null ? <span className="overview-unavailable">Not available</span> : <><NumberFlow value={value} locales="en-GB" format={{ maximumFractionDigits: decimals, minimumFractionDigits: decimals }} transformTiming={NUMBER_TIMING} spinTiming={NUMBER_TIMING} opacityTiming={NUMBER_TIMING} />{unit ? <span className="overview-stat-unit">{unit}</span> : null}</>}</div></div>;
}
