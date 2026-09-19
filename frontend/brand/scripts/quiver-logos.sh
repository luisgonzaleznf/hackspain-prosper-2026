#!/usr/bin/env bash
# Generate ROSARIO logo candidates with QuiverAI (SVG output).
# Usage: quiver-logos.sh <variants-file> [out_dir]
#   variants-file: one "<slug>|<prompt>" per line, # comments allowed.
#   MODEL=arrow-2 (default, cheap sweep) or arrow-2-telos (final quality).
# Reads QUIVER_API_KEY from the repo .env. Never echoes the key.
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
REPO="$(cd "$HERE/../../.." && pwd)"
ENV_FILE="${ENV_FILE:-$REPO/.env}"
VARIANTS_FILE="${1:?variants file required}"
OUT="${2:-$HERE/../logos/candidates}"
MODEL="${MODEL:-arrow-2}"
UA="OpenAI File Downloader, XaiImageApiFetch/1.0"

KEY="$(grep '^QUIVER_API_KEY=' "$ENV_FILE" | cut -d= -f2- | tr -d '"'"'"' ')"
[ -n "$KEY" ] || { echo "QUIVER_API_KEY missing in $ENV_FILE" >&2; exit 1; }
mkdir -p "$OUT"

# Style guidance kept separate from the subject, per Quiver docs.
# Placeholder burgundy: outputs are SVG, so fills get recolored to the final
# brand hex afterwards. Flat fills only so recoloring is a find/replace.
INSTRUCTIONS="${INSTRUCTIONS:-Brand: ROSARIO, a voice AI receptionist for clinics. Flat single color: mark in #7A1F3D on a solid #000000 background rect. Clean geometry, few control points, no gradients, no strokes, no shadows, no text unless the prompt asks for it. Centered with generous padding. Production-ready logo SVG.}"

log="$OUT/generation-log.tsv"
[ -f "$log" ] || printf 'slug\tmodel\tin_tokens\tout_tokens\test_usd\trequest_id\n' > "$log"

grep -v '^\s*#' "$VARIANTS_FILE" | grep -v '^\s*$' | while IFS='|' read -r slug prompt; do
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
    echo "HTTP $code for $slug: $json" >&2
    continue
  fi
  jq -r '.data[0].svg' <<<"$json" > "$OUT/$slug.svg"
  in_t="$(jq -r '.usage.input_tokens // 0' <<<"$json")"
  out_t="$(jq -r '.usage.output_tokens // 0' <<<"$json")"
  case "$MODEL" in
    arrow-2-telos) cost="$(awk -v i="$in_t" -v o="$out_t" 'BEGIN{printf "%.4f", i*6/1e6 + o*30/1e6}')" ;;
    arrow-2)       cost="$(awk -v i="$in_t" -v o="$out_t" 'BEGIN{printf "%.4f", i*4/1e6 + o*20/1e6}')" ;;
    *)             cost="n/a" ;;
  esac
  printf '%s\t%s\t%s\t%s\t%s\t%s\n' "$slug" "$MODEL" "$in_t" "$out_t" "$cost" "$(jq -r .id <<<"$json")" >> "$log"
  echo "saved $OUT/$slug.svg  in=$in_t out=$out_t  est \$$cost"
done
echo "done."
