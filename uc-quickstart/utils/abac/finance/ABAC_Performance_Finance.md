# ⚠️ ABAC Performance Anti-Patterns: Finance Domain

## 🎯 Critical Performance Guidelines for Financial Services ABAC

### 🚨 The Financial Services Performance Reality

**Financial services operates at millisecond scale.** Trading systems process thousands of transactions per second. A slow ABAC policy can cost millions in lost trading opportunities or cause audit queries to timeout. Poor function design turns compliance from enabler to bottleneck.

> **Key Principle**: ABAC policies run on EVERY query execution. In high-frequency trading environments, even 1ms of overhead multiplied by millions of queries becomes unacceptable.

---

## 🔴 FINANCE-SPECIFIC ANTI-PATTERNS

### ❌ Anti-Pattern #1: Real-Time Trading Position Calculations

**What NOT to Do:**
```sql
-- NEVER DO THIS - Complex P&L calculation in mask function
CREATE OR REPLACE FUNCTION mask_pnl_with_realtime_calc(
    position_id STRING,
    entry_price DECIMAL,
    quantity INT
)
RETURNS DECIMAL
DETERMINISTIC
RETURN 
  CASE 
    WHEN user_role = 'TRADER' THEN 
        (SELECT current_price FROM market_data.live_prices WHERE symbol = 
            (SELECT security_id FROM positions WHERE position_id = position_id)
        ) * quantity - (entry_price * quantity)
    ELSE NULL
  END;
```

**Why This Destroys Performance:**
- External market data lookup for every row
- Nested subquery for security lookup
- Calculations repeated for every masked value
- No caching possible
- Blocks query optimization

**Performance Impact:** 🔥 **10,000x+ slower** (External data fetch per row)

**Correct Approach:**
```sql
-- ✅ GOOD - Mask the stored P&L value, don't recalculate it
CREATE OR REPLACE FUNCTION mask_pnl_stored(pnl_value DECIMAL)
RETURNS DECIMAL
DETERMINISTIC
RETURN 
  CASE 
    WHEN pnl_value IS NULL THEN NULL
    ELSE ROUND(pnl_value, -2)  -- Round to nearest 100 for restricted roles
  END;
```

---

### ❌ Anti-Pattern #2: Customer Credit Score Lookups

**What NOT to Do:**
```sql
-- NEVER DO THIS - Credit bureau lookup in filter function
CREATE OR REPLACE FUNCTION filter_by_creditworthiness(customer_id STRING)
RETURNS BOOLEAN
DETERMINISTIC
RETURN 
  (
    SELECT credit_score 
    FROM external_credit_bureau.scores 
    WHERE customer_id = customer_id 
      AND score_date = CURRENT_DATE()
  ) >= 650;
```

**Why This Kills Performance:**
- External credit bureau API call per row
- Network latency multiplied by row count
- Expensive third-party API costs
- Single point of failure
- No result caching

**Performance Impact:** 🔥 **100,000x slower** + **$$$$ API costs**

**Correct Approach:**
```sql
-- ✅ GOOD - Filter based on stored risk score column
CREATE OR REPLACE FUNCTION filter_by_risk_score(
    customer_risk_score INT,
    required_score INT
)
RETURNS BOOLEAN
DETERMINISTIC
RETURN customer_risk_score >= required_score;

-- Pre-compute and store credit scores in your database
-- Use batch ETL to refresh from credit bureau daily, not per-query
```

---

### ❌ Anti-Pattern #3: AML Transaction Pattern Analysis

**What NOT to Do:**
```sql
-- NEVER DO THIS - Complex AML pattern detection in row filter
CREATE OR REPLACE FUNCTION filter_suspicious_transactions(
    customer_id STRING,
    transaction_id STRING,
    amount DECIMAL
)
RETURNS BOOLEAN
DETERMINISTIC
RETURN 
  CASE 
    -- Check for structuring (multiple transactions under $10k)
    WHEN (
      SELECT COUNT(*) 
      FROM transactions 
      WHERE customer_id = customer_id 
        AND transaction_date = CURRENT_DATE()
        AND amount < 10000
    ) > 3 THEN FALSE
    -- Check for rapid movement across borders
    WHEN (
      SELECT COUNT(DISTINCT country_code)
      FROM transactions
      WHERE customer_id = customer_id
        AND transaction_date >= CURRENT_DATE() - INTERVAL 7 DAYS
    ) > 5 THEN FALSE
    ELSE TRUE
  END;
```

**Why This Breaks Everything:**
- Multiple complex subqueries per row
- Correlated subqueries prevent parallelization
- Date range queries per transaction
- Cartesian product explosion risk
- Impossible to optimize

**Performance Impact:** 🔥 **50,000x slower** (Multiple subqueries per row)

**Correct Approach:**
```sql
-- ✅ GOOD - Filter based on pre-computed AML flag column
CREATE OR REPLACE FUNCTION filter_by_aml_flag(
    aml_flag_level STRING,
    user_clearance STRING
)
RETURNS BOOLEAN
DETERMINISTIC
RETURN 
  CASE 
    WHEN aml_flag_level = 'NONE' THEN TRUE
    WHEN aml_flag_level = 'LOW' AND user_clearance IN ('ANALYST', 'SENIOR', 'OFFICER') THEN TRUE
    WHEN aml_flag_level = 'HIGH' AND user_clearance IN ('SENIOR', 'OFFICER') THEN TRUE
    ELSE FALSE
  END;

-- Run AML pattern detection as separate batch job
-- Store results in aml_flag_level column
-- ABAC policies filter based on stored flags, not live analysis
```

---

### ❌ Anti-Pattern #4: Card BIN Lookup for Issuer Information

**What NOT to Do:**
```sql
-- NEVER DO THIS - BIN database lookup in mask function
CREATE OR REPLACE FUNCTION mask_card_with_issuer(card_number STRING)
RETURNS STRING
DETERMINISTIC
RETURN 
  CASE 
    WHEN (
      SELECT issuer_name 
      FROM card_bin_database.issuers 
      WHERE bin = SUBSTRING(card_number, 1, 6)
    ) IN ('Visa', 'Mastercard') THEN CONCAT('XXXX-XXXX-XXXX-', RIGHT(card_number, 4))
    ELSE 'XXXX-XXXX-XXXX-XXXX'
  END;
```

**Why This Kills Performance:**
- BIN lookup for every card number
- Database JOIN per row
- External table dependency
- Prevents column pruning

**Performance Impact:** 🔥 **1,000x slower** (Lookup per masked value)

**Correct Approach:**
```sql
-- ✅ GOOD - Mask based on stored card type column
CREATE OR REPLACE FUNCTION mask_card_by_type(
    card_number STRING,
    card_type STRING,
    user_clearance STRING
)
RETURNS STRING
DETERMINISTIC
RETURN 
  CASE 
    WHEN user_clearance = 'FULL' THEN card_number
    WHEN user_clearance = 'BASIC' AND card_type IS NOT NULL 
        THEN CONCAT('XXXX-XXXX-XXXX-', RIGHT(card_number, 4))
    ELSE 'XXXX-XXXX-XXXX-XXXX'
  END;

-- Store card_type when card is added to database
-- No runtime lookups needed
```

---

### ❌ Anti-Pattern #5: Exchange Rate Conversions in Amount Masking

**What NOT to Do:**
```sql
-- NEVER DO THIS - Currency conversion in mask function
CREATE OR REPLACE FUNCTION mask_amount_usd_converted(
    amount DECIMAL,
    currency STRING
)
RETURNS DECIMAL
DETERMINISTIC
RETURN 
  CASE 
    WHEN currency = 'USD' THEN ROUND(amount, -2)
    ELSE ROUND(
        amount * (
            SELECT rate 
            FROM forex.exchange_rates 
            WHERE from_currency = currency 
              AND to_currency = 'USD' 
              AND rate_date = CURRENT_DATE()
        ), 
        -2
    )
  END;
```

**Why This Destroys Performance:**
- Forex rate lookup per transaction
- Date-based queries per row
- External table dependency
- No rate caching

**Performance Impact:** 🔥 **5,000x slower** (Forex lookup per amount)

**Correct Approach:**
```sql
-- ✅ GOOD - Mask the stored amount in original currency
CREATE OR REPLACE FUNCTION mask_amount_rounded(
    amount DECIMAL,
    sensitivity_level STRING
)
RETURNS DECIMAL
DETERMINISTIC
RETURN 
  CASE 
    WHEN sensitivity_level = 'PUBLIC' THEN amount
    WHEN amount < 100 THEN ROUND(amount, -1)
    ELSE ROUND(amount, -2)
  END;

-- Pre-convert amounts to USD in ETL if needed
-- Store both original and USD amounts as columns
-- Mask the stored values, don't convert at query time
```

---

### ❌ Anti-Pattern #6: Account Balance Aggregation in Filter

**What NOT to Do:**
```sql
-- NEVER DO THIS - Account rollup in row filter
CREATE OR REPLACE FUNCTION filter_high_value_customers(customer_id STRING)
RETURNS BOOLEAN
DETERMINISTIC
RETURN 
  (
    SELECT SUM(balance) 
    FROM accounts 
    WHERE customer_id = customer_id
      AND account_status = 'Active'
  ) >= 100000;
```

**Why This Kills Performance:**
- Aggregation query per customer row
- Cross-table dependency
- Prevents parallel processing
- No optimization possible

**Performance Impact:** 🔥 **10,000x slower** (Aggregation per row)

**Correct Approach:**
```sql
-- ✅ GOOD - Filter based on pre-computed customer tier
CREATE OR REPLACE FUNCTION filter_by_customer_tier(
    customer_tier STRING,
    required_tier STRING
)
RETURNS BOOLEAN
DETERMINISTIC
RETURN 
  CASE 
    WHEN customer_tier = 'PLATINUM' THEN TRUE
    WHEN customer_tier = 'GOLD' AND required_tier IN ('GOLD', 'SILVER', 'BRONZE') THEN TRUE
    WHEN customer_tier = 'SILVER' AND required_tier IN ('SILVER', 'BRONZE') THEN TRUE
    WHEN customer_tier = 'BRONZE' AND required_tier = 'BRONZE' THEN TRUE
    ELSE FALSE
  END;

-- Compute customer tiers in batch ETL
-- Store as customer_tier column
-- Update nightly or as accounts change
```

---

## ✅ FINANCE-OPTIMIZED PATTERNS

### 🚀 High-Performance Trading Position Filter

```sql
-- ✅ EXCELLENT - Pure column-based trading desk filtering
CREATE OR REPLACE FUNCTION filter_trading_desk_access(
    position_desk STRING,
    information_barrier STRING,
    user_desk STRING,
    user_barrier STRING
)
RETURNS BOOLEAN
DETERMINISTIC
RETURN 
  CASE 
    -- Neutral roles (Risk, Compliance) see everything
    WHEN user_barrier = 'Neutral' THEN TRUE
    
    -- Same desk access
    WHEN position_desk = user_desk AND information_barrier = user_barrier THEN TRUE
    
    -- Block cross-barrier access (Chinese wall)
    WHEN information_barrier != user_barrier THEN FALSE
    
    ELSE FALSE
  END;
```

**Why This Works:**
- Pure column comparisons - no lookups
- No external dependencies
- Fully optimizable by Spark
- Vectorizes efficiently
- Enables predicate pushdown

**Performance Impact:** ✅ **Native speed** (< 1ms overhead)

---

### 🚀 High-Performance PCI-DSS Card Masking

```sql
-- ✅ EXCELLENT - Simple string operations for card masking
CREATE OR REPLACE FUNCTION mask_card_pci(
    card_number STRING,
    pci_clearance STRING
)
RETURNS STRING
DETERMINISTIC
RETURN 
  CASE 
    WHEN pci_clearance = 'FULL' THEN card_number
    WHEN pci_clearance = 'BASIC' THEN 
        CONCAT('XXXX-XXXX-XXXX-', RIGHT(REGEXP_REPLACE(card_number, '[^0-9]', ''), 4))
    WHEN pci_clearance = 'NONE' THEN 'XXXX-XXXX-XXXX-XXXX'
    ELSE 'XXXX-XXXX-XXXX-XXXX'
  END;
```

**Why This Works:**
- Built-in string functions only
- No external calls or lookups
- Deterministic and cacheable
- Simple CASE logic
- Minimal CPU overhead

**Performance Impact:** ✅ **Near-native** (< 0.1ms per value)

---

### 🚀 High-Performance Geographic Residency Filter

```sql
-- ✅ EXCELLENT - Simple region matching
CREATE OR REPLACE FUNCTION filter_data_residency(
    customer_region STRING,
    data_residency STRING,
    user_region STRING
)
RETURNS BOOLEAN
DETERMINISTIC
RETURN 
  CASE 
    -- Global access
    WHEN user_region = 'Global' THEN TRUE
    
    -- Exact region match
    WHEN customer_region = user_region THEN TRUE
    
    -- Public data accessible by all
    WHEN data_residency = 'Public' THEN TRUE
    
    ELSE FALSE
  END;
```

**Why This Works:**
- Simple string equality checks
- No subqueries or joins
- Spark can optimize predicate
- Enables partition pruning
- Vectorizes perfectly

**Performance Impact:** ✅ **Negligible overhead** (< 0.01ms)

---

### 🚀 High-Performance AML Clearance Filter

```sql
-- ✅ EXCELLENT - Integer comparison for clearance levels
CREATE OR REPLACE FUNCTION filter_aml_access(
    data_sensitivity INT,
    user_clearance INT,
    aml_flag STRING
)
RETURNS BOOLEAN
DETERMINISTIC
RETURN 
  CASE 
    -- High clearance sees everything
    WHEN user_clearance >= 5 THEN TRUE
    
    -- Match clearance to sensitivity
    WHEN user_clearance >= data_sensitivity THEN TRUE
    
    -- Block flagged data from low clearance
    WHEN aml_flag = 'SUSPICIOUS' AND user_clearance < 3 THEN FALSE
    
    ELSE FALSE
  END;
```

**Why This Works:**
- Integer comparisons (fastest operations)
- No string parsing or lookups
- Logical operators only
- Fully indexable
- Branch prediction friendly

**Performance Impact:** ✅ **Optimal** (< 0.001ms)

---

## 📊 Finance Performance Benchmarks

| Pattern Type | Query Time | Scalability | Trading Systems Compatible |
|-------------|------------|-------------|---------------------------|
| ❌ Real-time position calc | 10+ seconds | Breaks | No - unacceptable |
| ❌ Credit score lookup | 5-10 seconds | Poor | No - too slow |
| ❌ AML pattern analysis | 1-5 seconds | Poor | No - timeouts |
| ❌ BIN database lookup | 500ms-2s | Limited | No - high latency |
| ❌ Currency conversion | 500ms-1s | Poor | No - variable latency |
| ✅ Simple column logic | 1-10ms | Excellent | Yes - acceptable |
| ✅ Integer comparisons | < 1ms | Excellent | Yes - optimal |

**Trading System Requirement**: < 10ms query overhead for position queries
**Compliance Reporting**: < 100ms acceptable for audit queries
**Real-time Fraud**: < 50ms for card authorization queries

---

## 🎯 Finance ABAC Golden Rules

### **The 8 Commandments for Financial Services**

1. **Pre-Compute, Don't Calculate**: AML flags, risk scores, customer tiers - compute once, filter many
2. **Store, Don't Lookup**: Card types, account balances, position P&L - store in columns
3. **Filter Columns, Don't Join Tables**: Use column values, not subqueries
4. **Simple Logic, Fast Execution**: String equality and integer comparisons beat complex calculations
5. **Batch ETL, Not Real-Time**: Update risk scores nightly, not per-query
6. **Deterministic Always**: Same input = same output, enables caching
7. **Test at Trading Scale**: 1 million rows minimum, 10 million for HFT systems
8. **Monitor Query Plans**: EXPLAIN every ABAC query to verify optimization

---

## 🔧 Financial Services Performance Testing

### **Load Test Template for Trading Systems**

```sql
-- High-frequency trading simulation (1M positions)
WITH test_positions AS (
  SELECT 
    CONCAT('POS', LPAD(seq, 8, '0')) as position_id,
    CASE WHEN MOD(seq, 4) = 0 THEN 'Equity'
         WHEN MOD(seq, 4) = 1 THEN 'Fixed_Income'
         WHEN MOD(seq, 4) = 2 THEN 'FX'
         ELSE 'Commodities' 
    END as trading_desk,
    RAND() * 1000000 as pnl,
    current_timestamp() as test_start
  FROM range(1000000)
)
SELECT 
  COUNT(*) as rows_processed,
  MAX(test_start) as end_time,
  CAST(COUNT(*) / 
    (UNIX_TIMESTAMP(MAX(test_start)) - UNIX_TIMESTAMP(MIN(test_start)))
    AS BIGINT) as rows_per_second
FROM test_positions
WHERE trading_desk = 'Equity';  -- Simulates desk filtering
```

### **Performance Targets for Financial Services**

- **Trading Position Queries**: > 100,000 rows/second
- **Card Transaction Masking**: > 500,000 rows/second
- **Customer Data Filtering**: > 1,000,000 rows/second
- **Query Overhead**: < 5% additional latency
- **Memory Usage**: < 1.5x baseline query

---

## 🚨 Emergency Performance Recovery

### **When ABAC Policies Kill Trading Performance**

1. **Immediate Action**: 
   - Identify slow policy with query profiling
   - Check for external lookups or subqueries
   - Temporarily disable specific policy (not entire ABAC)

2. **Diagnosis**:
```sql
-- Analyze query plan
EXPLAIN EXTENDED 
SELECT * FROM fincat.finance.TradingPositions LIMIT 100;

-- Look for:
-- - Correlated subqueries
-- - External table joins in mask functions
-- - Non-deterministic operations
```

3. **Fix**: Rewrite using performance patterns above

4. **Validation**: Load test with 1M+ rows before re-enabling

---

## 💡 Finance-Specific Optimization Tips

### **For High-Frequency Trading Systems**
- Use integer-based clearance levels, not string comparisons
- Pre-filter positions by desk in ETL, use ABAC for secondary filtering
- Cache position snapshots, don't query live data in filters
- Minimize row filters, prefer column masking

### **For Card Payment Processing**
- Mask card numbers client-side when possible, not in database
- Store masked versions alongside encrypted versions
- Use column-level encryption + ABAC masking together
- Pre-validate PCI clearance, don't check per-query

### **For AML Compliance Reporting**
- Run pattern detection in batch (hourly/daily)
- Store results in investigation_status column
- ABAC filters based on stored flags, not live analysis
- Separate real-time monitoring from historical reporting

### **For Cross-Border Operations**
- Partition tables by customer_region
- Use region-based clusters when possible
- Leverage Spark partition pruning with region filters
- Consider materialized views per region

---

## 📋 Pre-Production Performance Checklist

Before deploying finance ABAC to production:

- [ ] All mask functions use only built-in SQL functions
- [ ] No external API calls or network operations
- [ ] No correlated subqueries or table joins in functions
- [ ] All row filters use column comparisons only
- [ ] Risk scores and tiers pre-computed and stored
- [ ] Tested with 1M+ rows per table minimum
- [ ] Query plans reviewed and optimized
- [ ] Performance monitoring in place
- [ ] Rollback plan documented
- [ ] Trading desk approved performance impact

---

## 🎯 Finance ABAC Architecture Principles

### **Layered Security Without Performance Penalty**

```
Layer 1: Data Classification (At Rest)
├── Pre-compute risk scores, customer tiers, AML flags
├── Store classification in columns
└── ETL runs nightly or on trigger events

Layer 2: ABAC Policies (Query Time)
├── Filter based on stored columns
├── Mask using simple string operations
└── Pure column logic, no external calls

Layer 3: Monitoring (Continuous)
├── Query performance metrics
├── Policy effectiveness tracking
└── Compliance audit logging
```

**Result**: Security that scales to millions of queries per second without becoming a bottleneck.

---

**🎯 Remember: In financial services, milliseconds are money. Great ABAC is invisible ABAC - secure by default, fast by design.**

---

## 🏦 Finance-Specific Test Scenarios

### **Scenario 1: High-Frequency Trading Query**
- **Volume**: 10,000 queries/second
- **Target**: < 10ms per query
- **Test**: Position filtering by trading desk

### **Scenario 2: Card Authorization**
- **Volume**: 50,000 transactions/second
- **Target**: < 50ms per authorization
- **Test**: PCI-DSS card number masking

### **Scenario 3: AML Batch Report**
- **Volume**: 10 million transactions
- **Target**: < 5 minutes total
- **Test**: Transaction filtering by clearance level

### **Scenario 4: Customer Analytics**
- **Volume**: 100 million customer records
- **Target**: < 30 seconds for aggregations
- **Test**: Cross-table joins with deterministic masking

---

**If your ABAC policies pass all four scenarios, you're ready for production financial services deployment.** 🚀
