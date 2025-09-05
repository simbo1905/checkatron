---
title: Agents Guide
description: Durable guidance for engineers and AI coding agents working in this repository.
---

# Agents Guide

This document helps humans and AI agents explore, run, test, and evolve the project without depending on brittle, fast‑changing details. For user‑facing features, commands, and the most up‑to‑date options, always consult `README.md` (source of truth).

## Overview

- Purpose: generate ANSI/Snowflake‑friendly SQL that compares two datasets and surfaces column‑wise differences and row presence/absence.
- Approach: small Python codepath renders Jinja2 SQL templates; tests validate behavior via DuckDB.
- Audience: data engineers, developers, and AI agents contributing changes.

## Source Of Truth

- User docs and examples: see `README.md`.
- Contributor norms and workflows: this guide.
- Template semantics: tests pin intended behavior; update tests alongside template changes.

## Codebase Shape (Stable Mental Model)

Treat names as illustrative—expect these areas, even if exact filenames evolve:

- Core Python: loads schema CSVs, reads key columns, and renders SQL via Jinja2.
- Templates: Jinja2 SQL defining null‑safe joins on business keys and per‑column status outputs.
- Samples: example schema CSVs and a simple driver script to generate demo SQL.
- Tests: pytest suite using DuckDB to exercise template logic and assert outcomes.
- Packaging/Config: standard Python packaging with editable installs for local dev and CI.

## Runbook

Local setup (example; adjust to your environment):

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install -e .
```

Generate SQL and run examples: see `README.md` for current commands and flags.

## Testing

- Runner: `pytest`
- DB: DuckDB in‑memory for fast verification
- Typical invocations:
  - `python -m pytest -q`
  - Filter to a single test when iterating on templates
- Testing ethos: keep cases small and table‑driven; cover null‑safety, differing schemas, and row presence/absence.

## Conventions

- Inputs: CSVs produced by a DESCRIBE‑TABLE‑style command; a separate CSV lists the business key columns.
- Joins: null‑safe equality across the key set to pair rows between datasets.
- Diff output: per‑column status codes and a row‑level presence indicator (machine‑filterable). Exact meanings live in tests/README.
- Templating: prefer Jinja2 macros/CTEs over embedding SQL in Python; evolve templates with tests.
- Types: infer only what is required for safe rendering/quoting; keep SQL ANSI‑friendly.

## Common Tasks

- Explore: locate the SQL builder and templates; use your preferred code search.
- Evolve templates: add macros/CTEs to support new comparison needs; update tests accordingly.
- Extend CLI: introduce options judiciously and keep sensible defaults; document in `README.md`.
- Add tests: build minimal DuckDB tables/rows and assert status outcomes for mismatches, nulls, and missing rows.

## Change Safety

- Update or add tests when changing template logic or output semantics.
- Keep backward‑compatible defaults when adding flags.
- Avoid hard‑coding filenames/paths in this guide; keep guidance role‑based, not file‑based.

## Troubleshooting

- Imports fail: ensure your virtual environment is active and the package is installed in editable mode.
- Template not found: verify runtime resolves templates relative to the package/module, not the current working directory.
- Missing dependencies: install requirements and dev tools before running tests.

## Tooling Neutrality

This repo does not mandate specific editors, agents, or external servers. Use whatever tooling helps you navigate and contribute. Any code‑pack, search, or analysis helpers are optional.

## Contact & Changes

- Start with `README.md` for user workflows.
- Open an issue/PR to propose semantic changes (e.g., status conventions, new filters, dialect support).

## SnowSQL Diagnostics Probe (Disposable)

Purpose: fact‑finding only. Fast, safe, no changes. Time‑limited per step. Writes a single log and prints a clear findings summary.

- Run checked‑in probe (preferred):
  - `python diagnostics/snowsql_probe.py --timeout 3 --log diagnostics/snowsql_probe.log`
  - Reads PATH, resolves `snowsql`, inspects typical locations, checks `~/.snowsql` readability, attempts `snowsql -v`, and a short query (may time out). Summarizes findings at the bottom of the log.

- Disposable heredoc (no files left behind):
  - If you can't access repo files, you can inline a minimal probe:
    ```bash
    python - <<'PY'
import os, shutil, subprocess, sys, time, datetime as dt
def run(cmd, t=3):
    print(f"$ {' '.join(cmd)} (timeout={t}s)")
    try:
        p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=t)
        print(p.stdout, end=''); print(p.stderr, end=''); print(f"rc={p.returncode}")
        return p.returncode, p.stdout, p.stderr, False
    except subprocess.TimeoutExpired:
        print(f"TIMEOUT after {t}s"); return 124, '', '', True
exe = shutil.which('snowsql'); print('PATH=', os.environ.get('PATH',''))
print('snowsql=', exe)
findings=[]
if exe:
  rc, out, _, to = run([exe, '-v'])
  findings.append('version ok' if rc==0 and not to else 'version check failed/timed out')
  rc, out, _, to = run([exe, '-o','friendly=false','-o','timing=false','-o','output_format=csv','-q','select current_timestamp();'])
  findings.append('connect/query ok' if rc==0 and not to else 'connect/query failed or timed out (expected if not configured)')
else:
  findings.append('snowsql not found on PATH')
print('\n=== FINDINGS SUMMARY ===')
for f in findings: print('-', f)
print('=== END ===')
PY
    ```

Crash‑resilience principles
- Add before remove: prefer additive diagnostics and keep prior commands until the new path is proven.
- Short timeouts: default 3s per external call to avoid agent stalls.
- Single log file: print as you go and summarize findings explicitly at the end.
- No fixes in probes: separate fact‑finding from remediation; open an issue/PR for changes.

## Step Ledger Runner (Idempotent Validation)

Purpose: run validation flows in discrete, resumable steps. Each completed step writes a sentinel file under `artifacts/ledger/NN_name.ok`. Re‑running resumes at the next missing step. No deletes before adds.

- Run locally (no Snowflake):
  - `make local`  (equivalent: `python tools/step_ledger.py --plan local`)
  - Steps: pytest → generate sample diff SQL → sanity check SQL tokens.

- Run against Snowflake (requires snowsql + creds):
  - `make snowflake`  (equivalent: `python tools/step_ledger.py --plan snowflake`)
  - Steps: probe → setup TEMP tables → load data → DESCRIBE to CSV → generate → execute → validate summary.
  - Uses `SNOWSQL_PROFILE` if set; otherwise relies on your default snowsql config.

- Reset the ledger safely (archive, do not delete):
  - `make reset-ledger`  (equivalent: `python tools/step_ledger.py --reset`)
  - Archives `artifacts/ledger` to `artifacts/ledger.<timestamp>.bak`.

Design guarantees
- Idempotence: steps are safe to re‑run; completed steps are skipped via sentinels.
- Single log: `artifacts/step_ledger.log` captures command output and outcomes.
- Add‑before‑remove: runner never deletes prior state as part of step completion.

## SnowSQL Run Convention (Fast, Evidenced)

- Always run direct commands (no wrapper scripts) with a hard timeout and timing:
  - `time timeout 90 "/Applications/SnowSQL.app/Contents/MacOS/snowsql" --config demo/snowsql-demo.config -c my_example_connection -q "...;"`
- If a command times out, manually retry with a higher timeout up to 300s.
- Present raw command + raw output as the evidence; no narration.

## Approval-Friendly Execution

- Prefer reusing the same command form across steps (only SQL changes), or use the pre‑approved batch runner `./run-sql-steps.sh` that reads the next SQL from a file.
- Avoid one-off, unique shell lines that trigger repeated approvals; keep the shell command stable and feed it different inputs.

Batch Runner
- Runner: `./run-sql-steps.sh`
- Input stack (one SQL per line): `script.steps.sql.input`
- Output log (append‑only): `script.steps.sql.output`
- Example (repeat until stack empty):
  - `time timeout 60 ./run-sql-steps.sh`
- Reset stack from template:
  - `cp script.steps.sql.input.example script.steps.sql.input`

## SQL Commenting Rule (Batchable)

- Do not use `--` comments in SQL that will be flattened to one line (they will comment out the remainder).
- Prefer `/* ... */` block comments in Jinja2 templates and samples so the SQL remains valid when collapsed to a single line.
