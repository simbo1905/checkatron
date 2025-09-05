#!/usr/bin/env python3
"""
Step‑ledger runner: idempotent, crash‑resilient validation flows.

Principles
- Add before remove: never delete prior state until the next step is proven.
- Sentinels: each step writes artifacts/ledger/<NN>_<name>.ok when complete.
- Idempotent: re‑runs skip completed steps; safe to resume after crash.
- Logs: single log at artifacts/step_ledger.log with clear step outcomes.

Plans
- local: validate without Snowflake (run tests, generate example SQL, sanity checks).
- snowflake: outline Snowflake validation (executes only if `snowsql` present).

Usage
  python tools/step_ledger.py --plan local
  python tools/step_ledger.py --plan snowflake  # requires snowsql and creds
  python tools/step_ledger.py --reset           # archive ledger (no delete)
"""
from __future__ import annotations

import argparse
import datetime as dt
import os
import shutil
import subprocess as sp
import sys
from pathlib import Path
from typing import Callable, List, Optional

ROOT = Path(__file__).resolve().parent.parent
ART = ROOT / "artifacts"
LEDGER = ART / "ledger"
LOG = ART / "step_ledger.log"


def now() -> str:
    return dt.datetime.now().isoformat(timespec="seconds")


def log(msg: str) -> None:
    ART.mkdir(parents=True, exist_ok=True)
    with LOG.open("a", encoding="utf-8") as f:
        line = f"[{now()}] {msg}\n"
        sys.stdout.write(line)
        sys.stdout.flush()
        f.write(line)


def run(cmd: List[str], timeout: int = 20) -> int:
    log(f"$ {' '.join(cmd)} (timeout={timeout}s)")
    try:
        p = sp.run(cmd, cwd=str(ROOT), text=True, timeout=timeout, capture_output=True)
        if p.stdout:
            log(p.stdout.rstrip())
        if p.stderr:
            log(p.stderr.rstrip())
        log(f"rc={p.returncode}")
        return p.returncode
    except sp.TimeoutExpired:
        log(f"TIMEOUT after {timeout}s")
        return 124


class Step:
    def __init__(self, idx: int, name: str, fn: Callable[[], None], optional: bool = False):
        self.idx = idx
        self.name = name
        self.fn = fn
        self.optional = optional

    @property
    def sentinel(self) -> Path:
        return LEDGER / f"{self.idx:02d}_{self.name}.ok"

    def run(self) -> None:
        LEDGER.mkdir(parents=True, exist_ok=True)
        if self.sentinel.exists():
            log(f"SKIP step {self.idx:02d}:{self.name} (sentinel exists)")
            return
        log(f"BEGIN step {self.idx:02d}:{self.name}")
        try:
            self.fn()
            self.sentinel.write_text(now())
            log(f"DONE step {self.idx:02d}:{self.name}")
        except Exception as e:
            log(f"FAIL step {self.idx:02d}:{self.name}: {e}")
            raise


def plan_local() -> List[Step]:
    out_sql = ART / "generated_diff.sql"

    def s01_pytest():
        py = (ROOT / "venv" / "bin" / "python").resolve()
        py_cmd = str(py) if py.exists() else sys.executable
        rc = run([py_cmd, "-m", "pytest", "-q"])
        if rc != 0:
            raise RuntimeError(f"pytest failed rc={rc}")

    def s02_generate_sql():
        py = (ROOT / "venv" / "bin" / "python").resolve()
        py_cmd = str(py) if py.exists() else sys.executable
        rc = run([
            py_cmd,
            "-m",
            "checkatron.diffgen",
            "samples/example_before.csv",
            "samples/example_after.csv",
            "--keys",
            "samples/example_keys.csv",
            "--before_table",
            "before_table",
            "--after_table",
            "after_table",
            "--out",
            str(out_sql),
        ])
        if rc != 0:
            raise RuntimeError(f"sql generation failed rc={rc}")
        if not out_sql.exists():
            raise RuntimeError("generated SQL missing")

    def s03_sanity_check_sql():
        txt = out_sql.read_text(encoding="utf-8")
        must = [
            "CREATE OR REPLACE TABLE",
            "diff_result",
            "WITH\n",
        ]
        for m in must:
            if m not in txt:
                raise RuntimeError(f"expected token not found in sql: {m}")

    return [
        Step(1, "pytest", s01_pytest),
        Step(2, "generate_sql", s02_generate_sql),
        Step(3, "sanity_check_sql", s03_sanity_check_sql),
    ]


def _snowsql() -> Optional[str]:
    return shutil.which("snowsql")


def plan_snowflake() -> List[Step]:
    exe = _snowsql()
    profile = os.environ.get("SNOWSQL_PROFILE")
    out_sql = ART / "generated_diff.sql"

    def s01_probe():
        rc = run([sys.executable, "diagnostics/snowsql_probe.py", "--timeout", "5", "--log", str(ART / "snowsql_probe.log")], timeout=10)
        if rc != 0:
            raise RuntimeError("probe reported nonzero rc")

    def s02_setup_tables():
        if not exe:
            raise RuntimeError("snowsql missing")
        # Use TEMP tables; safe to rerun with CREATE OR REPLACE
        sql = (
            "CREATE OR REPLACE TEMPORARY TABLE before_table("
            "ACCOUNT_ID NUMBER, PORTFOLIO_NAME VARCHAR(50), VALUATION_DATE DATE, BALANCE NUMBER(15,2), STATUS VARCHAR(20));"
            "CREATE OR REPLACE TEMPORARY TABLE after_table("
            "ACCOUNT_ID NUMBER, PORTFOLIO_NAME VARCHAR(50), VALUATION_DATE DATE, BALANCE NUMBER(15,2), STATUS VARCHAR(20), NEW_COLUMN NUMBER(10,2));"
        )
        cmd = [exe]
        if profile:
            cmd += ["-c", profile]
        cmd += ["-q", sql]
        rc = run(cmd, timeout=20)
        if rc != 0:
            raise RuntimeError("table setup failed")

    def s03_load_data():
        if not exe:
            raise RuntimeError("snowsql missing")
        sql = (
            "INSERT INTO before_table VALUES"
            " (1001,'PORTFOLIO_A','2024-01-01',10000.00,'ACTIVE'),"
            " (1002,'PORTFOLIO_B','2024-01-01',25000.50,'ACTIVE'),"
            " (1003,'PORTFOLIO_A','2024-01-01',5000.75,'SUSPENDED'),"
            " (1004,'PORTFOLIO_C','2024-01-01',15000.25,'ACTIVE'),"
            " (1005,'PORTFOLIO_B','2024-01-01',30000.00,'ACTIVE');"
            "INSERT INTO after_table VALUES"
            " (1001,'PORTFOLIO_A','2024-01-01',10000.00,'ACTIVE',100.00),"
            " (1002,'PORTFOLIO_B','2024-01-01',25000.50,'ACTIVE',200.00),"
            " (1003,'PORTFOLIO_A','2024-01-01',5000.75,'ACTIVE',150.00),"
            " (1004,'PORTFOLIO_C','2024-01-01',15000.25,'ACTIVE',300.00),"
            " (1005,'PORTFOLIO_B','2024-01-01',35000.00,'ACTIVE',400.00),"
            " (1006,'PORTFOLIO_D','2024-01-01',7500.00,'ACTIVE',500.00);"
        )
        cmd = [exe]
        if profile:
            cmd += ["-c", profile]
        cmd += ["-q", sql]
        rc = run(cmd, timeout=30)
        if rc != 0:
            raise RuntimeError("data load failed")

    def s04_describe_to_csv():
        if not exe:
            raise RuntimeError("snowsql missing")
        before = ROOT / "samples/example_before.csv"
        after = ROOT / "samples/example_after.csv"
        # Use output_file option to write csv
        base = ["-o", "output_format=csv", "-o", "header=true"]
        cmd1 = [exe] + (["-c", profile] if profile else []) + base + ["-q", "DESCRIBE TABLE before_table"]
        cmd2 = [exe] + (["-c", profile] if profile else []) + base + ["-q", "DESCRIBE TABLE after_table"]
        # We can't direct output_file per command in all versions; as fallback, redirect stdout via shell is avoided here.
        # Instead, capture stdout and write files locally.
        rc = run(cmd1, timeout=20)
        if rc != 0:
            raise RuntimeError("describe before failed")
        # The run() already logged stdout; re‑run to capture programmatically
        p = sp.run(cmd1, cwd=str(ROOT), text=True, capture_output=True)
        before.write_text(p.stdout)
        rc = run(cmd2, timeout=20)
        if rc != 0:
            raise RuntimeError("describe after failed")
        p = sp.run(cmd2, cwd=str(ROOT), text=True, capture_output=True)
        after.write_text(p.stdout)

    def s05_generate_sql():
        rc = run([
            sys.executable,
            "-m",
            "checkatron.diffgen",
            "samples/example_before.csv",
            "samples/example_after.csv",
            "--keys",
            "samples/example_keys.csv",
            "--before_table",
            "before_table",
            "--after_table",
            "after_table",
            "--out",
            str(out_sql),
        ])
        if rc != 0:
            raise RuntimeError("sql generation failed")

    def s06_execute_sql():
        if not exe:
            raise RuntimeError("snowsql missing")
        cmd = [exe] + (["-c", profile] if profile else []) + ["-f", str(out_sql)]
        rc = run(cmd, timeout=60)
        if rc != 0:
            raise RuntimeError("executing generated sql failed")

    def s07_validate_queries():
        if not exe:
            raise RuntimeError("snowsql missing")
        sql = (
            "SELECT COUNT(*) total_rows,"
            " SUM(CASE WHEN _row_status = 0 THEN 1 ELSE 0 END) matching_rows,"
            " SUM(CASE WHEN _row_status > 0 THEN 1 ELSE 0 END) different_rows,"
            " SUM(CASE WHEN _row_status = 4 THEN 1 ELSE 0 END) missing_in_before,"
            " SUM(CASE WHEN _row_status = 5 THEN 1 ELSE 0 END) missing_in_after"
            " FROM diff_result;"
        )
        cmd = [exe] + (["-c", profile] if profile else []) + ["-o", "output_format=csv", "-q", sql]
        rc = run(cmd, timeout=30)
        if rc != 0:
            raise RuntimeError("validation query failed")

    return [
        Step(1, "probe", s01_probe),
        Step(2, "setup_tables", s02_setup_tables, optional=True),
        Step(3, "load_data", s03_load_data, optional=True),
        Step(4, "describe_to_csv", s04_describe_to_csv, optional=True),
        Step(5, "generate_sql", s05_generate_sql),
        Step(6, "execute_sql", s06_execute_sql, optional=True),
        Step(7, "validate_queries", s07_validate_queries, optional=True),
    ]


def archive_ledger() -> None:
    if not LEDGER.exists():
        log("No ledger to archive")
        return
    ts = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    dest = ART / f"ledger.{ts}.bak"
    shutil.move(str(LEDGER), str(dest))
    log(f"Archived ledger to {dest}")


def main(argv: List[str]) -> int:
    # Prefer project venv interpreter if present to ensure deps (duckdb, pytest) are available
    vpy = ROOT / "venv" / "bin" / "python"
    if vpy.exists() and Path(sys.executable).resolve() != vpy.resolve():
        # Re‑exec under venv python
        os.execv(str(vpy), [str(vpy), __file__] + argv)

    ap = argparse.ArgumentParser(description="Step ledger runner")
    ap.add_argument("--plan", choices=["local", "snowflake"], default="local")
    ap.add_argument("--reset", action="store_true", help="archive ledger then exit")
    args = ap.parse_args(argv)

    ART.mkdir(parents=True, exist_ok=True)
    LOG.touch(exist_ok=True)

    if args.reset:
        archive_ledger()
        return 0

    steps = plan_local() if args.plan == "local" else plan_snowflake()
    log(f"Running plan: {args.plan}")
    for step in steps:
        step.run()
    log("All steps complete")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
