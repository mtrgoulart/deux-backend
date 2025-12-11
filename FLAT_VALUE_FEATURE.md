# Flat Value Sizing Feature

## Overview

This document describes the new **flat value sizing** feature added to the deux platform. This feature allows strategies to use exact dollar amounts for trades instead of percentage-based sizing.

## Motivation

**Before**: Strategies could only use percentage-based sizing
- Example: Trade with 10% of account balance
- Problem: Can't specify exact amounts like "trade $100 worth"

**After**: Strategies can use either mode
- **Percentage mode**: Trade with X% of account balance (legacy)
- **Flat value mode**: Trade exact $X amount (new)

## Use Cases

### Percentage Mode (Legacy)
```
Strategy: Buy with 10% of balance
Balance: $10,000
Order size: $1,000 (10% × $10,000)
```

### Flat Value Mode (New)
```
Strategy: Buy with exactly $500
Balance: $10,000
Order size: $500 (exact amount)
```

Benefits:
- ✅ Consistent position sizes regardless of account balance
- ✅ Better risk management with fixed dollar amounts
- ✅ Easier to calculate P&L expectations
- ✅ Useful for strategies with fixed capital allocation

---

## Database Changes

### New Columns in `strategy` Table

```sql
ALTER TABLE strategy
ADD COLUMN size_mode VARCHAR(20) DEFAULT 'percentage',
ADD COLUMN flat_value DECIMAL(20, 8) DEFAULT NULL;
```

**Column Descriptions**:

| Column | Type | Description | Values |
|--------|------|-------------|--------|
| `size_mode` | VARCHAR(20) | Sizing mode identifier | `"percentage"` or `"flat_value"` |
| `flat_value` | DECIMAL(20,8) | Exact amount to trade | Positive number or NULL |

**Constraints**:
- `size_mode` defaults to `"percentage"` for backward compatibility
- `flat_value` is only used when `size_mode = "flat_value"`
- `flat_value` must be positive when used

### Migration SQL

```sql
-- Add new columns to strategy table
ALTER TABLE strategy
ADD COLUMN IF NOT EXISTS size_mode VARCHAR(20) DEFAULT 'percentage',
ADD COLUMN IF NOT EXISTS flat_value DECIMAL(20, 8) DEFAULT NULL;

-- Optional: Add check constraint
ALTER TABLE strategy
ADD CONSTRAINT check_flat_value_positive
CHECK (flat_value IS NULL OR flat_value > 0);

-- Optional: Add check constraint for size_mode
ALTER TABLE strategy
ADD CONSTRAINT check_size_mode_valid
CHECK (size_mode IN ('percentage', 'flat_value'));
```

---

## Code Changes

### 1. SQL Queries Updated

**Files Modified**:
- `queries/select_buy_strategy_by_instance.sql`
- `queries/select_sell_strategy_by_instance.sql`

**Changes**: Added `s.size_mode` and `s.flat_value` to SELECT statement

```sql
SELECT
    s.id,
    i.symbol,
    s.percent,
    s.condition_limit,
    s.interval,
    s.simultaneous_operations,
    s.size_mode,        -- NEW
    s.flat_value        -- NEW
FROM ...
```

### 2. StrategyConfig DTO Enhanced

**File**: `source/models.py`

**Added Fields**:
```python
@dataclass
class StrategyConfig:
    # ... existing fields ...
    size_mode: str = "percentage"
    flat_value: Optional[float] = None
```

**Added Helper Methods**:
```python
def is_flat_value_mode(self) -> bool:
    """Check if strategy uses flat value sizing."""
    return self.size_mode == "flat_value"

def is_percentage_mode(self) -> bool:
    """Check if strategy uses percentage-based sizing."""
    return self.size_mode == "percentage"
```

### 3. OperationContext Updated

**File**: `source/models.py`

**Enhanced `to_trade_data()` method**:
```python
def to_trade_data(self) -> dict:
    return {
        # ... existing fields ...
        'size_mode': self.strategy.size_mode,      # NEW
        'flat_value': self.strategy.flat_value     # NEW
    }
```

### 4. Instance Interface Updated

**File**: `interface/instance.py`

**Changes**: Unpacks new fields from database query

```python
# Unpack strategy data (including new fields)
(
    strategy_id, symbol, percent, condition_limit,
    interval, simultaneous_operations,
    size_mode, flat_value  # NEW
) = strategy_result[0]

# Handle legacy data
if size_mode is None:
    size_mode = "percentage"

# Build StrategyConfig with new fields
strategy_config = StrategyConfig(
    # ... existing fields ...
    size_mode=size_mode,
    flat_value=flat_value
)
```

### 5. Operation Execution Refactored

**File**: `source/operation.py`

**Function Signature Updated**:
```python
def execute_operation(
    user_id, api_key, exchange_id, perc_balance_operation,
    symbol, side, instance_id, max_amount_size=None,
    size_mode="percentage",  # NEW - defaults to percentage
    flat_value=None          # NEW
):
```

**New Logic**:
```python
if size_mode == "flat_value":
    # Validate flat_value parameter
    if flat_value is None or flat_value <= 0:
        return {"status": "error", "message": "Invalid flat_value"}

    size = Decimal(str(flat_value))

    # Check if balance is sufficient
    if balance < size:
        return {
            "status": "insufficient_balance",
            "message": f"Required: {size}, Available: {balance}"
        }

else:  # percentage mode
    # Calculate size as percentage of balance (legacy logic)
    size = balance * Decimal(str(perc_balance_operation))
```

### 6. Celery Task Updated

**File**: `celeryManager/tasks/operation.py`

**Changes**: Passes new parameters to execute_operation

```python
result = execute_operation(
    # ... existing parameters ...
    size_mode=data.get("size_mode", "percentage"),  # NEW
    flat_value=data.get("flat_value")               # NEW
)
```

---

## Data Flow

### Complete Flow with Flat Value

```
1. Database: strategy table
   ↓ size_mode = "flat_value"
   ↓ flat_value = 500.00

2. SQL Query: select_buy_strategy_by_instance.sql
   ↓ Returns: (id, symbol, percent, ..., "flat_value", 500.00)

3. interface/instance.py
   ↓ Unpacks: size_mode, flat_value
   ↓ Builds: StrategyConfig(size_mode="flat_value", flat_value=500.00)
   ↓ Builds: OperationContext(strategy=strategy_config)

4. source/manager.py
   ↓ Calls: context.to_trade_data()
   ↓ Returns: {'size_mode': 'flat_value', 'flat_value': 500.00, ...}

5. Celery Task: trade.execute_operation
   ↓ Receives: data with size_mode and flat_value

6. source/operation.py::execute_operation()
   ↓ Gets balance from exchange
   ↓ Checks: balance >= 500.00?
   ↓ If yes: Uses size = 500.00
   ↓ If no: Returns insufficient_balance error
   ↓ Places order with exact $500
```

---

## Usage Examples

### Example 1: Creating a Flat Value Strategy

```sql
INSERT INTO strategy (
    side, percent, condition_limit, interval,
    simultaneous_operations, size_mode, flat_value
) VALUES (
    'buy',
    0.0,           -- Not used in flat_value mode
    2,             -- Require 2 indicators
    5.0,           -- 5 minute interval
    3,             -- Max 3 simultaneous operations
    'flat_value',  -- Use flat value mode
    500.00         -- Trade exactly $500
);
```

### Example 2: Creating a Percentage Strategy (Legacy)

```sql
INSERT INTO strategy (
    side, percent, condition_limit, interval,
    simultaneous_operations, size_mode, flat_value
) VALUES (
    'buy',
    0.10,          -- 10% of balance
    2,
    5.0,
    3,
    'percentage',  -- Use percentage mode
    NULL           -- flat_value not used
);
```

### Example 3: Updating Existing Strategy to Flat Value

```sql
UPDATE strategy
SET
    size_mode = 'flat_value',
    flat_value = 1000.00
WHERE
    id = 123;
```

---

## Backward Compatibility

### Legacy Data Handling

✅ **Fully backward compatible** - No breaking changes

1. **Existing strategies** without `size_mode`:
   - Default to `"percentage"` mode
   - Handled in `interface/instance.py`:
     ```python
     if size_mode is None:
         size_mode = "percentage"
     ```

2. **Execute operation** without new parameters:
   - Defaults to `size_mode="percentage"`
   - `flat_value=None`

3. **Database migration**:
   - `size_mode` defaults to `'percentage'`
   - `flat_value` defaults to `NULL`

### Migration Path

**Phase 1**: Deploy code (backward compatible)
- ✅ All existing strategies continue working
- ✅ New strategies can use either mode

**Phase 2**: Run database migration
```sql
ALTER TABLE strategy
ADD COLUMN IF NOT EXISTS size_mode VARCHAR(20) DEFAULT 'percentage',
ADD COLUMN IF NOT EXISTS flat_value DECIMAL(20, 8) DEFAULT NULL;
```

**Phase 3**: Create new strategies using flat_value mode
- Update frontend to support mode selection
- Allow users to choose between modes

---

## Validation & Error Handling

### Validation Rules

1. **Flat Value Mode**:
   - ✅ `flat_value` must be positive number
   - ✅ Account balance must be >= `flat_value`
   - ✅ Returns `insufficient_balance` if balance too low

2. **Percentage Mode**:
   - ✅ `percent` must be between 0 and 1
   - ✅ Calculated size must be > 0

### Error Responses

```python
# Insufficient balance for flat_value
{
    "status": "insufficient_balance",
    "message": "Insufficient balance. Required: 500, Available: 300"
}

# Invalid flat_value
{
    "status": "error",
    "message": "flat_value must be a positive number when size_mode is 'flat_value'"
}

# Zero order size (percentage mode)
{
    "status": "success",
    "message": "Calculated order size is zero. No operation performed."
}
```

---

## Testing Checklist

### Unit Tests

- [ ] `StrategyConfig.is_flat_value_mode()` returns True when mode is "flat_value"
- [ ] `StrategyConfig.is_percentage_mode()` returns True when mode is "percentage"
- [ ] `OperationContext.to_trade_data()` includes size_mode and flat_value
- [ ] `execute_operation()` calculates size correctly in flat_value mode
- [ ] `execute_operation()` checks balance in flat_value mode
- [ ] `execute_operation()` falls back to percentage mode when size_mode not specified
- [ ] Error handling for invalid flat_value (null, zero, negative)

### Integration Tests

- [ ] Create strategy with flat_value mode in database
- [ ] Execute operation with flat_value mode
- [ ] Verify order placed with exact flat_value amount
- [ ] Test insufficient balance error in flat_value mode
- [ ] Verify backward compatibility with existing percentage strategies
- [ ] Test mode switching (percentage → flat_value → percentage)

### End-to-End Tests

- [ ] Create instance with flat_value strategy
- [ ] Send webhook signal
- [ ] Verify operation executes with flat_value sizing
- [ ] Check logs for correct mode indication
- [ ] Verify trade saved to database with correct size

---

## Logging Enhancements

New log messages help identify which mode is being used:

```python
# Flat value mode
general_logger.info(f"Using FLAT VALUE mode: size = 500.00 USDT")

# Percentage mode
general_logger.info(f"Using PERCENTAGE mode: 10.0% of 5000.0 = 500.0 USDT")

# Order execution
general_logger.info(
    f'Sending order for user_id: 123, instance_id: 456, '
    f'side: buy, size: 500.0, ccy: USDT, mode: flat_value'
)
```

---

## Frontend Integration

### API Changes (Future)

When updating the frontend, add mode selection to strategy form:

```javascript
// Strategy form fields
{
  side: 'buy',
  size_mode: 'flat_value',  // 'percentage' or 'flat_value'
  percent: 0.10,             // Used if size_mode = 'percentage'
  flat_value: 500.00,        // Used if size_mode = 'flat_value'
  // ... other fields
}
```

### UI Recommendations

```
┌─────────────────────────────────────────┐
│ Strategy Configuration                  │
├─────────────────────────────────────────┤
│                                         │
│ Sizing Mode:                            │
│  ○ Percentage of Balance                │
│  ● Flat Value                           │
│                                         │
│ Amount: $ 500.00                        │
│                                         │
│ [When balance mode is selected:]       │
│ Percentage: 10 %                        │
│                                         │
└─────────────────────────────────────────┘
```

---

## Performance Impact

### Memory
- ✅ **Negligible**: 2 additional fields per strategy (8-16 bytes)

### CPU
- ✅ **Improved**: Flat value mode is simpler (no percentage calculation)
- ✅ **Same**: Percentage mode unchanged

### Database
- ✅ **Minimal**: 2 additional columns per strategy row
- ✅ **No additional queries**: Same number of DB calls

---

## Benefits of DTO Architecture

This feature demonstrates the **scalability** of the refactored DTO architecture:

### Adding This Feature

**Old Architecture** (would require):
1. ❌ Update 5+ files with parameter changes
2. ❌ Update 10+ function signatures
3. ❌ Risk breaking existing code
4. ❌ Complex testing due to scattered changes

**New Architecture** (actual):
1. ✅ Update SQL queries (2 files)
2. ✅ Add 2 fields to `StrategyConfig` DTO
3. ✅ Update 1 unpacking statement
4. ✅ Update `execute_operation()` logic
5. ✅ **DTO automatically propagates everywhere!**

### Lines of Code Changed

| File | Lines Changed | Reason |
|------|---------------|--------|
| `select_buy_strategy_by_instance.sql` | +2 | Add columns to SELECT |
| `select_sell_strategy_by_instance.sql` | +2 | Add columns to SELECT |
| `source/models.py` | +15 | Add fields + helper methods |
| `interface/instance.py` | +8 | Unpack new fields |
| `source/operation.py` | +50 | Add flat_value logic |
| `celeryManager/tasks/operation.py` | +3 | Pass new parameters |
| **Total** | **~80 lines** | **Minimal changes!** |

---

## Summary

### What Was Added

✅ **Two new database columns**: `size_mode`, `flat_value`
✅ **Flat value execution mode**: Trade exact dollar amounts
✅ **Balance validation**: Ensure sufficient funds for flat values
✅ **Backward compatibility**: Existing strategies work unchanged
✅ **Helper methods**: `is_flat_value_mode()`, `is_percentage_mode()`
✅ **Enhanced logging**: Mode indication in logs
✅ **Comprehensive error handling**: Clear error messages

### Key Benefits

🎯 **Flexible Position Sizing**: Choose percentage OR flat value
🎯 **Better Risk Management**: Fixed dollar risk per trade
🎯 **Easy to Extend**: Adding new modes is simple with DTOs
🎯 **Zero Breaking Changes**: Fully backward compatible
🎯 **Clean Code**: DTOs make data flow clear and maintainable

---

## Next Steps

1. **Database Migration**: Run ALTER TABLE to add new columns
2. **Testing**: Execute comprehensive test suite
3. **Deployment**: Deploy to QA environment
4. **Frontend**: Add UI for mode selection
5. **Documentation**: Update user-facing documentation
6. **Monitoring**: Watch for any issues with new mode

---

**Feature Status**: ✅ Complete and ready for testing
**Date**: 2025-12-08
**Compatibility**: Fully backward compatible
**Database Migration Required**: Yes (non-breaking)
