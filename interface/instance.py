from source.dbmanager import load_query
from log.log import general_logger
from source.context import get_db_connection
from source.director import OperationManager
from source.sharing import OperationBuilder

def get_instance_status(instance_id,user_id):
    with get_db_connection() as db_client:
        # Busca detalhes da instância e API Key
        
        query_instance = load_query('select_instance_status.sql')
        instance_status = db_client.fetch_data(query_instance, (instance_id, user_id))
        instance_status=instance_status[0][0]
        return instance_status
    
def execute_instance_operation(instance_id, user_id, side):
    """
    Executa a operação de compra ou venda para uma instância específica.
    """
    with get_db_connection() as db_client:
        # Busca detalhes da instância e API Key
        
        query_instance = load_query('select_instance_details.sql')
        instance_details = db_client.fetch_data(query_instance, (instance_id, user_id))

        if not instance_details:
            return False, "Instance not found"

        api_key_id, instance_name, exchange_id, start_date, share_id = instance_details[0]

        # Define a query correta com base no tipo de operação
        strategy_query = 'select_buy_strategy_by_instance.sql' if side == 'buy' else 'select_sell_strategy_by_instance.sql'
        query_strategies = load_query(strategy_query)
        strategy = db_client.fetch_data(query_strategies, (instance_id,))
        

        if not strategy:
            return False, f"No {side} strategies found for the instance"
        
        strategy_data = strategy[0]

        # Mapeamento dos dados da estratégia
        (
            strategy_id, 
            strategy_uuid, 
            symbol, 
            strategy_side, 
            percent, 
            condition_limit, 
            interval, 
            simultaneos_operations, 
            status,  # Adicionando a variável para armazenar o valor
            tp, 
            sl
        ) = strategy_data

        # Definindo None para os valores de tp e sl caso estejam vazios
        tp = tp if tp is not None else 0
        sl = sl if sl is not None else 0

        simultaneos_operations = simultaneos_operations if side == "buy" else 1

        operation_data = {
            "strategy_id": strategy_id,
            "symbol": symbol,
            "side": side,
            "percent": percent,
            "condition_limit": condition_limit,
            "interval": interval,
            "simultaneous_operations": simultaneos_operations,
            "tp": tp,
            "sl": sl
        }

        manager = OperationManager(
            user_id=user_id,
            data=operation_data,
            exchange_id=exchange_id,
            api_key=api_key_id,
            instance_id=instance_id,
            share_id=share_id
        )
        
        result=manager.execute_operation_handler(start_date)
        return result
    
def execute_shared_operations(share_id, user_id, symbol, side):
    try:
        builder = (
            OperationBuilder()
            .set_share_context(share_id, user_id)
            .set_symbol(symbol)
            .set_side(side)
        )

        all_builders = builder.fetch_sharing_info_all()
        OperationBuilder.send_all(all_builders)

        return {"status": "success", "message": f"{len(all_builders)} operações enviadas"}

    except Exception as e:
        general_logger.error(f"Erro ao executar operação compartilhada: {e}")
        return {"status": "error", "message": str(e)}
