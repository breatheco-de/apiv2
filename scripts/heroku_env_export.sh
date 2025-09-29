#!/usr/bin/env bash
# Export Heroku config vars to .env format
# Usage:
#   scripts/heroku_env_export.sh <heroku-app-name> [output=.env]
#
# Notes:
# - Requires the Heroku CLI installed and authenticated.
# - Writes the raw CLI output to .env.heroku and converts it to dotenv format.
# - If GOOGLE_APPLICATION_CREDENTIALS and GOOGLE_SERVICE_KEY are present in the
#   generated env file, it will write the JSON (or base64-decoded content) to
#   the credential path.

set -euo pipefail

APP="${1:-}"
OUT="${2:-.env.heroku}"
HEROKU_BIN="${HEROKU_BIN:-heroku}"

if [[ -z "$APP" ]]; then
  echo "Usage: $0 <heroku-app-name> [output=.env]" >&2
  exit 1
fi

# 1) Fetch config from Heroku (prefer JSON)
JSON_OK=0
if $HEROKU_BIN config -a "$APP" --json > .env.heroku.json 2>/dev/null; then
  JSON_OK=1
else
  # Fallback to text mode
  $HEROKU_BIN config -a "$APP" > .env.heroku
fi

# 2) Build .env output
if [[ $JSON_OK -eq 1 ]]; then
  # Use python to convert JSON to .env and also materialize Google creds
  python3 - <<PY
import json, os, sys, base64
from datetime import datetime, timezone

app = os.environ.get('APP_NAME', '${APP}')
out = os.environ.get('OUT_FILE', '${OUT}')
with open('.env.heroku.json', 'r') as f:
    data = json.load(f)

ts = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
lines = [f"# Generated from heroku config -a {app} on {ts}"]
for k, v in sorted(data.items()):
    s = v if isinstance(v, str) else str(v)
    # Minify JSON-looking strings
    if isinstance(s, str) and s.strip().startswith('{') and s.strip().endswith('}'):
        try:
            s = json.dumps(json.loads(s), separators=(',', ':'))
        except Exception:
            pass
    lines.append(f"{k}={s}")

with open(out, 'w') as f:
    f.write("\n".join(lines) + "\n")

cred_path = data.get('GOOGLE_APPLICATION_CREDENTIALS')
key_json = data.get('GOOGLE_SERVICE_KEY')
if cred_path and key_json:
    os.makedirs(os.path.dirname(cred_path), exist_ok=True)
    raw = key_json
    # Try base64 decode first
    try:
        raw_dec = base64.b64decode(key_json)
        # if result looks like JSON, use it
        try:
            json.loads(raw_dec)
            raw = raw_dec.decode('utf-8')
        except Exception:
            pass
    except Exception:
        pass

    with open(cred_path, 'w') as f:
        f.write(raw)
    # Validate JSON (non-fatal)
    try:
        json.load(open(cred_path))
    except Exception as e:
        sys.stderr.write(f"warning: {cred_path} is not valid JSON: {e}\n")

print(f"Wrote {out} (source: .env.heroku.json)")
if cred_path and key_json:
    print(f"Materialized Google credentials at {cred_path}")
PY
else
  # Text fallback, convert to dotenv (.env) format
  #    - Skip header lines like '=== <app> Config Vars'
  #    - Convert 'KEY:    VALUE' -> 'KEY=VALUE'
  #    - Trim surrounding whitespace
  awk '
  function ltrim(s){ sub(/^[ \t\r\n]+/, "", s); return s }
  function rtrim(s){ sub(/[ \t\r\n]+$/, "", s); return s }
  function trim(s){ return rtrim(ltrim(s)) }
  # Skip headers and empty lines
  /^==/ { next }
  /Config Vars/ { next }
  /^[[:space:]]*$/ { next }
  # Only process lines that look like KEY: VALUE
  /^[A-Za-z0-9_]+:[[:space:]]/ {
    split($0, arr, ":")
    key = trim(arr[1])
    # value starts after the first ':'
    val = substr($0, length(arr[1]) + 2)
    val = trim(val)
    print key "=" val
  }
  ' .env.heroku > "$OUT"

  printf "# Generated from heroku config -a %s on %s\n" "$APP" "$(date -u +'%Y-%m-%dT%H:%M:%SZ')" | cat - "$OUT" > "$OUT.tmp" && mv "$OUT.tmp" "$OUT"

  echo "Wrote $OUT (source: .env.heroku)"

  # Try to materialize google creds from text .env (best-effort)
  cred_path="$(grep -E '^GOOGLE_APPLICATION_CREDENTIALS=' "$OUT" | head -n1 | cut -d'=' -f2-)"
  key_json="$(grep -E '^GOOGLE_SERVICE_KEY=' "$OUT" | head -n1 | cut -d'=' -f2-)"
  if [[ -n "$cred_path" && -n "$key_json" ]]; then
    mkdir -p "$(dirname "$cred_path")" || true
    printf '%s\n' "$key_json" > "$cred_path"
    echo "Materialized Google credentials at $cred_path"
  fi
fi
