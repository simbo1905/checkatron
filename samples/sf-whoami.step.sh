#!/usr/bin/env sh
# POSIX. Step-by-step SnowSQL context check with hard timeouts and full log.
set -eu
set -x

DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
LOG="$DIR/sf-whoami.step.log"

# Tee all output to log
exec >"$LOG" 2>&1

# Timeout helper using perl (portable on macOS)
timeout() {
  # usage: timeout SECONDS cmd ...
  perl -e 'alarm shift @ARGV; exec @ARGV' "$@"
}

CONFIG=${SNOWSQL_CONFIG_FILE:-"$DIR/snowsql-demo.config"}

# Prefer key-enc if present, else key, else external browser
if [ -f "$DIR/../rsa_key_encrypted.p8" ]; then
  CONN=${SNOWSQL_CONN:-demo_key_enc}
elif [ -f "$DIR/../rsa_key.pem" ]; then
  CONN=${SNOWSQL_CONN:-demo_key}
else
  CONN=${SNOWSQL_CONN:-demo_ext}
fi

# Locate snowsql
if command -v snowsql >/dev/null 2>&1; then
  SNOWSQL=snowsql
elif [ -x "/Applications/SnowSQL.app/Contents/MacOS/snowsql" ]; then
  SNOWSQL="/Applications/SnowSQL.app/Contents/MacOS/snowsql"
else
  echo "snowsql not found on PATH or in /Applications" >&2
  exit 127
fi

echo "== Step 1: Version =="
timeout 15 "$SNOWSQL" -v || true

echo "== Step 2: Show config & connection =="
ls -l "$CONFIG" || true
echo "Using connection: $CONN"

echo "== Step 3: Query session context =="
timeout 70 "$SNOWSQL" \
  --config "$CONFIG" \
  -c "$CONN" \
  -o output_format=csv \
  -o header=true \
  -o friendly=false \
  -o log_level=ERROR \
  -q "select current_warehouse(), current_database(), current_schema(), current_role();" || true

echo "== END SUMMARY =="
echo "Log saved to: $LOG"

