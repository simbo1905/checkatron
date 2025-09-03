-- =====================================================
-- Checkatron Sample Tables Setup for Snowflake
-- =====================================================
-- This script creates the sample tables and loads test data
-- to demonstrate the diff functionality

-- =====================================================
-- 1. CREATE SAMPLE TABLES
-- =====================================================

-- Before table (original schema)
CREATE OR REPLACE TEMPORARY TABLE before_table (
    ACCOUNT_ID NUMBER,
    PORTFOLIO_NAME VARCHAR(50),
    VALUATION_DATE DATE,
    BALANCE NUMBER(15,2),
    STATUS VARCHAR(20)
);

-- After table (new schema with extra column)
CREATE OR REPLACE TEMPORARY TABLE after_table (
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
    (1005, 'PORTFOLIO_B', '202401-01', 30000.00, 'ACTIVE');

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

-- Show before table data
SELECT 'BEFORE TABLE' as table_name, COUNT(*) as row_count FROM before_table
UNION ALL
SELECT 'AFTER TABLE' as table_name, COUNT(*) as row_count FROM after_table;

-- Show sample data from both tables
SELECT 'BEFORE' as source, * FROM before_table ORDER BY ACCOUNT_ID
UNION ALL
SELECT 'AFTER' as source, * FROM after_table ORDER BY ACCOUNT_ID;

-- =====================================================
-- 4. CREATE THE DIFF RESULT TABLE USING CHECKATRON
-- =====================================================
-- After running the checkatron tool, this will create diff_result table
-- with status codes showing all the differences

-- =====================================================
-- 5. ANALYZE THE RESULTS
-- =====================================================
-- Once diff_result is created, you can run these queries:

/*
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
*/

-- =====================================================
-- 6. EXPECTED DIFF RESULTS
-- =====================================================
/*
Expected results from the diff:

ACCOUNT_ID 1001: All columns = 0 (match), _row_status = 0 (both sides)
ACCOUNT_ID 1002: All columns = 0 (match), _row_status = 0 (both sides)  
ACCOUNT_ID 1003: STATUS = 1 (different: SUSPENDED vs ACTIVE), _row_status = 0 (both sides)
ACCOUNT_ID 1004: All columns = 0 (match), _row_status = 0 (both sides)
ACCOUNT_ID 1005: BALANCE = 1 (different: 30000 vs 35000), _row_status = 0 (both sides)
ACCOUNT_ID 1006: All columns = 2 (NULL in BEFORE only), _row_status = 4 (missing in BEFORE)

NEW_COLUMN will show:
- 1001-1005: Status 2 (NULL in BEFORE only, since column didn't exist)
- 1006: Status 2 (NULL in BEFORE only)
*/
