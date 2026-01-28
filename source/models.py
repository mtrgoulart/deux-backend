"""
Data Transfer Objects (DTOs) for structured data flow in webhook processing.

This module defines data classes that encapsulate related data,
replacing scattered individual variables with cohesive structures.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class InstanceDetails:
    """
    Represents core instance information from the database.

    Data source: select_instance_details.sql
    """
    instance_id: int
    user_id: int
    api_key_id: int
    instance_name: str
    exchange_id: int
    start_date: datetime
    share_id: Optional[int] = None

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "instance_id": self.instance_id,
            "user_id": self.user_id,
            "api_key_id": self.api_key_id,
            "instance_name": self.instance_name,
            "exchange_id": self.exchange_id,
            "start_date": self.start_date.isoformat() if isinstance(self.start_date, datetime) else str(self.start_date),
            "share_id": self.share_id
        }


@dataclass
class StrategyConfig:
    """
    Represents a trading strategy configuration.

    Data source: select_buy_strategy_by_instance.sql / select_sell_strategy_by_instance.sql

    Size Modes:
        - "percentage": Calculate size as percentage of balance (uses percent field)
        - "flat_value": Use exact flat value amount (uses flat_value field)
    """
    strategy_id: int
    symbol: str
    side: str
    percent: float
    condition_limit: int
    interval: float
    simultaneous_operations: int
    size_mode: str = "percentage"  # "percentage" or "flat_value"
    flat_value: Optional[float] = None  # Used when size_mode = "flat_value"

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "strategy_id": self.strategy_id,
            "symbol": self.symbol,
            "side": self.side,
            "percent": self.percent,
            "condition_limit": self.condition_limit,
            "interval": self.interval,
            "simultaneous_operations": self.simultaneous_operations,
            "size_mode": self.size_mode,
            "flat_value": self.flat_value
        }

    def is_flat_value_mode(self) -> bool:
        """Check if strategy uses flat value sizing."""
        return self.size_mode == "flat_value"

    def is_percentage_mode(self) -> bool:
        """Check if strategy uses percentage-based sizing."""
        return self.size_mode == "percentage"


@dataclass
class OperationContext:
    """
    Complete context for executing a trading operation.

    Combines instance details and strategy configuration into a single cohesive structure.
    This replaces passing 10+ individual parameters through function calls.
    """
    instance: InstanceDetails
    strategy: StrategyConfig

    @property
    def user_id(self) -> int:
        """Convenience property for accessing user_id."""
        return self.instance.user_id

    @property
    def instance_id(self) -> int:
        """Convenience property for accessing instance_id."""
        return self.instance.instance_id

    @property
    def api_key_id(self) -> int:
        """Convenience property for accessing api_key_id."""
        return self.instance.api_key_id

    @property
    def exchange_id(self) -> int:
        """Convenience property for accessing exchange_id."""
        return self.instance.exchange_id

    @property
    def share_id(self) -> Optional[int]:
        """Convenience property for accessing share_id."""
        return self.instance.share_id

    @property
    def start_date(self) -> datetime:
        """Convenience property for accessing start_date."""
        return self.instance.start_date

    @property
    def symbol(self) -> str:
        """Convenience property for accessing symbol."""
        return self.strategy.symbol

    @property
    def side(self) -> str:
        """Convenience property for accessing side."""
        return self.strategy.side

    @property
    def percent(self) -> float:
        """Convenience property for accessing percent."""
        return self.strategy.percent

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "instance": self.instance.to_dict(),
            "strategy": self.strategy.to_dict()
        }

    def to_trade_data(self) -> dict:
        """
        Convert to trade execution data format.

        This format is used when sending tasks to the 'ops' queue.
        Includes both percentage and flat_value modes.
        """
        return {
            'user_id': self.user_id,
            'api_key': self.api_key_id,
            'exchange_id': self.exchange_id,
            'perc_balance_operation': self.percent,
            'symbol': self.symbol,
            'side': self.side,
            'instance_id': self.instance_id,
            'size_mode': self.strategy.size_mode,
            'flat_value': self.strategy.flat_value
        }

    def to_sharing_data(self) -> dict:
        """
        Convert to sharing data format.

        This format is used when sending tasks to the 'sharing' queue.
        Includes size_mode and flat_value for flat value sizing support.
        """
        return {
            "share_id": self.share_id,
            "user_id": self.user_id,
            "side": self.side,
            "symbol": self.symbol,
            "perc_size": self.percent,
            "size_mode": self.strategy.size_mode,
            "flat_value": self.strategy.flat_value
        }
