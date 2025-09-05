#!/usr/bin/env sh
# WHY: approved SQL runs without per-step prompts; reads first line from INPUT and executes.
# NOTE: Do not use `--` line comments in SQL statements that will be flattened to one line.
#       Use `/* ... */` block comments instead; `--` comments will eat the remainder of the line.
set -eu

SNOWSQL_BIN=${SNOWSQL_BIN:-"/Applications/SnowSQL.app/Contents/MacOS/snowsql"}
SNOWSQL_CONFIG=${SNOWSQL_CONFIG:-"demo/snowsql-demo.config"}
SNOWSQL_CONN=${SNOWSQL_CONN:-"my_example_connection"}

INPUT=${INPUT:-"script.steps.sql.input"}    # one SQL statement per line
OUTPUT=${OUTPUT:-"script.steps.sql.output"}  # append-only log

ts() { date -u +"%Y-%m-%dT%H:%M:%SZ"; }

[ -s "$INPUT" ] || { echo "no steps pending" | tee -a "$OUTPUT"; exit 0; }

# read exactly the first line
IFS= read -r SQL <"$INPUT" || SQL=""
[ -n "$SQL" ] || { echo "empty first line" | tee -a "$OUTPUT"; exit 1; }

{
  echo "----- $(ts)"
  echo "SQL: $SQL"
} >>"$OUTPUT"

TMP=$(mktemp -t snowsql.out)
if "$SNOWSQL_BIN" --config "$SNOWSQL_CONFIG" -c "$SNOWSQL_CONN" -q "$SQL" >"$TMP" 2>&1; then
  tee -a "$OUTPUT" <"$TMP" >/dev/null
  # success: drop first line
  tail -n +2 "$INPUT" >"$INPUT.tmp" && mv "$INPUT.tmp" "$INPUT"
  echo "RESULT: SUCCESS" | tee -a "$OUTPUT"
  rm -f "$TMP"
  exit 0
else
  tee -a "$OUTPUT" <"$TMP" >/dev/null
  echo "RESULT: FAILURE" | tee -a "$OUTPUT"
  rm -f "$TMP"
  exit 1
fi
