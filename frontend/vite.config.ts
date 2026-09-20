import { cpSync } from "node:fs";
import { fileURLToPath, URL } from "node:url";
import type { Plugin } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import { defineConfig } from "vite";
import { recordings } from "./tools/recordings-server.ts";

// One public origin fronts the compiled UI, WebRTC runner, Twilio media, and clinic APIs.
const api = process.env.ROSARIO_API ?? "http://127.0.0.1:7860";
const proxy = {
  "/api": { target: api, changeOrigin: true },
  "/start": { target: api, changeOrigin: true },
  "/sessions": { target: api, changeOrigin: true },
  "/ws": { target: api, changeOrigin: true, ws: true },
  "/twiml": { target: api, changeOrigin: true },
  "/health": { target: api, changeOrigin: true },
};

// Two pages share one origin: the brand landing page is `index.html` at `/`,
// the console SPA is `console.html` and owns these route prefixes (see
// src/main.tsx). Requests for those paths are rewritten to the console shell in
// dev and preview; any other host needs the same rewrite. The landing page is
// static HTML: it and /brand/identity.html read brand/, tokens/ and fonts/
// directly (classic scripts, runtime-fetched SVGs), so only the console is
// bundled and those files are copied into dist as they are.
const CONSOLE_ROUTES = /^\/(dashboard|calls|calendar|cases|metrics|talk)(\/|\?|$)/;
// The roleplay studio is its own bundled page at /demo; everything else under
// /demo/ (the review page, its script and the stylesheet) is served statically.
const DEMO_ROUTE = /^\/demo\/?(\?|$)/;
const STATIC_PATHS = ["index.html", "brand", "demo", "tokens", "fonts", "licenses"];
const root = fileURLToPath(new URL(".", import.meta.url));
function landingAndConsole(): Plugin {
  const rewrite = (server: { middlewares: { use: (fn: (req: { url?: string }, res: unknown, next: () => void) => void) => void } }) => {
    server.middlewares.use((req, _res, next) => {
      if (req.url && DEMO_ROUTE.test(req.url)) req.url = "/demo.html";
      else if (req.url && CONSOLE_ROUTES.test(req.url)) req.url = "/console.html";
      next();
    });
  };
  return {
    name: "rosario-landing-and-console",
    configureServer: rewrite,
    configurePreviewServer: rewrite,
    closeBundle() {
      for (const path of STATIC_PATHS) cpSync(`${root}${path}`, `${root}dist/${path}`, { recursive: true });
    },
  };
}

export default defineConfig({
  plugins: [react(), tailwindcss(), recordings(root), landingAndConsole()],
  build: { rollupOptions: { input: { console: "console.html", demo: "demo.html" } } },
  publicDir: "public",
  resolve: {
    alias: { "@": fileURLToPath(new URL("./src", import.meta.url)) },
  },
  server: {
    fs: {
      allow: [fileURLToPath(new URL(".", import.meta.url))],
      deny: [".env", ".env.*", "*.{crt,pem}", "**/.git/**", "**/.recordings/**"],
    },
    proxy,
  },
  preview: {
    proxy,
  },
});
