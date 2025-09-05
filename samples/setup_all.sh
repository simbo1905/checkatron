#!/bin/bash

# =====================================================
# Checkatron Complete Setup and Test Script
# =====================================================
# This script sets up everything needed to test checkatron
# with real Snowflake tables and data

set -e  # Exit on any error

echo "🔍 Checkatron Complete Setup and Test"
echo "======================================"

# =====================================================
# 1. CHECK PREREQUISITES
# =====================================================

echo "📋 Checking prerequisites..."

# Check if we're in the right directory
if [ ! -f "setup.py" ]; then
    echo "❌ Error: Please run this script from the checkatron project root directory"
    exit 1
fi

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "❌ Error: Virtual environment not found. Please run the installation steps first:"
    echo "   python -m venv venv"
    echo "   source venv/bin/activate"
    echo "   pip install -e ."
    exit 1
fi

# Check if virtual environment is activated
if [ -z "$VIRTUAL_ENV" ]; then
    echo "⚠️  Virtual environment not activated. Activating now..."
    source venv/bin/activate
fi

echo "✅ Prerequisites check passed"

# =====================================================
# 2. GENERATE THE DIFF SQL
# =====================================================

echo ""
echo "🔄 Generating diff SQL using checkatron..."

# Generate the SQL diff script
python -m checkatron.diffgen \
    samples/example_before.csv \
    samples/example_after.csv \
    --keys samples/example_keys.csv \
    --out samples/generated_diff.sql

if [ $? -eq 0 ]; then
    echo "✅ SQL diff script generated successfully"
    echo "📄 Output: samples/generated_diff.sql"
else
    echo "❌ Failed to generate SQL diff script"
    exit 1
fi

# =====================================================
# 3. CREATE SNOWFLAKE SETUP SCRIPT
# =====================================================

echo ""
echo "📝 Creating Snowflake setup script..."

# Create a combined script that includes both setup and diff
cat > samples/complete_snowflake_test.sql << 'EOF'
-- =====================================================
-- Checkatron Complete Test Script for Snowflake
-- =====================================================
-- Run this entire script in Snowflake to test checkatron

-- =====================================================
-- 1. CREATE SAMPLE TABLES
-- =====================================================

-- Before table (original schema)
CREATE OR REPLACE TABLE before_table (
    ACCOUNT_ID NUMBER,
    PORTFOLIO_NAME VARCHAR(50),
    VALUATION_DATE DATE,
    BALANCE NUMBER(15,2),
    STATUS VARCHAR(20)
);

-- After table (new schema with extra column)
CREATE OR REPLACE TABLE after_table (
    ACCOUNT_ID NUMBER,
    PORTFOLIO_NAME VARCHAR(50),
    VALUATION_DATE DATE,
    BALANCE NUMBER(15,2),
    STATUS VARCHAR(20),
    NEW_COLUMN NUMBER(10,2)
);

-- =====================================================
-- 2. LOAD TEST DATA
-- =====================================================

-- Insert data into before_table
INSERT INTO before_table VALUES
    (1001, 'PORTFOLIO_A', '2024-01-01', 10000.00, 'ACTIVE'),
    (1002, 'PORTFOLIO_B', '2024-01-01', 25000.50, 'ACTIVE'),
    (1003, 'PORTFOLIO_A', '2024-01-01', 5000.75, 'SUSPENDED'),
    (1004, 'PORTFOLIO_C', '2024-01-01', 15000.25, 'ACTIVE'),
    (1005, 'PORTFOLIO_B', '2024-01-01', 30000.00, 'ACTIVE');

-- Insert data into after_table (with some differences)
INSERT INTO after_table VALUES
    (1001, 'PORTFOLIO_A', '2024-01-01', 10000.00, 'ACTIVE', 100.00),      -- Same values, new column
    (1002, 'PORTFOLIO_B', '2024-01-01', 25000.50, 'ACTIVE', 200.00),      -- Same values, new column
    (1003, 'PORTFOLIO_A', '2024-01-01', 5000.75, 'ACTIVE', 150.00),      -- Status changed from SUSPENDED to ACTIVE
    (1004, 'PORTFOLIO_C', '2024-01-01', 15000.25, 'ACTIVE', 300.00),      -- Same values, new column
    (1005, 'PORTFOLIO_B', '2024-01-01', 35000.00, 'ACTIVE', 400.00),      -- Balance changed from 30000 to 35000
    (1006, 'PORTFOLIO_D', '2024-01-01', 7500.00, 'ACTIVE', 500.00);       -- New row (missing in before)

-- =====================================================
-- 3. VERIFY THE DATA
-- =====================================================

-- Show row counts
SELECT 'BEFORE TABLE' as table_name, COUNT(*) as row_count FROM before_table
UNION ALL
SELECT 'AFTER TABLE' as table_name, COUNT(*) as row_count FROM after_table;

-- Show sample data
SELECT 'BEFORE' as source, * FROM before_table ORDER BY ACCOUNT_ID
UNION ALL
SELECT 'AFTER' as source, * FROM after_table ORDER BY ACCOUNT_ID;

-- =====================================================
-- 4. RUN THE GENERATED DIFF SQL
-- =====================================================
-- Copy and paste the contents of samples/generated_diff.sql here
-- This will create the diff_result table

-- =====================================================
-- 5. ANALYZE THE RESULTS
-- =====================================================

-- Summary of all differences
SELECT 
    COUNT(*) as total_rows,
    SUM(CASE WHEN _row_status = 0 THEN 1 ELSE 0 END) as matching_rows,
    SUM(CASE WHEN _row_status > 0 THEN 1 ELSE 0 END) as different_rows,
    SUM(CASE WHEN _row_status = 4 THEN 1 ELSE 0 END) as missing_in_before,
    SUM(CASE WHEN _row_status = 5 THEN 1 ELSE 0 END) as missing_in_after
FROM diff_result;

-- Show rows with differences
SELECT * FROM diff_result WHERE _row_status > 0;

-- Show specific column differences
SELECT 
    ACCOUNT_ID,
    PORTFOLIO_NAME,
    VALUATION_DATE,
    CASE 
        WHEN BALANCE > 0 THEN 'DIFFERENT'
        WHEN BALANCE = 0 THEN 'MATCH'
        WHEN BALANCE = 2 THEN 'NULL in BEFORE only'
        WHEN BALANCE = 3 THEN 'NULL in AFTER only'
        ELSE 'UNKNOWN'
    END as balance_status,
    CASE 
        WHEN STATUS > 0 THEN 'DIFFERENT'
        WHEN STATUS = 0 THEN 'MATCH'
        WHEN STATUS = 2 THEN 'NULL in BEFORE only'
        WHEN STATUS = 3 THEN 'NULL in AFTER only'
        ELSE 'UNKNOWN'
    END as status_status,
    CASE 
        WHEN NEW_COLUMN > 0 THEN 'DIFFERENT'
        WHEN NEW_COLUMN = 0 THEN 'MATCH'
        WHEN NEW_COLUMN = 2 THEN 'NULL in BEFORE only'
        WHEN NEW_COLUMN = 3 THEN 'NULL in AFTER only'
        ELSE 'UNKNOWN'
    END as new_column_status,
    _row_status
FROM diff_result
ORDER BY ACCOUNT_ID;
EOF

echo "✅ Complete Snowflake test script created"
echo "📄 Output: samples/complete_snowflake_test.sql"

# =====================================================
# 4. CREATE INSTRUCTIONS
# =====================================================

echo ""
echo "📋 Creating step-by-step instructions..."

cat > samples/SNOWFLAKE_TEST_INSTRUCTIONS.md << 'EOF'
# Snowflake Test Instructions

## 🚀 Quick Test Setup

1. **Run the setup script** (you just did this):
   ```bash
   ./samples/setup_all.sh
   ```

2. **Open Snowflake Web UI** and navigate to your worksheet

3. **Copy the complete test script**:
   - Open `samples/complete_snowflake_test.sql`
   - Copy the entire contents

4. **Paste into Snowflake** and run the first 3 sections:
   - Creates the sample tables
   - Loads test data
   - Shows verification queries

5. **Copy the generated diff SQL**:
   - Open `samples/generated_diff.sql`
   - Copy the entire contents

6. **Paste into Snowflake** (after the verification queries) and run it

7. **Run the analysis queries** to see the diff results

## 📊 Expected Results

The diff should show:
- **6 total rows** (5 from before + 1 new in after)
- **2 rows with differences** (1003: status changed, 1005: balance changed)
- **1 new row** (1006: missing in before table)
- **NEW_COLUMN** showing status 2 for all rows (NULL in before only)

## 🔍 Understanding Status Codes

- **0**: Values match
- **1**: Values are different
- **2**: Column is NULL in before table only
- **3**: Column is NULL in after table only
- **4**: Row missing in before table
- **5**: Row missing in after table

## 📥 Download Results

After running the diff, you can:
1. Run `SELECT * FROM diff_result`
2. Click "Download" in Snowflake
3. Open in Excel and filter on any column > 0 to see differences
EOF

echo "✅ Instructions created"
echo "📄 Output: samples/SNOWFLAKE_TEST_INSTRUCTIONS.md"

# =====================================================
# 5. SUMMARY
# =====================================================

echo ""
echo "🎉 Setup Complete!"
echo "=================="
echo ""
echo "📁 Generated files:"
echo "   • samples/generated_diff.sql          - The diff SQL from checkatron"
echo "   • samples/complete_snowflake_test.sql - Complete Snowflake test script"
echo "   • samples/SNOWFLAKE_TEST_INSTRUCTIONS.md - Step-by-step instructions"
echo ""
echo "🚀 Next steps:"
echo "   1. Open samples/SNOWFLAKE_TEST_INSTRUCTIONS.md for detailed steps"
echo "   2. Copy samples/complete_snowflake_test.sql to Snowflake"
echo "   3. Run the setup and data loading sections"
echo "   4. Copy samples/generated_diff.sql to Snowflake and run it"
echo "   5. Analyze the results with the provided queries"
echo ""
echo "💡 The test data includes:"
echo "   • Matching rows (should show status 0)"
echo "   • Changed values (should show status 1)"
echo "   • New columns (should show status 2)"
echo "   • Missing rows (should show status 4)"
echo ""
echo "Happy testing! 🎯"
