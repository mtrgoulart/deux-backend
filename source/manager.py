from log.log import general_logger
import time
from .pp import Market, WebhookData, Operations
from .models import OperationContext
from datetime import datetime
import re
from .context import get_db_connection
from .exchange_interface import get_exchange_interface
from decimal import Decimal
from .celery_client import get_client
import uuid


def execute_operation(context: OperationContext):
    """
    Main entry point for executing a trading operation.

    This function orchestrates the entire operation flow:
    1. Validates interval constraints
    2. Checks trading conditions
    3. Executes the operation if conditions are met
    4. Handles copy trading distribution if applicable

    Args:
        context: OperationContext containing all necessary data

    Returns:
        dict: Operation result with status and details
    """
    # Check interval constraints
    interval_handler = IntervalHandler(context)

    if not interval_handler.check_interval():
        general_logger.info(f'[Instance: {context.instance_id}] Interval check failed')
        return {
            "status": "interval_not_met",
            "message": "Interval constraints not satisfied"
        }

    general_logger.info(f'[Instance: {context.instance_id}] Interval valid! Proceeding with operation')

    # Create market manager
    market = Market(symbol=context.symbol, side=context.side)

    # Execute operation with condition checking
    operation_handler = OperationHandler(context, market)
    result = operation_handler.execute_condition()

    return result


class IntervalHandler:
    """
    Handles interval validation for trading operations.

    Ensures that operations respect configured time intervals and
    simultaneous operation limits.
    """

    def __init__(self, context: OperationContext):
        """
        Initialize interval handler with operation context.

        Args:
            context: OperationContext containing strategy and instance details
        """
        self.interval = float(context.strategy.interval)
        self.symbol = context.symbol
        self.side = context.side
        self.instance_id = context.instance_id
        self.simultaneous_operations = context.strategy.simultaneous_operations

        # Initialize operations manager
        with get_db_connection() as db_client:
            self.operations = Operations(db_client)

    def get_last_operations(self, limit):
        """Fetch last N operations from database."""
        return self.operations.get_last_operations_from_db(self.instance_id, limit)

    def check_interval(self):
        """
        Check if interval constraints are satisfied.

        Returns:
            bool: True if operation can proceed, False otherwise
        """
        last_operations = self.get_last_operations(limit=self.simultaneous_operations)

        if not last_operations:
            return True

        # Check if all operations have the same side
        same_side = all(op["side"] == self.side for op in last_operations)
        if same_side:
            return False

        # Get the most recent operation
        last_operation = last_operations[0]

        # If last operation was opposite side, allow
        if last_operation["side"] != self.side:
            return True

        # Check time interval
        valid_interval = self._interval_logic(last_operation["date"])
        general_logger.info(f'Interval check result: {valid_interval}')
        return valid_interval

    def get_application_interval(self, last_operation_time):
        """Calculate minutes elapsed since last operation."""
        if last_operation_time:
            current_time = datetime.now()
            return (current_time - last_operation_time).total_seconds() / 60
        return None

    def _interval_logic(self, last_operation_time):
        """Validate if enough time has passed since last operation."""
        last_operation_interval = self.get_application_interval(last_operation_time)
        general_logger.info(f"Elapsed interval: {last_operation_interval} minutes")

        if self.interval == 0:
            return True

        return last_operation_interval >= self.interval


class OperationHandler:
    """
    Handles the execution of trading operations.

    Orchestrates condition checking, trade execution, webhook updates,
    and copy trading distribution.
    """

    def __init__(self, context: OperationContext, market_manager: Market):
        """
        Initialize operation handler with context and market manager.

        Args:
            context: OperationContext containing all operation details
            market_manager: Market instance for symbol/side management
        """
        self.context = context
        self.market_manager = market_manager
        self.condition_handler = ConditionHandler(context.strategy.condition_limit)

        # Initialize exchange interface
        self.exchange_interface = get_exchange_interface(
            context.exchange_id,
            context.user_id,
            context.api_key_id
        )

        # Initialize data managers
        with get_db_connection() as db_client:
            self.webhook_data_manager = WebhookData(db_client)

        with get_db_connection() as db_client:
            self.operations = Operations(db_client)

    def execute_condition(self):
        """
        Execute condition checking and trade execution.

        This method:
        1. Fetches webhook data for the instance
        2. Checks if trading conditions are met
        3. Sends trade execution task to ops queue
        4. Sends copy trading task to sharing queue (if applicable)
        5. Updates webhook records with operation task ID

        Returns:
            dict: Operation result with status and details
        """
        # Create unique execution ID for tracking
        execution_id = uuid.uuid4().hex[:8]
        log_prefix = f"[ExecID: {execution_id}] [Instance: {self.context.instance_id}] [Symbol: {self.context.symbol}]"

        try:
            # Fetch webhook data for condition checking
            data = self.webhook_data_manager.get_market_objects_as_models(
                self.context.instance_id,
                self.context.symbol,
                self.context.side,
                self.context.start_date
            )

            # Check if conditions are met
            conditions_met = self.check_conditions(data)
            data_is_sufficient = len(data) >= 1

            if conditions_met and data_is_sufficient:
                # Conditions satisfied - execute trade

                # Send trade execution task to ops queue
                async_result = get_client().send_task(
                    "trade.execute_operation",
                    kwargs={"data": self.context.to_trade_data()},
                    queue="ops"
                )

                operation_task_id = async_result.id

                # Send copy trading distribution task if share_id exists
                if self.context.share_id:
                    try:
                        general_logger.info(
                            f"{log_prefix} Sending sharing task for share_id={self.context.share_id}..."
                        )
                        get_client().send_task(
                            "process_sharing_operations",
                            kwargs={"data": self.context.to_sharing_data()},
                            queue="sharing"
                        )
                        general_logger.info(f"{log_prefix} Sharing task sent successfully.")
                    except Exception as e:
                        general_logger.error(
                            f"{log_prefix} Failed to send sharing task. Error: {e}",
                            exc_info=True
                        )

                # Update webhook records with operation task ID
                self.update_webhook_operation(data, operation_task_id)

                return {
                    "status": "success",
                    "operation_task_id": operation_task_id
                }

            else:
                # Conditions not met
                reason = ""
                if not conditions_met:
                    reason += "Condition check failed. "
                if not data_is_sufficient:
                    reason += f"Insufficient data (got {len(data)}, need >= 1). "

                return {
                    "status": "insufficient_condition",
                    "reason": reason.strip()
                }

        except Exception as e:
            general_logger.error(
                f"{log_prefix} Unexpected error during condition execution. Error: {e}",
                exc_info=True
            )
            return {
                "status": "failed",
                "error": str(e)
            }
        finally:
            general_logger.info(f"{log_prefix} Condition execution finished.")

    def update_webhook_operation(self, filtered_data, operation_task_id):
        """
        Update webhook records with the operation task ID.

        Args:
            filtered_data: List of webhook market objects
            operation_task_id: The Celery task ID for the operation
        """
        for market_object in filtered_data:
            webhook_id = market_object["id"]
            try:
                self.webhook_data_manager.update_market_object_at_index(
                    webhook_id,
                    str(operation_task_id)
                )
                general_logger.info(
                    f"Updated webhook {webhook_id} with operation task ID {operation_task_id}"
                )
            except Exception as e:
                general_logger.error(
                    f"Error updating webhook {webhook_id}: {e}"
                )

    def check_conditions(self, data):
        """Delegate condition checking to condition handler."""
        return self.condition_handler.check_condition(data)


class ConditionHandler:
    """
    Handles validation of trading conditions based on indicator signals.

    Ensures that the required number of different indicators have signaled
    before allowing a trade to execute.
    """

    def __init__(self, condition_limit):
        """
        Initialize condition handler.

        Args:
            condition_limit: Minimum number of different indicators required
        """
        self.condition_limit = condition_limit

    def check_condition(self, market_list):
        """
        Check if condition requirements are satisfied.

        Validates that for each symbol/side combination, we have signals
        from at least 'condition_limit' different indicators.

        Args:
            market_list: List of market webhook objects with indicator signals

        Returns:
            bool: True if conditions are met, False otherwise
        """
        # Group indicators by (symbol, side)
        symbol_side_indicators = {}

        for market in market_list:
            key = (market["symbol"], market["side"])

            if key not in symbol_side_indicators:
                symbol_side_indicators[key] = []

            # Add indicator if not already in the list
            if market["indicator"] not in symbol_side_indicators[key]:
                symbol_side_indicators[key].append(market["indicator"])

        # Verify each symbol/side combination has enough different indicators
        for key, indicators in symbol_side_indicators.items():
            if len(indicators) < int(self.condition_limit):
                return False

        return True
