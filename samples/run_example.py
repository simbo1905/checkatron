#!/usr/bin/env python3
"""
Example script demonstrating how to use Checkatron.

This script shows how to generate SQL diff scripts using the sample CSV files.
Run this from the project root directory.
"""

import sys
from pathlib import Path

# Add the project root to the path so we can import checkatron
sys.path.insert(0, str(Path(__file__).parent.parent))

from checkatron import build_sql, parse_args


def main():
    """Run the example with sample files."""
    print("🔍 Checkatron Example - Generating SQL Diff Scripts")
    print("=" * 60)
    
    # Get the samples directory
    samples_dir = Path(__file__).parent
    project_root = samples_dir.parent
    
    # Define file paths
    before_csv = samples_dir / "example_before.csv"
    after_csv = samples_dir / "example_after.csv"
    keys_csv = samples_dir / "example_keys.csv"
    output_sql = samples_dir / "example_diff.sql"
    
    print(f"📁 Using sample files from: {samples_dir}")
    print(f"📊 Before schema: {before_csv.name}")
    print(f"📊 After schema: {after_csv.name}")
    print(f"🔑 Business keys: {keys_csv.name}")
    print(f"📝 Output SQL: {output_sql.name}")
    print()
    
    # Check if sample files exist
    if not all(f.exists() for f in [before_csv, after_csv, keys_csv]):
        print("❌ Error: Sample files not found!")
        print("Make sure you're running this from the project root directory.")
        return
    
    try:
        # Generate the SQL
        print("🔄 Generating SQL diff script...")
        args = parse_args([
            str(before_csv),
            str(after_csv),
            "--keys", str(keys_csv),
            "--out", str(output_sql)
        ])
        
        sql = build_sql(args)
        output_sql.write_text(sql)
        
        print("✅ SQL generated successfully!")
        print(f"📄 Output written to: {output_sql}")
        print()
        
        # Show a preview of the generated SQL
        print("📋 SQL Preview (first 10 lines):")
        print("-" * 40)
        lines = sql.split('\n')[:10]
        for i, line in enumerate(lines, 1):
            print(f"{i:2d}: {line}")
        print("...")
        print()
        
        # Show what the status codes mean
        print("📊 Status Code Reference:")
        print("-" * 40)
        print("0: Values match")
        print("1: Values are different")
        print("2: Column is NULL in before table only")
        print("3: Column is NULL in after table only")
        print("4: Row missing in before table")
        print("5: Row missing in after table")
        print()
        
        print("🎯 Next Steps:")
        print("1. Copy the generated SQL from the output file")
        print("2. Paste it into your Snowflake Web UI")
        print("3. Run the script to create the diff_result table")
        print("4. Download the results as CSV")
        print("5. Filter in Excel on any column > 0 to see differences")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        print("Make sure you have installed checkatron in development mode:")
        print("  pip install -e .")


if __name__ == "__main__":
    main()
