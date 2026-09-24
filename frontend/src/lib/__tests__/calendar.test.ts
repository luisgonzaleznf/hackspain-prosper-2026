// The clinic diary feed: tolerant parsing, month windows, filters and day facts. Run with `pnpm test`.
import assert from "node:assert/strict";
import { test } from "node:test";
import {
  absencesOn, appointmentTypeLabel, closuresOn, filterRecords, groupByProvider, monthGrid, monthWindow, parseCalendarFeed, shiftDay, summarizeDays,
} from "../calendar.ts";

const feed = {
  from: "2026-09-28",
  to: "2026-11-08",
  providers: [
    { id: "PR05", name: "Dra. Elena Iglesias", specialtyId: "dermatology", specialtyName: "Dermatology" },
    { id: "PR01", name: "Dra. Carmen Ortiz Vidal", specialtyId: "general_practice", specialtyName: "General Practice" },
  ],
  locations: [{ id: "centro", name: "Arenal Centro" }, { id: "sur", name: "Arenal Sur" }],
  absences: [
    { providerId: "PR05", start: "2026-10-05", end: "2026-10-07", startTime: null, endTime: null, reason: "congress (EADV Vienna)" },
    { providerId: "PR01", start: "2026-10-06", end: "2026-10-06", startTime: "12:00", endTime: "14:00", reason: "personal" },
    { providerId: "", start: "2026-10-06", end: "2026-10-06", reason: "no provider" },
  ],
  closures: [
    { date: "2026-10-12", locationId: null, name: "Fiesta Nacional de España" },
    { date: "2026-10-06", locationId: "sur", name: "Local holiday" },
  ],
  records: [
    {
      id: "A100002", appointmentId: "A100002", callId: null, kind: "BOOK", recordedAt: null, slot: "2026-10-06T10:00:00+02:00", previousSlot: null,
      day: "2026-10-06", patient: "Lucas Romero", patientId: "P00003", caller: null, provider: "Dra. Carmen Ortiz Vidal", site: "Arenal Centro",
      supersededBy: null, practice: false, persisted: true, providerId: "PR01", specialtyId: "general_practice", durationMinutes: 15,
      end: "2026-10-06T10:15:00+02:00", appointmentType: "review", status: "booked", source: "diary",
    },
    {
      id: "LA1", appointmentId: "LA1", callId: "call-7", kind: "BOOK", recordedAt: 1790000000, slot: "2026-10-06T09:15:00+02:00",
      patient: "Josefa Navarro", patientId: "P00001", provider: "Dra. Elena Iglesias", site: "Arenal Sur", providerId: "PR05",
      durationMinutes: 15, appointmentType: "dermatology_review", status: "booked", source: "call",
    },
    {
      id: "A100003", appointmentId: "A100003", callId: null, kind: "CANCEL", slot: "2026-10-06T09:15:00+02:00", day: "2026-10-06",
      patient: "Ana Gil", provider: "Dra. Carmen Ortiz Vidal", site: "Arenal Centro", providerId: "PR01", status: "cancelled", source: "diary",
    },
    // A seeded row cancelled by Rosario keeps its call link.
    {
      id: "A100004", callId: "call-8", slot: "2026-10-07T11:00:00+02:00", patient: "Rosa Gil", provider: "Dra. Elena Iglesias",
      site: "Arenal Sur", status: "cancelled",
    },
    { id: "bad-slot", slot: "2026-10-06T09:00:00", patient: "No offset" },
    { patient: "No id at all" },
    "not an object",
  ],
};

test("the calendar feed parses every row it can and never trusts a slot without an offset", () => {
  const parsed = parseCalendarFeed(feed);
  assert.equal(parsed.from, "2026-09-28");
  assert.equal(parsed.to, "2026-11-08");
  assert.deepEqual(parsed.providers.map((provider) => provider.id), ["PR01", "PR05"], "doctors sorted by name");
  assert.deepEqual(parsed.records.map((record) => record.id), ["bad-slot", "A100003", "LA1", "A100002", "A100004"]);

  const call = parsed.records.find((record) => record.id === "LA1")!;
  assert.equal(call.source, "call");
  assert.equal(call.day, "2026-10-06", "day derived from the Madrid slot when missing");
  assert.equal(call.locationId, "sur", "site id recovered from the site name");
  assert.equal(call.endMs, Date.parse("2026-10-06T09:30:00+02:00"), "end derived from the duration");
  assert.equal(call.callLogged, true);

  const cancelled = parsed.records.find((record) => record.id === "A100003")!;
  assert.equal(cancelled.status, "cancelled");
  assert.equal(cancelled.kind, "CANCEL");
  assert.equal(cancelled.source, "diary");

  const cancelledByCall = parsed.records.find((record) => record.id === "A100004")!;
  assert.equal(cancelledByCall.source, "call", "a call id without an explicit source still marks the row");
  assert.equal(cancelledByCall.providerId, "PR05", "doctor id recovered from the name");

  const bad = parsed.records.find((record) => record.id === "bad-slot")!;
  assert.equal(bad.slot, null);
  assert.equal(bad.day, null);

  assert.equal(parsed.absences.length, 2, "an absence without a doctor is dropped");
  assert.deepEqual(parsed.closures.map((closure) => closure.locationId), [null, "sur"]);
});

test("a missing or empty body is an empty diary, not an error", () => {
  for (const body of [null, undefined, "", [], {}, { records: "nope" }]) {
    const parsed = parseCalendarFeed(body);
    assert.deepEqual(parsed.records, []);
    assert.deepEqual(parsed.providers, []);
  }
  // An older server without directory lists: doctors and sites come from the rows.
  const legacy = parseCalendarFeed({ records: [{ id: "x", slot: "2026-10-06T09:00:00+02:00", patient: "A", provider: "Dr. B", providerId: "PR02", site: "Arenal Norte" }] });
  assert.deepEqual(legacy.providers.map((provider) => provider.id), ["PR02"]);
  assert.deepEqual(legacy.locations, [{ id: "Arenal Norte", name: "Arenal Norte" }]);
  assert.equal(legacy.records[0]?.locationId, "Arenal Norte");
});

test("month windows cover the whole grid and never exceed the server's 62 days", () => {
  assert.deepEqual(monthWindow("2026-10"), { from: "2026-09-28", to: "2026-11-01" });
  assert.equal(monthGrid("2026-10").length, 35);
  assert.equal(monthGrid("2026-11").length, 42);
  assert.deepEqual(monthWindow("2026-11"), { from: "2026-10-26", to: "2026-12-06" });
  assert.equal(shiftDay("2026-10-31", 1), "2026-11-01");
  assert.equal(shiftDay("2026-10-25", -1), "2026-10-24", "DST change day is still one calendar day");
});

test("doctor, site and Rosario filters narrow the diary; day facts follow them", () => {
  const parsed = parseCalendarFeed(feed);
  const all = { providerId: "", locationId: "", rosarioOnly: false };
  assert.equal(filterRecords(parsed.records, all).length, 5);
  assert.deepEqual(filterRecords(parsed.records, { ...all, providerId: "PR05" }).map((record) => record.id), ["LA1", "A100004"]);
  assert.deepEqual(filterRecords(parsed.records, { ...all, locationId: "centro" }).map((record) => record.id), ["A100003", "A100002"]);
  assert.deepEqual(filterRecords(parsed.records, { ...all, rosarioOnly: true }).map((record) => record.id), ["LA1", "A100004"]);

  assert.deepEqual(absencesOn(parsed.absences, "2026-10-06").map((absence) => absence.providerId), ["PR05", "PR01"]);
  assert.deepEqual(absencesOn(parsed.absences, "2026-10-06", "PR01").map((absence) => absence.reason), ["personal"]);
  assert.equal(absencesOn(parsed.absences, "2026-10-08").length, 0, "the end date is inclusive and nothing after it");
  assert.equal(closuresOn(parsed.closures, "2026-10-06").length, 1);
  assert.equal(closuresOn(parsed.closures, "2026-10-06", "centro").length, 0, "another site's holiday does not close Centro");
  assert.equal(closuresOn(parsed.closures, "2026-10-12", "centro").length, 1, "a national holiday closes every site");
});

test("day summaries count bookings, cancellations and Rosario bookings separately", () => {
  const parsed = parseCalendarFeed(feed);
  const days = summarizeDays(parsed.records);
  assert.equal(days["2026-10-06"]?.booked, 2);
  assert.equal(days["2026-10-06"]?.cancelled, 1);
  assert.deepEqual(days["2026-10-06"]?.rosario.map((record) => record.id), ["LA1"]);
  assert.equal(days["2026-10-07"]?.booked, 0);
  assert.deepEqual(days["2026-10-07"]?.rosario, [], "a cancelled call row is not a Rosario booking");

  const groups = groupByProvider(parsed.records.filter((record) => record.day === "2026-10-06"), parsed.providers);
  assert.deepEqual(groups.map((group) => [group.name, group.records.map((record) => record.id)]), [
    ["Dra. Carmen Ortiz Vidal", ["A100003", "A100002"]],
    ["Dra. Elena Iglesias", ["LA1"]],
  ]);
  assert.equal(groups[1]?.specialty, "Dermatology");
  assert.equal(appointmentTypeLabel("dermatology_review"), "Dermatology review");
  assert.equal(appointmentTypeLabel("Dermatology Review"), "Dermatology Review");
  assert.equal(appointmentTypeLabel(null), null);
});
