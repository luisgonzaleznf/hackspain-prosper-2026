# QuiverAI (quiver.ai) research: SVG logo generation API

Researched 2026-09-18. Target use: generating logo variants for the brand ROSARIO with Quiver's newest model. All API facts below marked "verified" were confirmed against the live API with the project key in `.env` (`QUIVER_API_KEY`, a `sk_live_` production key). Screenshots live in `frontend/research/screens/quiver/`.

## 1. Product overview

QuiverAI ("Frontier AI for Design") is a research lab and product company that trains models for vector graphics. Their paradigm is "visual code generation": the model writes SVG markup rather than pixels. Founded by the authors of StarVector and RLRF; $8.3M seed led by a16z (Feb 2026).

What it generates:

- **SVG only.** Every model in the catalog has `output_modalities: ["svg"]`. Outputs are true vectors: XML `<svg>` markup with `<path>`, `<rect>`, gradients in `<defs>`, grouped `<g>` layers with readable ids. No raster output from the API. The App (app.quiver.ai) can export PNG, JPEG, WebP, and MP4 from a generated SVG, but the API returns SVG strings only; rasterize locally if needed.
- Use cases marketed: logos, icons, illustrations, diagrams, technical line work. Typography (custom letterforms) and animation are marked "coming soon" on the landing page, though the API already exposes `POST /v1/svgs/animations` on Arrow 2 models.
- Operations: text to SVG (`svg_generate`), image to SVG vectorization (`svg_vectorize`), SVG edit with natural language (`svg_edit`), SVG animation (`svg_animate`), and an OpenResponses-compatible agent endpoint (`open_responses`).
- Inputs: text prompt, optional `instructions`, optional reference images (URL or base64: PNG, JPEG, WebP, GIF, SVG; max 12,582,912 bytes decoded, 4096x4096, 16,777,216 total pixels).
- No brand kits, no font files, no color palette objects. It is a single-asset generator. "Brand kit" behavior has to be built on top by looping prompts (see section 6).
- Known weakness (from third-party reviews, DesignCourse Feb 2026): text rendering inside logos is unreliable; treat wordmarks as risky and prefer pictorial marks and monograms, or set type yourself.
- Generated SVGs carry the comment `<!-- SVG created with Arrow, by QuiverAI (https://quiver.ai) -->` (observed in test output).

Surfaces: web App (app.quiver.ai, subscription), API Platform (platform.quiver.ai, prepaid balance, separate from App credits), hosted MCP server (`https://app.quiver.ai/mcp`, App billing, Arrow 1.x only, no Arrow 2), Cursor and Codex plugins, `npx quiverai add <creation>` CLI that installs SVGs as React components.

## 2. Models

Model catalog as returned by `GET /v1/models` with the project key on 2026-09-18 (verified). Arrow 2 and Arrow 2 Telos were announced 2026-09-07 and are the current generation.

| Model id | Name | Positioning (catalog `description`) | Billing | Price | Context / max output | Operations | Sampling params |
|---|---|---|---|---|---|---|---|
| **`arrow-2-telos`** (LATEST, most capable) | Arrow 2 Telos | "Our most capable model that combines Arrow intelligence with frontier model capabilities." | token_usage | $6.00 in / $0.60 cached in / $7.50 cache write / $30.00 out, per 1M tokens | 1,050,000 / 65,536 | open_responses, svg_animate, svg_edit, svg_generate, svg_vectorize | none advertised |
| `arrow-2` (latest, default) | Arrow 2 | "Flagship model that balances high quality and speed." | token_usage | $4.00 in / $0.40 cached / $5.00 cache write / $20.00 out, per 1M tokens | 131,072 / 65,536 | open_responses, svg_animate, svg_edit, svg_generate, svg_vectorize | none advertised |
| `arrow-1.1-max` | Arrow 1.1 Max | "Best for detailed diagrams and illustrations." | fixed_credit | 25 credits ($0.25) per SVG; 20 ($0.20) per vectorize | 131,072 / 65,536 | svg_generate, svg_vectorize | temperature, top_p, presence_penalty |
| `arrow-1.1` | Arrow 1.1 | "Best default for speed and quality, with strong prompt following and precise SVG." | fixed_credit | 20 credits ($0.20) per SVG; 15 ($0.15) per vectorize | 131,072 / 65,536 | svg_generate, svg_vectorize | temperature, top_p, presence_penalty |
| `arrow-1` | Arrow 1.0 | "First-gen vector-native model for editable logos, icons, and illustrations." | fixed_credit | 30 credits ($0.30) per SVG or vectorize | 65,536 / 32,768 | svg_generate, svg_vectorize | temperature, top_p, presence_penalty |

Which to use for ROSARIO:

- Docs (Text to SVG page): "Use `arrow-2` for most text-to-SVG generation. It balances quality and speed while keeping outputs clean and editable. Use `arrow-2-telos` when output quality is the priority. It is better suited to dense illustrations, logos with tight geometry, technical diagrams, and other compositions where precision matters more than speed."
- Blog: "Choose Arrow 2 when speed and cost per asset are the priority. Choose Telos for harder briefs that benefit from additional refinement."
- Telos is 1.5x the token rate of Arrow 2 in every category. The test call (one 1024x1024 rose mark) used 476 input + 7,140 output tokens on Telos = $0.217 and took 83 seconds. The same on Arrow 2 would be about $0.145 and, per the blog, faster (not measured).
- Practical rule: iterate prompts on `arrow-2`, then rerun the winners on `arrow-2-telos`.

Arrow 2 vs Arrow 1.x differences (blog + catalog): faster generation; "cleaner geometry: SVGs use fewer, more precise control points, reducing unnecessary nodes and messy, overlapping paths"; "stronger composition: elements naturally respect spacing, padding, and alignment without exhaustive prompt engineering"; adds edit and animation operations and the Responses API; billed by tokens instead of fixed credits; no `temperature`/`top_p`/`presence_penalty` advertised (catalog `supported_sampling_parameters` is empty); adds `reasoning_effort` (`low`, `medium`, `high`, `xhigh`).

Limits: no prompt length limit is published for `/v1/svgs/generations` (`prompt` is `minLength: 1` only). `/v1/svgs/edits` caps `prompt` at 4000 chars and inline `svg` at 200,000 chars. `n` is 1 to 16. `max_output_tokens` is 1 to 65,536. Reference images: 16 in schema, runtime "4 for Arrow 1.1/Arrow 1.x aliases, 16 for Arrow 1.1 Max" (Arrow 2 runtime limit not documented). Output size is set with `attributes.viewBox`; the model chose `width="1024" height="1024" viewBox="0 0 1024 1024"` when unset.

Key authority: "The key must also authorize the requested model and operation; appearing in the catalog does not grant access." Keys are created per environment (`sk_live_` production, `sk_test_` sandbox) with explicit allowed operations and models. This project's key is verified to allow `catalog_read` and `svg_generate` on `arrow-2-telos`.

## 3. API reference (verified against the live API and the OpenAPI spec)

- Base URL: `https://api.quiver.ai/v1`. OpenAPI 3.1 spec: `https://api.quiver.ai/v1/openapi.json` (458 KB; `https://api.quiver.ai/` 302-redirects to it).
- Auth: `Authorization: Bearer <QUIVER_API_KEY>`. JSON requests also need `Content-Type: application/json`.
- Optional request header `x-trace-id` (1 to 256 chars), echoed back as `X-Trace-ID`.
- Every response carries `X-Request-ID`. Production keys also get data-posture headers (`x-quiver-inference-data-policy`, `x-quiver-payload-capture`, `x-quiver-request-metadata-policy`, `x-quiver-request-metadata-retention-seconds`, `x-quiver-zero-data-retention`). Test keys add `x-quiver-environment: test` and the SVG root gets `data-quiver-sandbox="true"`.
- SDKs: Node `@quiverai/sdk` (npm, 0.9.3 as of 2026-09-18, repo github.com/quiverai/quiverai-node, generated from the OpenAPI spec). No official Python package (`quiverai`, `quiver-ai`, `quiverai-sdk` all 404 on PyPI). The OpenAI JS SDK works against `/v1/responses` with `baseURL: "https://api.quiver.ai/v1"`. Vercel AI SDK via `@ai-sdk/open-responses`.

Endpoints:

| Method | Path | operationId | Purpose |
|---|---|---|---|
| GET | `/v1/models` | listModels | Catalog available to the org |
| GET | `/v1/models/{model}` | getModel | One model's metadata |
| POST | `/v1/svgs/generations` | generateSVG | Text to SVG (the one to use) |
| POST | `/v1/svgs/vectorizations` | vectorizeSVG | Image to SVG |
| POST | `/v1/svgs/edits` | editSVG | Natural-language edit of an SVG (Arrow 2 only) |
| POST | `/v1/svgs/animations` | animateSVG | Animate an SVG (Arrow 2 only) |
| POST | `/v1/responses` | createOpenResponse | OpenResponses-compatible agent endpoint, stateless, tool calls handled by caller |

### 3.1 POST /v1/svgs/generations (Text to SVG)

Request body (`GenerateSVGRequest`, from the OpenAPI spec):

| Field | Type | Default | Notes |
|---|---|---|---|
| `model` | string | required | e.g. `arrow-2-telos`, `arrow-2` |
| `prompt` | string | required | "Primary text prompt that describes the desired SVG." minLength 1, no max published |
| `instructions` | string | | "Additional style or formatting guidance." Keeps style separate from subject |
| `n` | integer 1..16 | 1 | Number of outputs. Fixed-credit models bill `n x svg_generate`; token models bill measured tokens |
| `stream` | boolean | false | true returns `text/event-stream` with `generating`, `reasoning`, `draft`, `content` events, ends with `data: [DONE]` |
| `reasoning_effort` | `low` / `medium` / `high` / `xhigh` | model default | Arrow 2 family |
| `references` | array, max 16 | | `{ "url": "..." }`, `{ "base64": "..." }`, or a bare URL string |
| `attributes.viewBox` | `{minX, minY, width, height}` | | Requested root viewBox |
| `max_output_tokens` | integer 1..65536 | | |
| `temperature` | number 0..2 | 1 | Advertised only for Arrow 1.x |
| `top_p` | number 0..1 | 1 | Advertised only for Arrow 1.x |
| `presence_penalty` | number -2..2 | 0 | Advertised only for Arrow 1.x |

There is no `style`, `colors`, `format`, `seed`, `negative_prompt`, or `aspect_ratio` field. Style and color go in `prompt` or `instructions`; aspect ratio goes in `attributes.viewBox`; there is no seed and no determinism control on Arrow 2.

Verbatim request examples from the OpenAPI spec:

```json
{
  "model": "arrow-2",
  "prompt": "Generate an icon of a unicorn",
  "stream": false
}
```

```json
{
  "instructions": "Use a flat monochrome style with rounded corners and clean geometry.",
  "max_output_tokens": 4096,
  "model": "arrow-2",
  "n": 2,
  "presence_penalty": 0.2,
  "prompt": "Generate a minimalist unicorn icon for a SaaS dashboard",
  "stream": false,
  "temperature": 0.4,
  "top_p": 0.95
}
```

```json
{
  "instructions": "Use flat monochrome geometry and keep them visually distinct.",
  "model": "arrow-2",
  "n": 2,
  "prompt": "Generate two minimalist unicorn badge variants",
  "stream": true
}
```

Verbatim cURL from docs.quiver.ai/developers/models/text-to-svg:

```bash
curl --request POST \
  --url https://api.quiver.ai/v1/svgs/generations \
  --header 'Authorization: Bearer <QUIVERAI_API_KEY>' \
  --header 'Content-Type: application/json' \
  --data '{
    "model": "arrow-2",
    "prompt": "Elegant calligraphic script in a flowing hand-lettered style, single continuous stroke"
  }'
```

Verbatim Node SDK example from the same page:

```ts
import { QuiverAI } from "@quiverai/sdk";
const client = new QuiverAI({
  bearerAuth: process.env["QUIVERAI_API_KEY"],
});
const result = await client.createSVGs.generateSVG({
  generateSVGRequest: {
    model: "arrow-2",
    prompt: "Japanese crane in traditional woodblock illustration style with warm earth tones",
    instructions: "Use a warm muted palette with detailed feather work",
  },
});
```

Response (`SvgResponse`, non-streaming), shape verified by the test call:

```json
{
  "id": "svg-f9517902337d420f9c60af13084472ab",
  "created": 1789760094,
  "data": [
    { "mime_type": "image/svg+xml", "svg": "<svg xmlns=\"http://www.w3.org/2000/svg\" width=\"1024\" height=\"1024\" viewBox=\"0 0 1024 1024\">...</svg>" }
  ],
  "usage": { "input_tokens": 476, "output_tokens": 7140, "total_tokens": 7616 }
}
```

The SVG comes back inline as a string (no URL, no base64, no job id, no polling). `data` has one entry per `n`. Fixed-credit models add `"credits": <int>` and zero the usage counters; token models omit `credits`.

Streaming event examples (verbatim from the spec):

```json
{ "event": "draft", "data": { "id": "svg_out_01J9AZ3XJ7D5S9ZV2Q5Z8E1A4N", "index": 1, "svg": "<svg xmlns=\"http://www.w3.org/2000/svg\"><path d=\"M12 2\"/></svg>", "type": "draft", "update_type": "snapshot" } }
```

```json
{ "event": "content", "data": { "credits": 20, "id": "svg_out_01J9AZ3XJ7D5S9ZV2Q5Z8E1A4N", "index": 1, "svg": "<svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 24 24\"><path d=\"M12 2l8 20H4z\"/></svg>", "type": "content", "usage": { "input_tokens": 0, "output_tokens": 0, "total_tokens": 0 } } }
```

Docs warn: "Do not persist preview output as an authoritative SVG." Only `content` events are final.

### 3.2 GET /v1/models

Verbatim from the docs:

```bash
curl -X GET "https://api.quiver.ai/v1/models" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

Response: `{ "object": "list", "data": [Model, ...] }`. `Model` fields: `id`, `name`, `description`, `object: "model"`, `owned_by: "quiverai"`, `created`, `context_length`, `max_output_length`, `input_modalities`, `output_modalities`, `supported_operations`, `supported_sampling_parameters`, `billing` (`{kind: "fixed_credit", unit: "credits_per_output"}` or `{kind: "token_usage", currency: "USD", pricing_model: "token_usage_v1", unit: "millicents_per_million_tokens", rates: {input, cached_input, cache_write, output}}`), `pricing_credits` (fixed models), deprecated `pricing` USD strings. Divide `rates` by 100,000 to get USD per 1M tokens (arrow-2-telos: input 600000 -> $6, output 3000000 -> $30).

### 3.3 POST /v1/svgs/edits (useful for refining a chosen ROSARIO mark)

Verbatim spec example:

```json
{
  "model": "arrow-2",
  "prompt": "Make the star bolder and simplify the outline",
  "stream": false,
  "svg": "<svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 24 24\"><path d=\"M12 2l3 7h7l-5.5 4.5L18 21l-6-4-6 4 1.5-7.5L2 9h7z\"/></svg>"
}
```

Fields: `model`, `prompt` (max 4000), exactly one of inline `svg` (max 200,000 chars) or `svg_source` (`{url}` or `{base64}`), optional `reference_images` (max 4), `max_review_steps` 0..5, `reasoning_effort`, `settings.{temperature, max_output_tokens, ...}`, `stream`. Returns the same `SvgResponse` shape.

### 3.4 Errors

Envelope: `{ "status": 429, "code": "rate_limit_exceeded", "message": "Rate limit exceeded", "request_id": "..." }`, plus optional `param` (path of the offending field) and `retry_after`. Codes: `invalid_request`, `invalid_api_key`, `unauthorized`, `funding_payment_failed`, `funding_payment_method_required`, `funding_payment_action_required`, `funding_pending`, `insufficient_credits` (402), `account_frozen`, `content_policy_violation` (403), `model_not_found` (404, also returned when the key lacks authority for the model), `payload_too_large` (413), `request_timeout` (408/504), `rate_limit_exceeded`, `operation_rate_limit_exceeded`, `weekly_limit_exceeded` (429), `server_error` (500), `model_error` (502), `model_unavailable` (503). Docs: branch on `status` and `code`, never on `message`; honor `Retry-After`; there is no idempotency key, so assess duplicate-work risk before retrying 5xx.

### 3.5 Rate limits

No fixed public numbers. Capacity comes from the org's usage tier, enforced on several independent dimensions: request rate, operation throughput, input token rate, output token rate; project overrides can lower them. Headers: `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset` (epoch ms), `X-RateLimit-Scope`, `X-RateLimit-Subject`, `X-RateLimit-Dimension`, `Retry-After` on 429. Observed on the test call for this org: `x-ratelimit-dimension: operation_throughput`, `x-ratelimit-scope: operation_class`, `x-ratelimit-subject: svg_generate`, `x-ratelimit-limit: 20`, `x-ratelimit-remaining: 19`, `x-ratelimit-reset: 1789760040000` (19:34:00 UTC, the top of the minute after the request started), so about 20 generation requests per minute. Sandbox keys have their own budget. Review live numbers at platform.quiver.ai/limits.

### 3.6 Billing

API usage draws from the org's prepaid API balance (platform.quiver.ai/billing), not App subscription credits. Minimum purchase $10, credits expire after 1 year, 1 credit = $0.01. Token-priced requests place a temporary $1 hold before dispatch and settle actual usage afterwards. 402 `insufficient_credits` is returned before the model runs if the balance cannot cover the request. Output tokens include reasoning tokens. Worked example from docs: 10,000 input + 2,000 output tokens = $0.08 on Arrow 2, $0.12 on Telos.

## 4. Prompting guide (from QuiverAI docs and landing page)

Docs recipe (Text to SVG page, "Writing prompts"), verbatim elements:

- **Subject:** "What is in the image? Be specific. For example, 'a logo for an eco-friendly coffee company'."
- **Style:** "What is the overall aesthetic? For example, 'line art', 'hand drawn', 'duotone', or 'flat monochrome icon'."
- **Color palette:** "Which colors should be used? For example, 'background: #e9edc9 and logo in #fb8500'."
- **Composition:** "Include framing details like 'centered icon' or 'wide horizontal logo'."
- **Text integration:** "Clearly state what text should appear and how. For example, 'The headline "URBAN EXPLORER" in bold white sans-serif at the top'."
- "You can also use the `instructions` parameter to provide separate style or formatting guidance without mixing it into the prompt."

SVG guide tips: "Be explicit about style: e.g. 'flat monochrome icon', 'duotone illustration', 'clean geometric lines'." "Constrain composition: Include framing details like 'centered icon' or 'wide horizontal logo'."

Style keywords that appear in official examples: minimalist, monogram, sharp vector paths, flat monochrome, duotone, line art, hand drawn, clean geometry, geometric, isometric line art, woodblock illustration, heraldic crest, ornate medieval, gold gradient accents, calligraphic script, single continuous stroke, bold black-and-white, retro, grotesque, emblem. There is no enumerated style list; it is free text.

Brand colors: hex codes in the prompt or `instructions` (`"logo in #7A1F3D on background #000000"`). The test confirmed the model honors named colors ("burgundy on black" produced `#94092f` family fills on `#000100`). For exact brand hex, pass hex explicitly. For a transparent background, say so; the model otherwise adds a `<rect>` background layer (observed).

Logo types. Docs do not define these terms, so steer with plain language:

- Pictorial mark: "a [subject] logo mark, no text, centered icon". The test prompt is this pattern.
- Monogram / lettermark: the landing page's own example is "Create a minimalist monogram logo using the letter Q with sharp vector paths". For ROSARIO: "monogram of the letter R, ...". Add "single letter, no other text".
- Wordmark: state the text and treatment explicitly per the docs' text-integration rule: "wordmark 'ROSARIO' in bold geometric uppercase sans-serif, letterspaced, single color". Third-party tests report weak text fidelity, so verify letters and expect to rebuild type by hand.
- Combination mark / lockup: "wide horizontal logo: rose mark on the left, wordmark 'ROSARIO' on the right".
- Emblem / badge: "circular emblem badge with ... enclosed in a ring".

Variations:

- `n` (1 to 16) returns several outputs for one prompt in one request; the spec example adds `instructions: "... keep them visually distinct."` Token models bill each output's tokens.
- Prompt sweeps: vary style words per request (see script in section 6).
- `reasoning_effort: "high"` or `"xhigh"` for harder briefs on Arrow 2 (more output tokens, so more cost).
- `references`: pass an earlier winning SVG or a mood image as `{ "url" }` or `{ "base64" }` to hold palette and shape language; the blog says Arrow 2 "can produce new variations that retain its palette, shape language, and graphic treatment" from a reference.
- `/v1/svgs/edits`: iterate on a chosen SVG with instructions such as "make the mark bolder", "remove the background rect", "reduce to a single flat fill".
- No seed: Arrow 2 exposes no sampling parameters, so identical prompts produce different results.

Suggested ROSARIO prompt shape (derived from the rules above, not from Quiver docs):

```
prompt: "Logo mark for a brand named ROSARIO: a single geometric rose seen from above, built from a few clean curved paths. Pictorial mark only, no text. Centered, generous padding."
instructions: "Flat single color: rose in #7A1F3D on a solid #000000 background. Clean geometry, minimal nodes, no gradients, no strokes, no shadows. Production-ready SVG."
```

## 5. Test call log (2026-09-18)

Read-only check first:

```
GET https://api.quiver.ai/v1/models
Authorization: Bearer sk_live_[REDACTED]
User-Agent: OpenAI File Downloader, XaiImageApiFetch/1.0
-> HTTP 200, x-request-id: 5697d4d8-4c21-46ea-b3f8-a07a0c183bef
-> 5 models: arrow-1, arrow-1.1, arrow-1.1-max, arrow-2, arrow-2-telos (bodies in section 2)
-> data posture headers: x-quiver-inference-data-policy: forbid_storage, x-quiver-payload-capture: off,
   x-quiver-request-metadata-policy: full, x-quiver-request-metadata-retention-seconds: 86400, x-quiver-zero-data-retention: false
```

Single generation (one of the two allowed; the second was not used):

```
POST https://api.quiver.ai/v1/svgs/generations
Authorization: Bearer sk_live_[REDACTED]
Content-Type: application/json
x-trace-id: rosario-research-test-1
User-Agent: OpenAI File Downloader, XaiImageApiFetch/1.0

{
  "model": "arrow-2-telos",
  "prompt": "minimal geometric rose mark, single color, burgundy on black, logo",
  "n": 1,
  "stream": false
}
```

Result:

- HTTP 200 after 82.9 s (non-streaming; the whole SVG is generated before the response).
- Headers of interest: `x-request-id: a91c1caa-a0cd-4e5c-a0fb-e1aabcf0d107`, `x-trace-id: rosario-research-test-1` (echoed), `x-ratelimit-dimension: operation_throughput`, `x-ratelimit-scope: operation_class`, `x-ratelimit-subject: svg_generate`, `x-ratelimit-limit: 20`, `x-ratelimit-remaining: 19`, `x-ratelimit-reset: 1789760040000`. No cost header; cost is in the body `usage`.
- Body: `{ "id": "svg-f9517902337d420f9c60af13084472ab", "created": 1789760094, "data": [ { "mime_type": "image/svg+xml", "svg": "<svg ...>" } ], "usage": { "input_tokens": 476, "output_tokens": 7140, "total_tokens": 7616 } }`. No `credits` field (token-priced model).
- Cost: 476 x $6/1M + 7140 x $30/1M = $0.217.
- Output saved to `frontend/research/screens/quiver/test-rose.svg` (4,843 bytes). Root: `<svg xmlns="http://www.w3.org/2000/svg" width="1024" height="1024" viewBox="0 0 1024 1024">`. Elements: `defs`, `radialGradient`, `linearGradient`, `rect` (full black background `#000100`), one `<g id="geometric-crimson-rose">` with named `<path>` petals, fills `#94092f`/`#90072c`/`#870526` gradients, stroke `#65041f`. No `<text>`. Rendered preview: `frontend/research/screens/quiver/test-rose-render.png` (Chromium render). Visually a flat, layered geometric rose from above, burgundy on black, on brief. Note the model added subtle gradients despite "single color"; say "flat fill, no gradients" in `instructions` when that matters.

Screenshots taken: `quiver-landing.png`, `docs-models.png`, `docs-text-to-svg-examples.png` (includes the three official example outputs: calligraphy, crane illustration, heraldic lion logo), `docs-pricing.png`, `blog-arrow-2.png`.

## 6. Script skeleton: N logo variants with the latest model

Saves one SVG per prompt into an output directory, logs tokens and estimated cost, stops on the first non-200. `jq` and `curl` required (both present on this machine). Change `MODEL` to `arrow-2` for cheaper, faster sweeps.

```bash
#!/usr/bin/env bash
# Generate ROSARIO logo variants with QuiverAI Arrow 2 Telos.
# Usage: ./quiver-logos.sh [out_dir]
set -euo pipefail

REPO="$(cd "$(dirname "$0")" && pwd)"
ENV_FILE="${ENV_FILE:-$REPO/.env}"
OUT="${1:-$REPO/frontend/research/screens/quiver/rosario}"
MODEL="${MODEL:-arrow-2-telos}"          # or arrow-2 for cheaper iteration
UA="OpenAI File Downloader, XaiImageApiFetch/1.0"

# Read the key without echoing it.
KEY="$(grep '^QUIVER_API_KEY=' "$ENV_FILE" | cut -d= -f2- | tr -d '"'"'"' ')"
[ -n "$KEY" ] || { echo "QUIVER_API_KEY missing in $ENV_FILE" >&2; exit 1; }
mkdir -p "$OUT"

# Shared style guidance; kept out of the prompt per Quiver docs.
INSTRUCTIONS='Brand: ROSARIO. Flat single color: mark in #7A1F3D on a solid #000000 background. Clean geometry, minimal nodes, no gradients, no strokes, no shadows, no text unless the prompt asks for it. Centered with generous padding. Production-ready SVG.'

# One line per variant: <slug>|<prompt>
VARIANTS=(
  'rose-topdown|Logo mark: a single geometric rose seen from above, built from a few clean curved paths. Pictorial mark only, no text.'
  'rose-profile|Logo mark: a stylized rose in profile with one stem and one leaf, reduced to bold geometric shapes. Pictorial mark only, no text.'
  'monogram-r|Minimalist monogram logo of the letter R whose bowl becomes a rose spiral. Sharp vector paths. Single letter, no other text.'
  'wordmark|Wordmark logo: the text ROSARIO in bold geometric uppercase sans-serif, letterspaced, single color, wide horizontal logo.'
  'emblem|Circular emblem badge: a geometric rose centered inside a thin ring. Pictorial mark only, no text.'
  'lockup|Wide horizontal logo lockup: a geometric rose mark on the left and the wordmark ROSARIO on the right in bold uppercase sans-serif.'
)

total_cost=0
for line in "${VARIANTS[@]}"; do
  slug="${line%%|*}"; prompt="${line#*|}"
  body="$(jq -n --arg m "$MODEL" --arg p "$prompt" --arg i "$INSTRUCTIONS" \
    '{model:$m, prompt:$p, instructions:$i, n:1, stream:false}')"
  echo "== $slug ($MODEL)"
  resp="$(curl -sS --max-time 600 -A "$UA" \
    -X POST https://api.quiver.ai/v1/svgs/generations \
    -H "Authorization: Bearer $KEY" -H "Content-Type: application/json" \
    -H "x-trace-id: rosario-$slug" \
    -w '\n%{http_code}' --data-binary "$body")"
  code="${resp##*$'\n'}"; json="${resp%$'\n'*}"
  if [ "$code" != "200" ]; then
    echo "HTTP $code: $json" >&2; exit 1
  fi
  # n=1 so data[0]; with n>1 loop over .data[] and suffix the index.
  jq -r '.data[0].svg' <<<"$json" > "$OUT/$slug.svg"
  in_t="$(jq -r '.usage.input_tokens // 0' <<<"$json")"
  out_t="$(jq -r '.usage.output_tokens // 0' <<<"$json")"
  # Telos: $6/M in, $30/M out. Arrow 2: $4/M in, $20/M out.
  case "$MODEL" in
    arrow-2-telos) cost="$(awk -v i="$in_t" -v o="$out_t" 'BEGIN{printf "%.4f", i*6/1e6 + o*30/1e6}')" ;;
    arrow-2)       cost="$(awk -v i="$in_t" -v o="$out_t" 'BEGIN{printf "%.4f", i*4/1e6 + o*20/1e6}')" ;;
    *)             cost="n/a" ;;
  esac
  echo "saved $OUT/$slug.svg  tokens in=$in_t out=$out_t  est \$$cost  request_id=$(jq -r .id <<<"$json")"
  [ "$cost" != "n/a" ] && total_cost="$(awk -v a="$total_cost" -v b="$cost" 'BEGIN{printf "%.4f", a+b}')"
done
echo "done. estimated total \$$total_cost"
```

Expect roughly $0.15 to $0.35 and 60 to 120 s per Telos variant based on the one measured call. Six variants sequentially fit well under the observed 20 per minute operation limit. To rasterize for previews, open the SVG in Chromium (agent-browser with `--allow-file-access`) or use a proper SVG renderer; ImageMagick's built-in MSVG delegate mishandled the gradients here.

## 7. Sources

- https://quiver.ai (landing, use cases, developer summary)
- https://quiver.ai/blog/introducing-arrow-2-0 (Arrow 2 and Arrow 2 Telos announcement, 2026-09-07)
- https://quiver.ai/blog/announcing-our-seed-round (company background, Arrow 1.0)
- https://quiver.ai/pricing (App plans)
- https://docs.quiver.ai/llms.txt (docs index)
- https://docs.quiver.ai/api-reference/introduction
- https://docs.quiver.ai/api-reference/create-svgs/generatesvg
- https://docs.quiver.ai/api-reference/models/listmodels
- https://docs.quiver.ai/developers/models
- https://docs.quiver.ai/developers/models/arrow-2-telos
- https://docs.quiver.ai/developers/models/text-to-svg (prompting guide, examples, parameter table)
- https://docs.quiver.ai/developers/pricing
- https://docs.quiver.ai/developers/quickstart (Responses API tool-loop example)
- https://docs.quiver.ai/developers/guides/scalable-vector-graphics-svg
- https://docs.quiver.ai/developers/guides/errors-and-debugging
- https://docs.quiver.ai/developers/guides/sandbox-and-test-keys
- https://docs.quiver.ai/developers/platform/billing-and-limits
- https://docs.quiver.ai/app, https://docs.quiver.ai/app/mcp, https://docs.quiver.ai/app/pricing
- https://api.quiver.ai/v1/openapi.json (OpenAPI 3.1, version 1.0.0; source of the verbatim request and SSE examples)
- https://registry.npmjs.org/@quiverai/sdk and https://registry.npmjs.org/quiverai (SDK and CLI versions)
- Live API calls with the project key (GET /v1/models, one POST /v1/svgs/generations), 2026-09-18
- Third-party: DesignCourse "QuiverAI - Are Illustrators and Brand Designers Cooked? 5 Tests" (YouTube, 2026-02-27) for the text-rendering weakness

## 8. Unverified

- Whether `temperature`, `top_p`, `presence_penalty` are rejected (400) or silently ignored on `arrow-2` / `arrow-2-telos`. The spec and Text to SVG docs list them; the catalog reports `supported_sampling_parameters: []` for both Arrow 2 models. Not tested (generation budget).
- Effect and cost of `reasoning_effort` levels, and the Arrow 2 default level.
- Arrow 2 runtime cap on `references` (docs only state 4 for Arrow 1.x and 16 for Arrow 1.1 Max).
- Actual Arrow 2 (non-Telos) latency and token usage for the same prompt; only Telos was measured (83 s, 7,140 output tokens).
- Whether the 20 per minute `svg_generate` limit is a fixed one-minute window for this org tier, and the request-rate and token-rate ceilings (view at platform.quiver.ai/limits).
- The org's current prepaid balance and whether the key authorizes `svg_edit`, `svg_animate`, `svg_vectorize`, or `open_responses` (only `svg_generate` on `arrow-2-telos` and catalog read were exercised).
- Text fidelity of Arrow 2 wordmarks ("ROSARIO"); the weakness is reported for Arrow 1 by third parties and not retested here.
- Whether `attributes.viewBox` also sets `width`/`height` on the root or only `viewBox`.
- Streaming behavior on Telos (only non-streaming tested).
