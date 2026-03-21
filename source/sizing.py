"""
SizingSpec — unified value object for order sizing.

Encapsulates all sizing parameters (mode, percentage, flat_value, max_cap)
and provides validated computation of order size from a balance.

Used by both regular operations (via OperationContext) and
copy trading operations (via OperationBuilder).
"""
from decimal import Decimal
from dataclasses import dataclass
from typing import Optional
from log.log import general_logger


@dataclass(frozen=True)
class SizingSpec:
    """Immutable specification for how to size an order.

    Attributes:
        size_mode: "percentage" or "flat_value"
        percent: Decimal fraction of balance (0.80 = 80%). Used in percentage mode.
        flat_value: Exact quote currency amount. Used in flat_value mode.
        max_amount_size: Cap on the base amount for percentage calc (copy trading).
    """
    size_mode: str = "percentage"
    percent: float = 1.0
    flat_value: Optional[float] = None
    max_amount_size: Optional[float] = None

    def __post_init__(self):
        if self.size_mode not in ("percentage", "flat_value"):
            raise ValueError(f"Unknown size_mode: {self.size_mode}")

    def validate(self):
        """Validate sizing parameters. Returns error message or None."""
        if self.size_mode == "flat_value":
            if self.flat_value is None or self.flat_value <= 0:
                return f"flat_value must be a positive number, got {self.flat_value}"
            return None

        # Percentage mode
        if self.percent is None:
            return "percent is required for percentage mode"
        if self.percent <= 0.0 or self.percent > 1.0:
            return f"percent={self.percent} out of range (0, 1.0]"
        return None

    def compute_order_size(self, balance: Decimal, currency: str):
        """Compute order size from balance.

        Returns:
            (size: Decimal, error: dict or None)
            On success: (computed_size, None)
            On error: (Decimal('0'), error_dict)
        """
        if self.size_mode == "flat_value":
            size = Decimal(str(self.flat_value))
            if balance < size:
                return Decimal('0'), {
                    "status": "insufficient_balance",
                    "message": f"Insufficient balance. Required: {size} {currency}, Available: {balance} {currency}",
                    "sizing_context": {
                        "size_mode": "flat_value",
                        "required": float(size),
                        "available": float(balance),
                        "currency": currency,
                    },
                }
            return size, None

        # Percentage mode
        base = balance

        if self.max_amount_size is not None:
            max_cap = Decimal(str(self.max_amount_size))
            if balance < max_cap:
                return Decimal('0'), {
                    "status": "insufficient_balance",
                    "message": f"Insufficient balance to cover max_amount_size. Balance: {balance} {currency}, Required: {max_cap} {currency}",
                    "sizing_context": {
                        "size_mode": "percentage",
                        "percent": self.percent,
                        "max_amount_size": self.max_amount_size,
                        "available": float(balance),
                        "currency": currency,
                    },
                }
            base = max_cap

        perc_decimal = Decimal(str(self.percent))
        size = base * perc_decimal
        return size, None

    def log_details(self, size, balance_raw, currency: str):
        """Log sizing computation details."""
        if self.size_mode == "flat_value":
            general_logger.info(f"  Mode: {self.size_mode} | Size: {size:.2f} {currency}")
        else:
            general_logger.info(f"  Mode: {self.size_mode} | Size: {size:.2f} {currency} | Percentage: {self.percent * 100}%")
        general_logger.info(f"  Balance: {balance_raw} {currency}")
        general_logger.info("-" * 80)

    def to_dict(self) -> dict:
        """Serialize for celery task transport."""
        return {
            "size_mode": self.size_mode,
            "perc_balance_operation": self.percent,
            "flat_value": self.flat_value,
            "max_amount_size": self.max_amount_size,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "SizingSpec":
        """Deserialize from celery task data dict."""
        percent = data.get("perc_balance_operation", 1.0)

        # Auto-correct whole-number percentages from old data
        if percent is not None and percent > 1.0:
            general_logger.warning(
                f"  SIZING AUTO-CORRECT: perc_balance_operation={percent} "
                f"looks like a whole-number percentage. Converting to {percent / 100.0}"
            )
            percent = percent / 100.0

        return cls(
            size_mode=data.get("size_mode", "percentage"),
            percent=percent,
            flat_value=data.get("flat_value"),
            max_amount_size=data.get("max_amount_size"),
        )

    @classmethod
    def from_strategy(cls, strategy) -> "SizingSpec":
        """Create from a StrategyConfig dataclass."""
        return cls(
            size_mode=strategy.size_mode,
            percent=strategy.percent,
            flat_value=strategy.flat_value,
            max_amount_size=None,
        )
