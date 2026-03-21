# Trade Operation Sizing Refactor Plan

## Problem

The sizing system has inconsistent data formats and missing safety guards:

- `strategy.percent` stores decimals (0.8 = 80%) — frontend divides by 100 on save
- `neouser_sharing.size_amount` stores whole numbers (80 = 80%) — backend divides by 100 on read (`sharing.py` line 87)
- Both feed into the same `execute_operation()` via `perc_balance_operation` with no validation
- `max_amount_size` (copy trading USDT cap) is set in the payload but never passed to `execute_operation()`

## Bugs Found

1. **`max_amount_size` silently dropped**: `celeryManager/tasks/operation.py` does not pass `data.get("max_amount_size")` to `execute_operation()`. Copy trading USDT safety caps are non-functional.
2. **No range validation on `perc_balance_operation`**: A value of `80.0` would attempt to buy 8000% of balance with no guard.
3. **Dead code**: `calculate_order_size()` in `operation.py` lines 35-41 is unused.

## Phase 1 — Validation Guards (immediate, no downtime) [DONE]

Add safety nets without changing existing logic.

### 1.1 Add validation in `execute_operation()` (`source/operation.py`)

- Validate `perc_balance_operation` is in range `0 < x <= 1.0` for percentage mode
- Validate `flat_value > 0` for flat_value mode
- Self-healing guard: if `perc_balance_operation > 1.0`, log warning and auto-correct by dividing by 100
- Return `status: "validation_error"` (don't raise, avoids tenacity retries)

### 1.2 Fix `max_amount_size` bug (`celeryManager/tasks/operation.py`)

- Add `max_amount_size=data.get("max_amount_size")` to the `execute_operation()` call
- One-line fix, critical for copy trading safety caps

### 1.3 Add Pydantic validators on `OperationPayload` (`source/sharing.py`)

- Reject `perc_balance_operation` outside 0-1 range
- Validate consistency between `size_mode` and value fields

### 1.4 Remove dead code (`source/operation.py`)

- Delete unused `calculate_order_size()` function

## Phase 2 — Better Error Messages (no downtime) [DONE]

### 2.1 Enrich error responses (`source/operation.py`)

When exchange returns None/error, include in the response:
- `size_mode` used
- `perc_balance_operation` or `flat_value` value
- Computed `size` in quote currency
- Available balance

### 2.2 Enrich trace stages (`celeryManager/tasks/operation.py`)

Include sizing parameters in trace `record_stage` so traces show what was attempted.

## Phase 3 — Normalize DB Format (requires migration + coordination) [DONE]

### 3.1 Normalize `neouser_sharing.size_amount` to decimal on write

- **`deux-webapp/view/sharing.py`**: In `subscribe_sharing_instance()` and `update_sharing_subscription_sizing()`, when `size_mode == "percentage"`, divide `size_amount` by 100 before storing.
- **`deux-backend/source/sharing.py`**: Remove the `sub_value / 100.0` conversion on line 87.

### 3.2 Migrate existing rows

```sql
UPDATE neouser_sharing
SET size_amount = size_amount / 100.0
WHERE size_mode = 'percentage' AND size_amount > 1.0;
```

### 3.3 Deployment sequence

1. Deploy webapp change (new writes are decimal)
2. Run migration (existing rows converted)
3. Deploy backend change (remove `/100.0` conversion)
4. Can combine into single deployment with temporary guard: `if sub_value > 1.0: sub_value /= 100.0`

## Phase 4 — Structural Improvements (longer term) [DONE]

### 4.1 `SizingSpec` value object

Replace loose `perc_balance_operation / size_mode / flat_value / max_amount_size` params with a dataclass:
- Encapsulates all sizing parameters
- Validates on construction
- Has `compute_order_size(balance: Decimal) -> Decimal` method
- Serializable for celery transport

### 4.2 Unify operation paths

Both `OperationContext.to_trade_data()` and `OperationBuilder.build()` should produce payloads via the same `SizingSpec` construction.

## Key Files

| File | Role |
|------|------|
| `source/operation.py` | Core execution, sizing calculation (lines 200-280) |
| `source/sharing.py` | OperationBuilder + OperationPayload for copy trading |
| `source/models.py` | OperationContext + StrategyConfig DTOs |
| `interface/instance.py` | Regular operation context building |
| `celeryManager/tasks/operation.py` | Celery task handler (max_amount_size bug) |
| `deux-webapp/view/sharing.py` | Webapp endpoint saving size_amount |
