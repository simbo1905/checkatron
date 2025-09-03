# Checkatron Samples

This folder contains example files and scripts to help you get started with Checkatron.

## 📁 Sample Files

### `example_before.csv`
A sample schema CSV representing the "before" state of a table. This mimics the output you'd get from running `DESCRIBE TABLE` in Snowflake.

**Columns:**
- `ACCOUNT_ID` (NUMBER) - Business identifier
- `PORTFOLIO_NAME` (VARCHAR) - Portfolio identifier  
- `VALUATION_DATE` (DATE) - Date of valuation
- `BALANCE` (NUMBER) - Account balance
- `STATUS` (VARCHAR) - Account status

### `example_after.csv`
A sample schema CSV representing the "after" state of a table. This example shows a table with an additional column.

**Columns:**
- All columns from `example_before.csv`
- `NEW_COLUMN` (NUMBER) - New column added to the table

### `example_keys.csv`
A CSV containing only the business key columns that should be used for matching rows between the two tables.

**Columns:**
- `ACCOUNT_ID` (NUMBER) - Primary business identifier
- `PORTFOLIO_NAME` (VARCHAR) - Secondary business identifier
- `VALUATION_DATE` (DATE) - Temporal business identifier

## 🚀 Running the Example

### Option 1: Use the Example Script

```bash
python samples/run_example.py
```

This will:
1. Generate a SQL diff script using the sample files
2. Save it as `example_diff.sql` in the samples folder
3. Show you a preview of the generated SQL
4. Explain the status codes and next steps

### Option 2: Use the Command Line

```bash
python -m checkatron.diffgen \
    samples/example_before.csv \
    samples/example_after.csv \
    --keys samples/example_keys.csv \
    --out samples/example_diff.sql
```

**💡 Pro Tip**: In PyCharm/VSCode, you can click the run button on these commands to execute them directly!

## 📊 Understanding the Output

The generated SQL will create a temporary table called `diff_result` with status codes for each column:

- **0**: Values match between tables
- **1**: Values are different between tables
- **2**: Column exists in after table but is NULL in before table
- **3**: Column exists in before table but is NULL in after table
- **4**: Row exists in after table but missing in before table
- **5**: Row exists in before table but missing in after table

## 🔧 Customizing the Examples

1. **Modify the schemas**: Edit the CSV files to match your actual table structures
2. **Change business keys**: Update `example_keys.csv` to include your actual key columns
3. **Add more columns**: Extend the schemas with additional columns you want to compare
4. **Test different scenarios**: Create variations to test different comparison scenarios

## 📝 Real-World Usage

1. **Export your schemas**: Use `DESCRIBE TABLE` in Snowflake and download as CSV
2. **Identify business keys**: Determine which columns uniquely identify your business records
3. **Generate SQL**: Use Checkatron to create comparison scripts
4. **Run in Snowflake**: Execute the generated SQL in your Snowflake environment
5. **Analyze results**: Download the results and filter in Excel to identify differences

## 🧪 Testing the Examples

You can also use these sample files to test the Checkatron functionality:

```bash
python -m pytest tests/ -v
```

The tests use similar sample data to verify the tool works correctly.

## 💡 Tips

- **Column names**: Make sure column names match exactly between your CSV files
- **Data types**: The tool uses data types to determine proper quoting in SQL
- **Key columns**: Choose business keys that are stable and unique
- **File paths**: Use absolute paths or relative paths from your working directory
