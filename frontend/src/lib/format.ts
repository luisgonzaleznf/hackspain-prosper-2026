// Copy rules from CONSOLE.md section 8: Europe/Madrid, 24h, `HH:MM` wall clock,
// `+ss.s` offsets, `1m 42s` durations, `312 ms` latencies.

const MADRID = "Europe/Madrid";

const clock = new Intl.DateTimeFormat("en-GB", { timeZone: MADRID, hour: "2-digit", minute: "2-digit", hour12: false });
const clockSeconds = new Intl.DateTimeFormat("en-GB", { timeZone: MADRID, hour: "2-digit", minute: "2-digit", second: "2-digit", hour12: false });
const dayMonth = new Intl.DateTimeFormat("en-GB", { timeZone: MADRID, day: "numeric", month: "short" });
const weekdayLong = new Intl.DateTimeFormat("en-GB", { timeZone: MADRID, weekday: "long", day: "numeric", month: "long" });

export function wallClock(epochSeconds: number): string {
  return clock.format(new Date(epochSeconds * 1000));
}

export function wallClockSeconds(epochSeconds: number): string {
  return clockSeconds.format(new Date(epochSeconds * 1000));
}

export function dayLabel(epochSeconds: number): string {
  return dayMonth.format(new Date(epochSeconds * 1000));
}

export function duration(seconds: number | null | undefined): string {
  if (seconds == null || !Number.isFinite(seconds)) return "\u2013";
  const total = Math.max(0, Math.round(seconds));
  const m = Math.floor(total / 60);
  const s = total % 60;
  if (m >= 60) {
    const h = Math.floor(m / 60);
    return `${h}h ${String(m % 60).padStart(2, "0")}m`;
  }
  return m > 0 ? `${m}m ${String(s).padStart(2, "0")}s` : `${s}s`;
}

/** mm:ss for the player clock. */
export function playerClock(seconds: number): string {
  const total = Math.max(0, Math.floor(seconds));
  return `${Math.floor(total / 60)}:${String(total % 60).padStart(2, "0")}`;
}

export function offset(seconds: number): string {
  return `+${seconds.toFixed(1)}s`;
}

export function latency(ms: number | null | undefined): string {
  if (ms == null || !Number.isFinite(ms)) return "\u2013";
  return ms >= 10_000 ? `${(ms / 1000).toFixed(1)} s` : `${Math.round(ms)} ms`;
}

/** +34 612 ··· 678: keep country code and the first three and last three digits. */
export function maskPhone(e164: string | null | undefined): string {
  if (!e164) return "withheld";
  const digits = e164.replace(/\D/g, "");
  if (digits.length < 9) return e164;
  const national = digits.startsWith("34") && digits.length > 9 ? digits.slice(2) : digits;
  const prefix = digits.length > national.length ? `+${digits.slice(0, digits.length - national.length)} ` : "";
  return `${prefix}${national.slice(0, 3)} \u00b7\u00b7\u00b7 ${national.slice(-3)}`;
}

export function maskNationalId(id: string | null | undefined): string {
  if (!id) return "\u2013";
  const clean = id.replace(/[\s.-]/g, "");
  if (clean.length < 5) return clean;
  return `${clean.slice(0, 2)}\u00b7\u00b7\u00b7\u00b7${clean.slice(-2)}`;
}

/** "2026-09-21T09:00:00+02:00" to "Monday 21 September, 09:00" in Madrid time. */
export function slotLabel(iso: string | null | undefined): string {
  if (!iso) return "\u2013";
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return iso;
  return `${weekdayLong.format(date)}, ${clock.format(date)}`;
}

export function shortId(id: string, head = 8): string {
  return id.length > head + 1 ? id.slice(0, head) : id;
}

export function percent(numerator: number, denominator: number): string {
  if (denominator === 0) return "\u2013";
  return `${Math.round((numerator / denominator) * 100)}%`;
}

export function euros(value: number): string {
  return new Intl.NumberFormat("es-ES", { style: "currency", currency: "EUR", maximumFractionDigits: 2 }).format(value);
}
