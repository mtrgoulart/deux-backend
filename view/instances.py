from flask import jsonify
from source.dbmanager import load_query
from log.log import general_logger
from source.context import get_db_connection
from source.director import OperationManager

operation_managers = {}

def start_running_instances():
    """
    Verifica e inicia todas as instâncias que estavam rodando antes da reinicialização da aplicação.
    """
    query = load_query('select_running_instances.sql')

    try:
        with get_db_connection() as db_client:
            running_instances_data = db_client.fetch_data(query)

            if not running_instances_data:
                general_logger.info('Nenhuma instancia para iniciar.')
                return
            
            general_logger.info(f"Iniciando {len(running_instances_data)} instâncias...")

            for data in running_instances_data:
                instance_id = data[1]
                user_id = data[0]

                success, message = start_instance_operation(instance_id=instance_id, user_id=user_id)
                
                if success:
                    general_logger.info(f"Instância {instance_id} iniciada com sucesso.")
                else:
                    general_logger.error(f"Erro ao iniciar instância {instance_id}: {message}")

    except Exception as e:
        general_logger.error(f"Error starting running instance: {str(e)}")

def save_instance(data, user_id):
    """
    Salva uma nova instância no banco de dados.
    """
    query = load_query('insert_instance.sql')
    try:
        with get_db_connection() as db_client:
            strategy_id = data.get('strategy')  # Obtém o ID da estratégia do payload
            if not strategy_id:
                raise ValueError("Strategy ID is required to create an instance.")
            api_key = data.get('api_key')
            if not api_key:
                raise ValueError("API Key is required to create an instance.")

            params = (
                user_id,          # ID do usuário
                api_key,  # ID da API Key
                data.get('name'),     # Nome da instância
                data.get('status', 1),  # Status (padrão: 1)
                data.get('instance_uuid'),
            )
            instance_id = db_client.insert_data_returning(query, params)

            if not instance_id:
                raise ValueError("Failed to generate instance ID.")

            #general_logger.info(f"Instance {instance_id} created for user {user_id}.")

            # Retorna o ID da instância criada
            return {"message": "Instance saved successfully", "instance_id": instance_id}, 201
    except Exception as e:
        general_logger.error(f"Error saving instance: {str(e)}")
        return {"error": str(e)}, 500

def remove_instance(instance_id, user_id):
    """
    Remove uma instância do banco de dados.
    """
    query = load_query('delete_instance.sql')
    try:
        with get_db_connection() as db_client:
            db_client.execute_query(query, (instance_id, user_id))
        return jsonify({"message": "Instance removed successfully"}), 200
    except Exception as e:
        general_logger.error(f"Error removing instance: {str(e)}")
        return jsonify({"error": str(e)}), 500

def start_instance(instance_id, user_id):
    with get_db_connection() as db_client:
        # Busca detalhes da instância e API Key
        query_instance = load_query('select_instance_details.sql')
        instance_details = db_client.fetch_data(query_instance, (instance_id, user_id))
        if not instance_details:
            return False, "Instance not found"
        
        update_instance_query=load_query('update_starting_instance.sql')
        db_client.update_data(update_instance_query,(2,instance_id))

        return True, "Instância iniciada com sucesso!"

def start_instance_operation(instance_id, user_id):
    global operation_managers
    try:
        # Conexão com o banco de dados
        with get_db_connection() as db_client:
            # Busca detalhes da instância e API Key
            query_instance = load_query('select_instance_details.sql')
            instance_details = db_client.fetch_data(query_instance, (instance_id, user_id))

            if not instance_details:
                return False, "Instance not found"

            api_key_id, instance_name, exchange_id = instance_details[0]

            # Busca as estratégias associadas à instância
            query_strategies = load_query('select_strategies_by_instance.sql')
            strategies = db_client.fetch_data(query_strategies, (instance_id,))

            if not strategies:
                return False, "No strategies found for the instance"

            # Inicia o OperationManager para cada estratégia
            responses = []
            for strategy in strategies:
                strategy_id = strategy[0]  # ID da estratégia (primary key)
                strategy_uuid = strategy[1]  # UUID da estratégia
                symbol = strategy[2]  # Símbolo
                side = strategy[3]  # "buy" ou "sell"
                operation_key = f"{instance_id}_{strategy_uuid}_{side}"

                # Verifica se já existe uma operação com a mesma chave
                if operation_key in operation_managers:
                    general_logger.warning(f"Operation for instance {instance_id}, strategy {strategy_uuid}, side {side} already running.")
                    continue  # Pula para a próxima estratégia

                operation_data = {
                    "strategy_id": strategy_id,
                    "symbol": symbol,
                    "side": side,
                    "percent": strategy[4],
                    "condition_limit": strategy[5],
                    "interval": strategy[6],
                    "simultaneous_operations": strategy[7] if side == "buy" else 1,
                    "tp":strategy[9],
                    "sl":strategy[10]
                }

                # Instancia o OperationManager e inicia a operação
                manager = OperationManager(
                    user_id=user_id,
                    data=operation_data,
                    strategy_id=strategy_id,
                    exchange_id=exchange_id,
                    api_key=api_key_id,
                    instance_id=instance_id
                )
                manager.start_operation()
                operation_key = f"{instance_id}_{strategy_uuid}_{side}"
                operation_managers[operation_key] = manager

                # Atualiza o status da estratégia para "running"
                update_query = load_query('update_strategy_status.sql')
                db_client.update_data(update_query, ('running', strategy_uuid, user_id))                

                general_logger.info(f"Started {side} operation for instance {instance_id}, strategy {strategy_uuid}, user {user_id}.")
                responses.append({"strategy_uuid": strategy_uuid, "side": side, "status": "running"})

            update_instance_query=load_query('update_instance_status.sql')
            db_client.update_data(update_instance_query,(2,instance_id))

            return True, "Instância iniciada com sucesso!"

    except Exception as e:
        general_logger.error(f"Error starting instance operations: {str(e)}")
        return False, str(e)

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

        api_key_id, instance_name, exchange_id, start_date = instance_details[0]

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
            instance_id=instance_id
        )
        
        result=manager.execute_operation_handler(start_date)
        return result

def get_instance_status(instance_id,user_id):
    with get_db_connection() as db_client:
        # Busca detalhes da instância e API Key
        
        query_instance = load_query('select_instance_status.sql')
        instance_status = db_client.fetch_data(query_instance, (instance_id, user_id))
        instance_status=instance_status[0][0]
        return instance_status

def stop_instance_operation(instance_id):
    global operation_managers
    try:
        instance_keys = [key for key in operation_managers if key.startswith(f"{instance_id}_")]

        if not instance_keys:
            return jsonify({"error": "No operations found for the instance"}), 404

        for key in instance_keys:
            manager = operation_managers.pop(key)
            manager.stop_operation()

            # Garante que todas as threads foram finalizadas
            if manager.monitoring_thread and manager.monitoring_thread.is_alive():
                manager.monitoring_thread.join()
            if manager.tp_sl_thread and manager.tp_sl_thread.is_alive():
                manager.tp_sl_thread.join()

            general_logger.info(f"Stopped operation for key {key}.")

        with get_db_connection() as db_client:
            update_instance_query = load_query('update_instance_status.sql')
            db_client.update_data(update_instance_query, (1, instance_id))

        return jsonify({"message": "All operations for the instance stopped successfully"}), 200
    except Exception as e:
        general_logger.error(f"Error stopping instance operations: {str(e)}")
        return jsonify({"error": str(e)}), 500

def get_instances(api_key):
    """
    Busca todas as instâncias salvas para a API Key.
    """
    query = load_query('select_instances_by_api_key.sql')
    try:
        with get_db_connection() as db_client:
            results = db_client.fetch_data(query, (api_key,))
            
            instances = {}
            for row in results:
                instance_id = row[0]  # ID da instância
                if instance_id not in instances:
                    # Cria a instância no dicionário se não existir
                    instances[instance_id] = {
                        "id": instance_id,
                        "api_key": row[1],
                        "name": row[2],
                        "status": row[3],
                        "created_at": row[4],
                        "updated_at": row[5],
                        "strategies": {"buy": None, "sell": None}  # Estruturas separadas para `buy` e `sell`
                    }
                
                # Adiciona a estratégia de `buy` ou `sell`
                strategy_side = row[8]  # `buy` ou `sell`
                instances[instance_id]["strategies"][strategy_side] = {
                    "strategy_id": row[6],
                    "symbol": row[7],
                    "percent": row[9],
                    "condition_limit": row[10],
                    "interval": row[11],
                    "simultaneous_operations": row[12] if strategy_side == 'buy' else None,
                }
            
            return jsonify({"instances": list(instances.values())}), 200
    except Exception as e:
        general_logger.error(f"Error fetching instances: {str(e)}")
        return jsonify({"error": str(e)}), 500