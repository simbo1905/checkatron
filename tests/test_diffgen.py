"""
Unit tests using DuckDB.
Simply run:  pytest
"""
import tempfile
from pathlib import Path

import duckdb
import pytest

from checkatron import build_sql, parse_args
import sys
import subprocess


def mk_csv(rows, tmp: Path, name: str) -> Path:
    p = tmp / name
    p.write_text("\n".join(rows))
    return p


def test_simple_same_table():
    """Two identical rows: per-column status 0; _row_status is NULL."""
    with tempfile.TemporaryDirectory() as td:
        t = Path(td)
        # describe-like csv
        schema = [
            "name,type,kind,null?,default,primary key,unique key,check,expression,comment,policy name,privacy domain",
            "k1,NUMBER,,,,,,,,,,",
            "val,VARCHAR,,,,,,,,,,",
        ]
        before_csv = mk_csv(schema, t, "before.csv")
        after_csv  = mk_csv(schema, t, "after.csv")
        keys_csv   = mk_csv([
            "name,type,kind,null?",
            "k1,NUMBER,,"
        ], t, "keys.csv")

        con = duckdb.connect(":memory:")
        con.execute("CREATE TABLE before_table(k1 INT, val VARCHAR)")
        con.execute("CREATE TABLE after_table(k1 INT, val VARCHAR)")
        con.execute("INSERT INTO before_table VALUES (1,'a')")
        con.execute("INSERT INTO after_table  VALUES (1,'a')")

        sql = build_sql(parse_args([
            str(before_csv),
            str(after_csv),
            "--keys", str(keys_csv),
            "--before_table", "before_table",
            "--after_table",  "after_table",
        ]))
        con.execute(sql)
        # Select only status columns present in diff_result (avoid relying on order)
        res = con.execute("SELECT val, _row_status FROM diff_result").fetchall()
        # expect (0, NULL): val matches, row present both sides
        assert res == [(0, None)]


def test_missing_column():
    """After table has an extra column; should appear as NULL in BEFORE."""
    with tempfile.TemporaryDirectory() as td:
        t = Path(td)
        before_schema = [
            "name,type,kind,null?",
            "k1,NUMBER,,",
            "val,VARCHAR,,",
        ]
        after_schema = [
            "name,type,kind,null?",
            "k1,NUMBER,,",
            "val,VARCHAR,,",
            "new_col,NUMBER,,",
        ]
        before_csv = mk_csv(before_schema, t, "before.csv")
        after_csv  = mk_csv(after_schema,  t, "after.csv")
        keys_csv   = mk_csv(["name,type", "k1,NUMBER"], t, "keys.csv")

        con = duckdb.connect(":memory:")
        con.execute("CREATE TABLE before_table(k1 INT, val VARCHAR)")
        con.execute("CREATE TABLE after_table(k1 INT, val VARCHAR, new_col INT)")
        con.execute("INSERT INTO before_table VALUES (1,'a')")
        con.execute("INSERT INTO after_table  VALUES (1,'a', 99)")

        sql = build_sql(parse_args([
            str(before_csv),
            str(after_csv),
            "--keys", str(keys_csv),
            "--before_table", "before_table",
            "--after_table",  "after_table",
        ]))
        con.execute(sql)
        res = con.execute("SELECT val, new_col, _row_status FROM diff_result").fetchall()
        # new_col should be 2 (null in before but not after); _row_status is NULL
        assert res == [(0, 2, None)]


def test_different_values():
    """Same row but different values should show status 1."""
    with tempfile.TemporaryDirectory() as td:
        t = Path(td)
        schema = [
            "name,type,kind,null?",
            "k1,NUMBER,,",
            "val,VARCHAR,,",
        ]
        before_csv = mk_csv(schema, t, "before.csv")
        after_csv  = mk_csv(schema, t, "after.csv")
        keys_csv   = mk_csv(["name,type", "k1,NUMBER"], t, "keys.csv")

        con = duckdb.connect(":memory:")
        con.execute("CREATE TABLE before_table(k1 INT, val VARCHAR)")
        con.execute("CREATE TABLE after_table(k1 INT, val VARCHAR)")
        con.execute("INSERT INTO before_table VALUES (1,'a')")
        con.execute("INSERT INTO after_table  VALUES (1,'b')")

        sql = build_sql(parse_args([
            str(before_csv),
            str(after_csv),
            "--keys", str(keys_csv),
            "--before_table", "before_table",
            "--after_table",  "after_table",
        ]))
        con.execute(sql)
        res = con.execute("SELECT val, _row_status FROM diff_result").fetchall()
        # val should be 1 (different values); _row_status is NULL
        assert res == [(1, None)]


def test_missing_row_before():
    """Row exists in after but not before should show status 4."""
    with tempfile.TemporaryDirectory() as td:
        t = Path(td)
        schema = [
            "name,type,kind,null?",
            "k1,NUMBER,,",
            "val,VARCHAR,,",
        ]
        before_csv = mk_csv(schema, t, "before.csv")
        after_csv  = mk_csv(schema, t, "after.csv")
        keys_csv   = mk_csv(["name,type", "k1,NUMBER"], t, "keys.csv")

        con = duckdb.connect(":memory:")
        con.execute("CREATE TABLE before_table(k1 INT, val VARCHAR)")
        con.execute("CREATE TABLE after_table(k1 INT, val VARCHAR)")
        con.execute("INSERT INTO after_table  VALUES (1,'a')")

        sql = build_sql(parse_args([
            str(before_csv),
            str(after_csv),
            "--keys", str(keys_csv),
            "--before_table", "before_table",
            "--after_table",  "after_table",
        ]))
        con.execute(sql)
        res = con.execute("SELECT val, _row_status FROM diff_result").fetchall()
        # row_status should be 4 (missing in before)
        assert res == [(2, 4)]


def test_multiple_key_columns():
    """Test with two key columns."""
    with tempfile.TemporaryDirectory() as td:
        t = Path(td)
        schema = [
            "name,type,kind,null?",
            "k1,NUMBER,,",
            "k2,VARCHAR,,",
            "val,NUMBER,,",
        ]
        before_csv = mk_csv(schema, t, "before.csv")
        after_csv  = mk_csv(schema, t, "after.csv")
        keys_csv   = mk_csv([
            "name,type,kind,null?",
            "k1,NUMBER,,",
            "k2,VARCHAR,,"
        ], t, "keys.csv")

        con = duckdb.connect(":memory:")
        con.execute("CREATE TABLE before_table(k1 INT, k2 VARCHAR, val INT)")
        con.execute("CREATE TABLE after_table(k1 INT, k2 VARCHAR, val INT)")
        con.execute("INSERT INTO before_table VALUES (1,'x',100)")
        con.execute("INSERT INTO after_table  VALUES (1,'x',100)")

        sql = build_sql(parse_args([
            str(before_csv),
            str(after_csv),
            "--keys", str(keys_csv),
            "--before_table", "before_table",
            "--after_table",  "after_table",
        ]))
        con.execute(sql)
        res = con.execute("SELECT val, _row_status FROM diff_result").fetchall()
        # val should be 0 (match), _row_status is NULL
        assert res == [(0, None)]


def test_single_line_stack_prepend(tmp_path: Path):
    """Generate single-line SQL and prepend to a stack file for batching."""
    # minimal describe-like CSVs
    before_schema = [
        "name,type,kind,null?",
        "k1,NUMBER,,",
        "val,VARCHAR,,",
    ]
    after_schema = [
        "name,type,kind,null?",
        "k1,NUMBER,,",
        "val,VARCHAR,,",
    ]
    keys_schema = ["name,type", "k1,NUMBER"]

    before_csv = mk_csv(before_schema, tmp_path, "before.csv")
    after_csv = mk_csv(after_schema, tmp_path, "after.csv")
    keys_csv = mk_csv(keys_schema, tmp_path, "keys.csv")

    out_sql = tmp_path / "out.sql"
    stack = tmp_path / "stack.input"
    stack.write_text("EXISTING;\n")

    # Call the module as a script to exercise --single_line and --stack_input
    cmd = [
        sys.executable,
        "-m",
        "checkatron.diffgen",
        str(before_csv),
        str(after_csv),
        "--keys",
        str(keys_csv),
        "--before_table",
        "B",
        "--after_table",
        "A",
        "--out",
        str(out_sql),
        "--single_line",
        "--stack_input",
        str(stack),
    ]
    r = subprocess.run(cmd, cwd=str(tmp_path), text=True)
    assert r.returncode == 0

    # Stack should now end with our single-line SQL; prior content remains at top
    lines = stack.read_text().splitlines()
    assert len(lines) >= 2
    last = lines[-1]
    assert "\n" not in last
    assert "--" not in last
    assert "CREATE OR REPLACE TABLE diff_result AS" in last
    assert lines[0] == "EXISTING;"
