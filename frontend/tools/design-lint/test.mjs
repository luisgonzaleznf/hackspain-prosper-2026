// Fixture test for the design linter: bad fixtures must fail, good ones must pass.
// Run: pnpm test:design-lint
import { execFileSync } from "node:child_process";

const bin = (name) => new URL(`../../node_modules/.bin/${name}`, import.meta.url).pathname;
const run = (file, args) => {
  try {
    return execFileSync(file, args, { encoding: "utf8", stdio: ["ignore", "pipe", "pipe"] });
  } catch (err) {
    return `${err.stdout ?? ""}${err.stderr ?? ""}`;
  }
};

const ox = run(bin("oxlint"), ["-c", "oxlint.config.ts", "--format", "json", "tools/design-lint/fixtures"]);
const oxDiag = JSON.parse(ox).diagnostics.filter((d) => d.code.startsWith("design("));
const oxByFile = Object.groupBy(oxDiag, (d) => d.filename.split("/").pop());

const st = run(bin("stylelint"), ["tools/design-lint/fixtures/*.css", "--formatter", "json"]);
const stByFile = Object.fromEntries(JSON.parse(st).map((r) => [r.source.split("/").pop(), r.warnings]));

const expect = [
  ["bad.tsx", (oxByFile["bad.tsx"] ?? []).length >= 8, "oxlint flags bad.tsx"],
  ["good.tsx", (oxByFile["good.tsx"] ?? []).length === 0, "oxlint passes good.tsx"],
  ["bad.css", (stByFile["bad.css"] ?? []).length >= 7, "stylelint flags bad.css"],
  ["bad.css", (stByFile["bad.css"] ?? []).some((warning) => warning.rule === "declaration-property-value-disallowed-list" && warning.text.includes("animation")), "stylelint still rejects decorative animation loops"],
  ["good.css", (stByFile["good.css"] ?? []).length === 0, "stylelint passes good.css"],
  ["tokens.css", (stByFile["tokens.css"] ?? []).length === 0, "stylelint allows raw values in tokens.css"],
];

let failed = 0;
for (const [, ok, label] of expect) {
  console.log(`${ok ? "ok  " : "FAIL"} ${label}`);
  if (!ok) failed++;
}
if (failed) {
  console.log("\noxlint design diagnostics:", JSON.stringify(oxByFile, null, 1));
  console.log("\nstylelint warnings:", JSON.stringify(stByFile, null, 1));
  process.exit(1);
}
