import { defineConfig } from "oxlint";

// Design-rule linting for TS/TSX. Code-quality rules (correctness, anti-slop)
// get added when the app scaffold lands; this file is the design contract.
export default defineConfig({
  ignorePatterns: ["node_modules/**", "dist/**", "research/**", "brand/logos/**", "tools/design-lint/index.js", "brand/vendor/**"],
  jsPlugins: [{ name: "design", specifier: "./tools/design-lint/index.js" }],
  rules: {
    "design/no-raw-color": "error",
    "design/no-infinite-motion": "error",
    "design/no-decorative-chrome": "error",
    "design/no-raw-font": "error",
    "design/no-em-dash": "error",
    "design/no-inline-style-tokens": "error",
  },
  overrides: [
    {
      // The token file is the one place raw values are allowed to live.
      files: ["src/styles/tokens.ts", "tokens/**"],
      rules: { "design/no-raw-color": "off", "design/no-raw-font": "off" },
    },
  ],
});
