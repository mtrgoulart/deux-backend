from source.dbmanager import load_query
from log.log import general_logger
from source.context import get_db_connection
from source.models import InstanceDetails, StrategyConfig, OperationContext
from source.manager import execute_operation
from source.sharing import OperationBuilder


def get_instance_status(instance_id, user_id):
    """
    Get the current status of an instance.

    Returns:
        int: Status code (2 = running, etc.) or None if not found
    """
    query_instance = load_query('select_instance_status.sql')

    with get_db_connection() as db_client:
        result = db_client.fetch_data(query_instance, (instance_id, user_id))

        if not result:
            return None

        return result[0][0]


def execute_instance_operation(instance_id, user_id, side):
    """
    Execute a trading operation for a specific instance.

    This function:
    1. Fetches instance details and strategy configuration from the database
    2. Builds structured DTOs (OperationContext) containing all necessary data
    3. Delegates to the operation handler for execution

    Args:
        instance_id: The instance ID
        user_id: The user ID
        side: 'buy' or 'sell'

    Returns:
        dict: Operation result with status and details
    """
    with get_db_connection() as db_client:
        # Fetch instance details
        query_instance = load_query('select_instance_details.sql')
        instance_result = db_client.fetch_data(query_instance, (instance_id, user_id))

        if not instance_result:
            return {"status": "error", "message": "Instance not found"}

        # Unpack instance details
        api_key_id, instance_name, exchange_id, start_date, share_id = instance_result[0]

        # Build InstanceDetails DTO
        instance_details = InstanceDetails(
            instance_id=instance_id,
            user_id=user_id,
            api_key_id=api_key_id,
            instance_name=instance_name,
            exchange_id=exchange_id,
            start_date=start_date,
            share_id=share_id
        )

        # Fetch strategy configuration based on side
        strategy_query = 'select_buy_strategy_by_instance.sql' if side == 'buy' else 'select_sell_strategy_by_instance.sql'
        query_strategies = load_query(strategy_query)
        strategy_result = db_client.fetch_data(query_strategies, (instance_id,))

        if not strategy_result:
            return {"status": "error", "message": f"No {side} strategies found for the instance"}

        # Unpack strategy data (including new size_mode and flat_value fields)
        (
            strategy_id,
            symbol,
            percent,
            condition_limit,
            interval,
            simultaneous_operations,
            size_mode,
            flat_value
        ) = strategy_result[0]

        # For sell operations, always use 1 simultaneous operation
        if side == "sell":
            simultaneous_operations = 1

        # Handle legacy data: if size_mode is None, default to "percentage"
        if size_mode is None:
            size_mode = "percentage"

        # Build StrategyConfig DTO
        strategy_config = StrategyConfig(
            strategy_id=strategy_id,
            symbol=symbol,
            side=side,
            percent=percent,
            condition_limit=condition_limit,
            interval=interval,
            simultaneous_operations=simultaneous_operations,
            size_mode=size_mode,
            flat_value=flat_value
        )

        # Build complete OperationContext
        operation_context = OperationContext(
            instance=instance_details,
            strategy=strategy_config
        )

        # Execute operation with structured context
        result = execute_operation(operation_context)
        return result
    
def execute_shared_operations(share_id, user_id, symbol, side, perc_size):
    try:
        builder = (
            OperationBuilder()
            .set_share_context(share_id, user_id)
            .set_symbol(symbol)
            .set_side(side)
            .set_perc_size(perc_size)
        )

        all_builders = builder.fetch_sharing_info_all()
        OperationBuilder.send_all(all_builders)

        return {"status": "success", "message": f"{len(all_builders)} operações enviadas"}

    except Exception as e:
        general_logger.error(f"Erro ao executar operação compartilhada: {e}")
        return {"status": "error", "message": str(e)}

