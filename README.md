# Checkatron

A Python tool for generating brute-force SQL diff scripts to compare two database tables or datasets. Perfect for data validation, migration testing, and ensuring data consistency between production and test environments.

## Features

- **Schema-aware comparisons**: Automatically handles different column structures between tables
- **Flexible key matching**: Supports single or multiple business key columns with null-safe comparisons
- **Comprehensive diff reporting**: Generates status codes for each column and row-level differences
- **Snowflake/ANSI SQL compatible**: Generates standard SQL that works with Snowflake and other databases
- **DuckDB testing support**: Includes unit tests using DuckDB for validation

## Installation

1. Clone the repository:
```bash
git clone <your-repo-url
cd checkatron
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate
```

3. Install the package in development mode:
```bash
pip install -e .
```

**💡 Pro Tip**: In VSCode, you can click on any of these commands to run them directly in your terminal!



## Quick Start

**⚠️ Important**: Make sure you've activated your virtual environment first:

```bash
source venv/bin/activate
```

Want to see Checkatron in action? Try the included samples:

**Run the interactive example:**
```bash
python samples/run_example.py
```

**Or use the command line directly:**
```bash
python -m checkatron.diffgen \
    samples/example_before.csv \
    samples/example_after.csv \
    --keys samples/example_keys.csv \
    --out samples/example_diff.sql
```

**💡 Pro Tip**: In PyCharm/VSCode, you can click the run button on these commands to execute them directly!

See the `samples/` folder for example files and detailed usage instructions.

## 🎯 Complete Tutorial: Test in Snowflake

Want to test Checkatron with real Snowflake tables? Follow this step-by-step tutorial:

### Step 1: Create Tables in Snowflake
Copy and paste this into Snowflake:

```sql
-- Create the sample tables
CREATE OR REPLACE TEMPORARY TABLE before_table (
    ACCOUNT_ID NUMBER,
    PORTFOLIO_NAME VARCHAR(50),
    VALUATION_DATE DATE,
    BALANCE NUMBER(15,2),
    STATUS VARCHAR(20)
);

CREATE OR REPLACE TEMPORARY TABLE after_table (
    ACCOUNT_ID NUMBER,
    PORTFOLIO_NAME VARCHAR(50),
    VALUATION_DATE DATE,
    BALANCE NUMBER(15,2),
    STATUS VARCHAR(20),
    NEW_COLUMN NUMBER(10,2)
);
```

### Step 2: Load Test Data
Copy and paste this into Snowflake:

```sql
-- Load before table data
INSERT INTO before_table VALUES
    (1001, 'PORTFOLIO_A', '2024-01-01', 10000.00, 'ACTIVE'),
    (1002, 'PORTFOLIO_B', '2024-01-01', 25000.50, 'ACTIVE'),
    (1003, 'PORTFOLIO_A', '2024-01-01', 5000.75, 'SUSPENDED'),
    (1004, 'PORTFOLIO_C', '2024-01-01', 15000.25, 'ACTIVE'),
    (1005, 'PORTFOLIO_B', '2024-01-01', 30000.00, 'ACTIVE');

-- Load after table data (with differences)
INSERT INTO after_table VALUES
    (1001, 'PORTFOLIO_A', '2024-01-01', 10000.00, 'ACTIVE', 100.00),
    (1002, 'PORTFOLIO_B', '2024-01-01', 25000.50, 'ACTIVE', 200.00),
    (1003, 'PORTFOLIO_A', '2024-01-01', 5000.75, 'ACTIVE', 150.00),
    (1004, 'PORTFOLIO_C', '2024-01-01', 15000.25, 'ACTIVE', 300.00),
    (1005, 'PORTFOLIO_B', '2024-01-01', 35000.00, 'ACTIVE', 400.00),
    (1006, 'PORTFOLIO_D', '2024-01-01', 7500.00, 'ACTIVE', 500.00);
```

### Step 3: Verify the Data
Copy and paste this into Snowflake:

```sql
-- Check row counts
SELECT 'BEFORE TABLE' as table_name, COUNT(*) as row_count FROM before_table
UNION ALL
SELECT 'AFTER TABLE' as table_name, COUNT(*) as row_count FROM after_table;

-- Show sample data
SELECT 'BEFORE' as source, * FROM before_table ORDER BY ACCOUNT_ID
UNION ALL
SELECT 'AFTER' as source, * FROM after_table ORDER BY ACCOUNT_ID;
```

### Step 4: Export Table Schemas
Now export the table schemas to create your CSV files:

1. **Export before_table schema:**
   ```sql
   DESCRIBE TABLE before_table;
   ```
   - Click "Download" in Snowflake
   - Save as `samples/example_before.csv`

2. **Export after_table schema:**
   ```sql
   DESCRIBE TABLE after_table;
   ```
   - Click "Download" in Snowflake  
   - Save as `samples/example_after.csv`

3. **Create business keys file:**
   - Copy `samples/example_before.csv`
   - Remove all rows except ACCOUNT_ID, PORTFOLIO_NAME, VALUATION_DATE
   - Save as `samples/example_keys.csv`

### Step 5: Generate the Diff SQL
Now use checkatron to generate the comparison SQL:

```bash
python -m checkatron.diffgen \
    samples/example_before.csv \
    samples/example_after.csv \
    --keys samples/example_keys.csv \
    --out samples/generated_diff.sql
```

### Step 6: Run the Generated Diff SQL
Copy the contents of `samples/generated_diff.sql` and paste it into Snowflake.

### Step 7: Analyze the Results
Copy and paste this into Snowflake:

```sql
-- Summary of differences
SELECT 
    COUNT(*) as total_rows,
    SUM(CASE WHEN _row_status = 0 THEN 1 ELSE 0 END) as matching_rows,
    SUM(CASE WHEN _row_status > 0 THEN 1 ELSE 0 END) as different_rows,
    SUM(CASE WHEN _row_status = 4 THEN 1 ELSE 0 END) as missing_in_before,
    SUM(CASE WHEN _row_status = 5 THEN 1 ELSE 0 END) as missing_in_after
FROM diff_result;

-- Show rows with differences
SELECT * FROM diff_result WHERE _row_status > 0;
```

### Expected Results:
- **6 total rows** (5 from before + 1 new in after)
- **2 rows with differences** (1003: status changed, 1005: balance changed)  
- **1 new row** (1006: missing in before table)
- **NEW_COLUMN** showing status 2 for all rows (NULL in before only)

### Download for Excel Analysis:
```sql
SELECT * FROM diff_result;
```
Then click "Download" in Snowflake and filter on any column > 0 to see differences.

## Usage

### Basic Usage

Generate a SQL diff script comparing two tables:

```bash
python -m checkatron.diffgen \
    before_schema.csv \
    after_schema.csv \
    --keys business_keys.csv \
    --out diff_script.sql
```

### Command Line Options

- `before_csv`: CSV file from `DESCRIBE TABLE` command (before state)
- `after_csv`: CSV file from `DESCRIBE TABLE` command (after state)
- `--keys`: CSV file containing only the business key columns
- `--before_where`: Optional WHERE clause for filtering before table
- `--after_where`: Optional WHERE clause for filtering after table
- `--before_table`: Override table name for before table
- `--after_table`: Override table name for after table
- `--out`: Output SQL file (default: diff.sql)

### Input CSV Format

The tool expects CSV files in the format produced by Snowflake's `DESCRIBE TABLE` command:

```csv
name,type,kind,null?,default,primary key,unique key,check,expression,comment,policy name,privacy domain
ACCOUNT_ID,NUMBER,,,,,,,,,,
PORTFOLIO_NAME,VARCHAR,,,,,,,,,,
VALUATION_DATE,DATE,,,,,,,,,,
BALANCE,NUMBER,,,,,,,,,,
```

### Business Keys CSV

Create a CSV with the same header but only the columns that serve as business keys:

```csv
name,type,kind,null?,default,primary key,unique key,check,expression,comment,policy name,privacy domain
ACCOUNT_ID,NUMBER,,,,,,,,,,
PORTFOLIO_NAME,VARCHAR,,,,,,,,,,
VALUATION_DATE,DATE,,,,,,,,,,
```

### Generated SQL Output

The tool generates a temporary table with status codes for each column:

- **0**: Values match
- **1**: Values are different
- **2**: Column is NULL in before table only
- **3**: Column is NULL in after table only
- **4**: Row missing in before table
- **5**: Row missing in after table

### Example Use Cases

#### 1. Compare Production vs Test Tables

```bash
python -m checkatron.diffgen \
    prod_schema.my_table.csv \
    test_schema.my_table.csv \
    --keys business_keys.csv \
    --out prod_vs_test_diff.sql
```

#### 2. Compare Same Table at Different Dates

```bash
python -m checkatron.diffgen \
    my_table_2024_01_01.csv \
    my_table_2024_01_02.csv \
    --keys business_keys.csv \
    --before_where "VALUATION_DATE = '2024-01-01'" \
    --after_where "VALUATION_DATE = '2024-01-02'" \
    --out daily_diff.sql
```

#### 3. Override Table Names

```bash
python -m checkatron.diffgen \
    schema_a.csv \
    schema_b.csv \
    --keys business_keys.csv \
    --before_table "PROD.SCHEMA_A.TABLE_X" \
    --after_table "TEST.SCHEMA_B.TABLE_Y" \
    --out custom_names_diff.sql
```

## Development

### Running Tests

```bash
# Run all tests
python -m pytest tests/ -v

# Run specific test
python -m pytest tests/test_diffgen.py::test_simple_same_table -v
```

### Project Structure

```
checkatron/
├── __init__.py          # Package initialization
├── diffgen.py           # Main SQL generation logic
└── templates/           # Jinja2 SQL templates
    └── full_compare.sql.j2

samples/                 # Example files and scripts
├── README.md            # Samples documentation
├── example_before.csv   # Sample before schema
├── example_after.csv    # Sample after schema
├── example_keys.csv     # Sample business keys
└── run_example.py       # Interactive example script

tests/
├── __init__.py
└── test_diffgen.py      # Unit tests using DuckDB

setup.py                 # Package configuration
requirements.txt         # Dependencies
```

### Adding New Features

1. **New SQL Templates**: Add Jinja2 templates in the `templates/` directory
2. **Additional Options**: Extend the argument parser in `diffgen.py`
3. **New Test Cases**: Add tests in `tests/test_diffgen.py`

## Dependencies

- **Jinja2**: Template engine for SQL generation
- **pytest**: Testing framework
- **duckdb**: In-memory database for testing

## Troubleshooting

### Common Issues

**"No module named 'checkatron'"**
```bash
# Make sure you've activated the virtual environment and installed the package
source venv/bin/activate && pip install -e .
```

**"Permission denied" on venv creation**
```bash
# Try using python3 explicitly
python3 -m venv venv
```

**"Command not found: python"**
```bash
# On macOS/Linux, try python3
python3 -m venv venv
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

## License

[Your License Here]

## Support

For issues and questions, please open an issue on GitHub.