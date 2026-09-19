import { createReadStream } from "node:fs";
import { readFile, stat } from "node:fs/promises";
import type { IncomingMessage, ServerResponse } from "node:http";
import { join } from "node:path";
import type { Connect, Plugin } from "vite";
import type { CallsIndex } from "../src/lib/types.ts";

interface Manifest {
  revision: string;
  audio_files: Record<string, string>;
}

interface Dataset {
  directory: string;
  manifest: Manifest;
  index: Buffer;
  callIds: Set<string>;
}

const IMPORT_HELP = "Run pnpm recordings:import in frontend after signing in with gh auth login.";
const CALL_ID = /^[A-Za-z0-9_-]+$/;

function json(res: ServerResponse, status: number, value: unknown, head = false) {
  const body = Buffer.from(JSON.stringify(value));
  res.writeHead(status, { "Content-Type": "application/json; charset=utf-8", "Content-Length": body.length, "Cache-Control": "no-store" });
  res.end(head ? undefined : body);
}

function byteRange(header: string, size: number): { start: number; end: number } | null {
  const match = /^bytes=(\d*)-(\d*)$/.exec(header);
  if (!match || (!match[1] && !match[2])) return null;
  if (!match[1]) {
    const suffix = Number(match[2]);
    return Number.isSafeInteger(suffix) && suffix > 0 && size > 0 ? { start: Math.max(0, size - suffix), end: size - 1 } : null;
  }
  const start = Number(match[1]);
  const end = match[2] ? Number(match[2]) : size - 1;
  if (!Number.isSafeInteger(start) || !Number.isSafeInteger(end) || start >= size || end < start) return null;
  return { start, end: Math.min(end, size - 1) };
}

async function audio(req: IncomingMessage, res: ServerResponse, path: string) {
  const { size } = await stat(path);
  if (size === 0) {
    json(res, 404, { detail: "This call has no playable recording." }, req.method === "HEAD");
    return;
  }
  const headers = { "Content-Type": "audio/ogg; codecs=opus", "Accept-Ranges": "bytes", "Cache-Control": "private, no-cache", "X-Content-Type-Options": "nosniff" };
  // Range only applies to GET. HEAD describes the complete representation.
  const range = req.method === "GET" && req.headers.range ? byteRange(req.headers.range, size) : undefined;
  if (range === null) {
    res.writeHead(416, { ...headers, "Content-Range": `bytes */${size}`, "Content-Length": 0 });
    res.end();
    return;
  }
  res.writeHead(range ? 206 : 200, {
    ...headers,
    "Content-Length": range ? range.end - range.start + 1 : size,
    ...(range ? { "Content-Range": `bytes ${range.start}-${range.end}/${size}` } : {}),
  });
  if (req.method === "HEAD") {
    res.end();
    return;
  }
  const stream = createReadStream(path, range);
  stream.on("error", () => res.destroy());
  res.on("close", () => stream.destroy());
  stream.pipe(res);
}

export function recordings(root: string): Plugin {
  const dataRoot = join(root, ".recordings");
  let loaded: Dataset | undefined;

  async function dataset(): Promise<Dataset> {
    const pointer: { revision?: string } = JSON.parse(await readFile(join(dataRoot, "current.json"), "utf8"));
    if (!pointer.revision || !/^[0-9a-f]{40}$/.test(pointer.revision)) throw new Error("Invalid recording revision");
    if (loaded?.manifest.revision === pointer.revision) return loaded;
    const directory = join(dataRoot, pointer.revision);
    const [manifestText, index] = await Promise.all([
      readFile(join(directory, "manifest.json"), "utf8"),
      readFile(join(directory, "index.json")),
    ]);
    const manifest: Manifest = JSON.parse(manifestText);
    const calls: CallsIndex = JSON.parse(index.toString());
    if (manifest.revision !== pointer.revision || !manifest.audio_files || !Array.isArray(calls.calls)) throw new Error("Incomplete recording dataset");
    loaded = { directory, manifest, index, callIds: new Set(calls.calls.map((call) => call.call_id)) };
    return loaded;
  }

  const middleware: Connect.NextHandleFunction = (req, res, next) => {
    const pathname = (req.url ?? "/").split("?", 1)[0] ?? "/";
    if (pathname !== "/api/calls" && !pathname.startsWith("/api/calls/")) {
      next();
      return;
    }
    const head = req.method === "HEAD";
    if (req.method !== "GET" && !head) {
      res.setHeader("Allow", "GET, HEAD");
      json(res, 405, { detail: "This recording API is read-only. Use GET or HEAD." });
      return;
    }
    const match = /^\/api\/calls(?:\/([^/]+)(\/audio)?)?\/?$/.exec(pathname);
    if (!match) {
      json(res, 404, { detail: "Recording endpoint not found." }, head);
      return;
    }
    let id: string | undefined;
    try {
      id = match[1] ? decodeURIComponent(match[1]) : undefined;
    } catch {
      json(res, 400, { detail: "The call ID is not a valid URL component." }, head);
      return;
    }
    if (id && !CALL_ID.test(id)) {
      json(res, 400, { detail: "The call ID contains unsupported characters." }, head);
      return;
    }
    void (async () => {
      let current: Dataset;
      try {
        current = await dataset();
      } catch {
        json(res, 503, { detail: `The local recording dataset is unavailable. ${IMPORT_HELP}` }, head);
        return;
      }
      try {
        if (!id) {
          res.writeHead(200, { "Content-Type": "application/json; charset=utf-8", "Content-Length": current.index.length, "Cache-Control": "no-store" });
          res.end(head ? undefined : current.index);
          return;
        }
        if (!current.callIds.has(id)) {
          json(res, 404, { detail: "This call is not in the imported dataset." }, head);
          return;
        }
        if (match[2]) {
          const relative = current.manifest.audio_files[id];
          if (!relative) {
            json(res, 404, { detail: "This call has no playable recording. Its call log is still available." }, head);
            return;
          }
          await audio(req, res, join(current.directory, relative));
          return;
        }
        const body = await readFile(join(current.directory, "calls", `${id}.json`));
        res.writeHead(200, { "Content-Type": "application/json; charset=utf-8", "Content-Length": body.length, "Cache-Control": "no-store" });
        res.end(head ? undefined : body);
      } catch {
        if (res.headersSent) res.destroy();
        else json(res, 503, { detail: `A file is missing from the local recording dataset. Re-import the pinned revision to restore it. ${IMPORT_HELP}` }, head);
      }
    })();
  };

  return {
    name: "rosario-recordings",
    configureServer(server) { server.middlewares.use(middleware); },
    configurePreviewServer(server) { server.middlewares.use(middleware); },
  };
}
