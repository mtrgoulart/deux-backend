from flask import jsonify
from source.director import OperationManager
from source.dbmanager import load_query
from log.log import general_logger
from source.context import get_db_connection  # Usa o gerenciador de conexão do context.py
from .instances import save_instance

operation_managers = {}  # Dicionário para gerenciar múltiplas instâncias


def save_strategy(data, user_id):
    """
    Salva ou atualiza uma estratégia no banco de dados (Buy e Sell) e cria a relação com uma instância.
    """
    try:
        strategy_uuid = data.get('strategy_id')
        instance_id = data.get('instance_id')  # Campo da instância
        symbol = data.get('symbol')
        buy_data = data.get('buy', {})
        sell_data = data.get('sell', {})
        api_key = data.get('api_key')  # Necessário para criar a instância
        instance_name = data.get('instanceName','default')  # Nome padrão da instância


        # Validação dos dados recebidos
        missing_fields = []
        if not strategy_uuid:
            missing_fields.append('strategy_id')
        if not instance_id:
            missing_fields.append('instance_id')
        if not symbol:
            missing_fields.append('symbol')
        if not buy_data:
            missing_fields.append('buy data')
        if not sell_data:
            missing_fields.append('sell data')

        if missing_fields:
            error_message = f"Missing required fields: {', '.join(missing_fields)}"
            general_logger.error(error_message)
            return jsonify({"error": error_message}), 400
        
        with get_db_connection() as db_client:
        
            check_instance_uuid_exist_query=load_query('check_instance_exists.sql')
            existing_instance=db_client.fetch_data(check_instance_uuid_exist_query, (instance_id,user_id))
        
    
            if not existing_instance:
                # Chamar a rota `save_instance` para criar uma nova instância
                instance_payload = {
                    "api_key": api_key,
                    "strategy": strategy_uuid,
                    "name": instance_name,
                    "status": 1,  # Status padrão
                    "instance_uuid": instance_id
                }
                instance_response, status_code = save_instance(instance_payload, user_id)


                if status_code != 201:
                    raise ValueError(f"Failed to create instance: {instance_response.get('error')}")

                # Atualizar o ID da instância a partir da resposta
                instance_id = instance_response["instance_id"]

        with get_db_connection() as db_client:
            # 1. Verificar se a estratégia já existe
            check_strategy_query = load_query('check_strategy_exists.sql')
            existing_strategy = db_client.fetch_data(check_strategy_query, (user_id, strategy_uuid))

            if not existing_strategy:
                # Inserir nova estratégia
                insert_strategy_query = load_query('insert_strategy.sql')
                strategy_id_buy=db_client.insert_data_returning(insert_strategy_query, (
                    user_id, strategy_uuid, symbol, 'buy', buy_data['percent'],
                    buy_data['condition_limit'], buy_data['interval'],
                    buy_data['simultaneous_operations'], 'stopped',buy_data['tp'],buy_data['sl']
                ))
                strategy_id_sell=db_client.insert_data_returning(insert_strategy_query, (
                    user_id, strategy_uuid, symbol, 'sell', sell_data['percent'],
                    sell_data['condition_limit'], sell_data['interval'],
                    None, 'stopped',None, None
                ))
                strategy_ids=[strategy_id_buy,strategy_id_sell]
                
                

            # 2. Criar relação entre a instância e a estratégia
            for strategy_id in strategy_ids:
                relation_query = load_query('insert_instance_strategy.sql')
                db_client.insert_data(relation_query, (instance_id, strategy_id))
                general_logger.info(f"Strategy {strategy_id} saved and linked to instance {instance_id} for user {user_id}.")

        
        return jsonify({"message": "Strategies saved and linked successfully", "strategy_ids": strategy_ids}), 200

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
