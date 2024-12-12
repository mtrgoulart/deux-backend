from flask import jsonify
from source.director import OperationManager
from source.dbmanager import load_query
from log.log import general_logger
from source.context import get_db_connection  # Usa o gerenciador de conexão do context.py

operation_managers = {}  # Dicionário para gerenciar múltiplas instâncias


def save_strategy(data, user_id):
    """
    Salva uma estratégia no banco de dados (Buy e Sell).
    """
    try:
        strategy_id = data.get('strategy_id')
        symbol = data.get('symbol')
        buy_data = data.get('buy')
        sell_data = data.get('sell')

        if not strategy_id or not symbol or not buy_data or not sell_data:
            return jsonify({"error": "Invalid strategy data"}), 400

        with get_db_connection() as db_client:
            # Query para salvar a estratégia Buy
            buy_query = load_query('insert_strategy.sql')
            db_client.insert_data(buy_query, (
                user_id, strategy_id, symbol, 'buy', buy_data['percent'],
                buy_data['condition_limit'], buy_data['interval'],
                buy_data['simultaneous_operations'], 'stopped'
            ))

            # Query para salvar a estratégia Sell
            sell_query = load_query('insert_strategy.sql')
            db_client.insert_data(sell_query, (
                user_id, strategy_id, symbol, 'sell', sell_data['percent'],
                sell_data['condition_limit'], sell_data['interval'],
                None, 'stopped'
            ))

        general_logger.info(f"Strategy {strategy_id} saved for user {user_id}.")
        return jsonify({"message": "Strategy saved successfully", "strategy_id": strategy_id}), 200
    except Exception as e:
        general_logger.error(f"Error saving strategy: {str(e)}")
        return jsonify({"error": str(e)}), 500


def delete_strategy(strategy_id, user_id):
    """
    Deleta uma estratégia do banco de dados.
    """
    try:
        with get_db_connection() as db_client:
            # Busca a query de deleção no arquivo SQL
            query = load_query('delete_strategy.sql')
            
            # Passa os parâmetros no formato correto
            params = (user_id, strategy_id)

            # Executa a query usando o método update_data
            rows_affected = db_client.delete_data(query, params)
            
            if rows_affected == 0:
                message = f"No strategy found with ID {strategy_id} for user {user_id}."
                general_logger.warning(message)
                return jsonify({"error": message}), 404

            general_logger.info(f"Strategy {strategy_id} deleted for user {user_id}.")
            return jsonify({"message": "Strategy deleted successfully", "strategy_id": strategy_id}), 200
    except Exception as e:
        general_logger.error(f"Error deleting strategy: {str(e)}")
        return jsonify({"error": str(e)}), 500


def start_bot_operation(data, user_id):
    """
    Inicia operações do bot com base na estratégia registrada (Buy e Sell).
    """
    global operation_managers
    try:
        strategy_id = data.get('strategy_id')
        if not strategy_id:
            return {"error": "Strategy ID is required"}, 400

        with get_db_connection() as db_client:
            # Busca as estratégias no banco
            query = load_query('select_strategies_by_id.sql')
            strategies = db_client.fetch_data(query, (strategy_id, user_id))

        if not strategies:
            return {"error": "No strategies found for the given ID"}, 404

        # Inicializa cada subestratégia (Buy e Sell)
        responses = []
        for strategy in strategies:
            symbol = strategy[1]  # Obtém o símbolo do banco de dados
            side = strategy[2]  # "buy" ou "sell"
            operation_data = {
                "strategy_id": strategy_id,
                "symbol": symbol,
                "side": side,
                "percent": strategy[3],
                "condition_limit": strategy[4],
                "interval": strategy[5],
                "simultaneous_operations": strategy[6] if side == "buy" else 1
            }

            # Cria o OperationManager e inicia a operação
            director = OperationManager(user_id, operation_data, strategy_id)
            director.start_operation()
            operation_managers[f"{strategy_id}_{side}"] = director

            # Atualiza o status no banco de dados para "running"
            update_query = load_query('update_strategy_status.sql')
            db_client.update_data(update_query, ('running', strategy_id, user_id))

            general_logger.info(f"Started {side} operation for user {user_id} with strategy ID {strategy_id} and symbol {symbol}.")
            responses.append({"side": side, "symbol": symbol, "status": "started"})

        return {"message": "Both strategies started successfully", "responses": responses}, 200
    except Exception as e:
        general_logger.error(f"Error starting strategies: {str(e)}")
        return {"error": f"An error occurred: {str(e)}"}, 500
    
def stop_bot_operation(data, user_id):
    """
    Para uma operação em execução.
    """
    global operation_managers
    strategy_id = data.get('strategy_id')
    side = data.get('side')  # Adiciona o lado (buy/sell) ao identificar a operação
    try:
        operation_key = f"{strategy_id}_{side}"  # Combina ID da estratégia com o lado
        if operation_key in operation_managers:
            with get_db_connection() as db_client:
                manager = operation_managers.pop(operation_key)
                manager.stop_operation()
                query = load_query('update_strategy_status.sql')  # Atualiza o status no banco
                db_client.update_data(query, ('stopped', strategy_id, user_id))
                general_logger.info(f"Operation {operation_key} stopped for user {user_id}.")
            return {"message": f"Operation {operation_key} stopped successfully"}, 200
        return {"error": f"No operation found with key {operation_key}"}, 404
    except Exception as e:
        general_logger.error(f"Error stopping operation: {str(e)}")
        return {"error": str(e)}, 500
