#!/usr/bin/env python3
"""
Generate a brute-force SQL diff script for two Snowflake tables.

Usage
-----
# same table, two dates
$ python diffgen.py \
        prod_schema.my_table.csv \
        prod_schema.my_table.csv \
        --keys keys.csv \
        --before_where "HEADER_VALUATION_DATE = '2024-06-01'" \
        --after_where  "HEADER_VALUATION_DATE = '2024-06-02'"

# two different tables
$ python diffgen.py \
        prod_schema.table_a.csv \
        test_schema.table_b.csv \
        --keys keys.csv
"""
import argparse
import csv
import sys
from pathlib import Path
from typing import List, Dict

from jinja2 import Environment, FileSystemLoader, select_autoescape

# ------------------------------------------------------------------ helpers
def load_schema(csv_path: Path) -> List[Dict[str, str]]:
    """Read the output of Snowflake's 'DESCRIBE TABLE ...' CSV."""
    with csv_path.open(newline='') as f:
        reader = csv.DictReader(f)
        return [row for row in reader]


def infer_sql_type(col: Dict[str, str]) -> str:
    """
    Very small helper – just returns 'TEXT' or 'NUMBER'.
    We only need this for quoting literals correctly.
    """
    t = col["type"].upper()
    if "VARCHAR" in t or "STRING" in t or "TEXT" in t:
        return "TEXT"
    if "NUMBER" in t or "INT" in t or "FLOAT" in t or "DECIMAL" in t:
        return "NUMBER"
    return "TEXT"  # fallback


def parse_args(argv: List[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Generate brute-force SQL diff")
    p.add_argument("before_csv", type=Path, help="CSV from DESCRIBE TABLE (before)")
    p.add_argument("after_csv",  type=Path, help="CSV from DESCRIBE TABLE (after)")
    p.add_argument("--keys",     type=Path, required=True,
                   help="CSV with the same header as DESCRIBE but *only* the key cols")
    p.add_argument("--before_where", default="", help="Free-form WHERE clause (before)")
    p.add_argument("--after_where",  default="", help="Free-form WHERE clause (after)")
    p.add_argument("--before_table", help="Override DB.SCHEMA.TABLE (before)")
    p.add_argument("--after_table",  help="Override DB.SCHEMA.TABLE (after)")
    p.add_argument("--out", type=Path, default=Path("diff.sql"),
                   help="Output SQL file")
    return p.parse_args(argv)


# ------------------------------------------------------------------ main
def build_sql(args: argparse.Namespace) -> str:
    before_cols = load_schema(args.before_csv)
    after_cols  = load_schema(args.after_csv)
    key_cols    = [row["name"].upper() for row in load_schema(args.keys)]

    # Build union list of all columns, preserve order encountered
    before_names = [c["name"].upper() for c in before_cols]
    after_names = [c["name"].upper() for c in after_cols]
    all_names = before_names + \
                [c["name"].upper() for c in after_cols
                 if c["name"].upper() not in {c2["name"].upper() for c2 in before_cols}]
    # Build lookup of type
    type_map: Dict[str, str] = {c["name"].upper(): infer_sql_type(c)
                                for c in before_cols + after_cols}

    # Infer table names from file names if not overridden
    def table_name(csv_path: Path, override: str | None) -> str:
        if override:
            return override
        # strip .csv and replace _ with .
        stem = csv_path.stem.replace("_", ".")
        return stem

    before_table = table_name(args.before_csv, args.before_table)
    after_table  = table_name(args.after_csv,  args.after_table)

    j2 = Environment(
        loader=FileSystemLoader(Path(__file__).parent / "templates"),
        autoescape=select_autoescape(["sql.j2"])
    )
    tpl = j2.get_template("full_compare.sql.j2")
    return tpl.render(
        before_table=before_table,
        after_table=after_table,
        key_cols=key_cols,
        all_cols=all_names,
        before_cols=before_names,
        after_cols=after_names,
        type_map=type_map,
        before_where=args.before_where,
        after_where=args.after_where,
    )


def main():
    """Main entry point for the console script."""
    ns = parse_args(sys.argv[1:])
    sql = build_sql(ns)
    ns.out.write_text(sql)
    print(f"SQL written to {ns.out}")


if __name__ == "__main__":
    main()