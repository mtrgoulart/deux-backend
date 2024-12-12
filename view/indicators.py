from flask import jsonify
from source.dbmanager import load_query
from log.log import general_logger
from source.context import get_db_connection  # Usa o gerenciador de conexão do context.py


def save_indicators(data, user_id):
    """
    Salva indicadores no banco de dados.
    """
    indicators = data.get('indicators', [])
    query = load_query('insert_indicator.sql')
    try:
        with get_db_connection() as db_client:
            for indicator in indicators:
                params = (
                    indicator['id'],
                    indicator['strategy_id'],
                    user_id,
                    indicator['side'],
                    indicator['mandatory'],
                )
                db_client.insert_data(query, params)
        return jsonify({"message": "Indicators saved successfully"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
def remove_indicators(data, user_id):
    """
    Remove indicadores do banco de dados.
    """
    indicators = data.get('indicators', [])
    query = load_query('delete_indicator.sql')
    try:
        with get_db_connection() as db_client:
            for indicator_id in indicators:
                params = (indicator_id, user_id)
                db_client.insert_data(query, params)
        return jsonify({"message": "Indicators removed successfully"}), 200
    except Exception as e:
        general_logger.error(f"Error removing indicators: {str(e)}")
        return jsonify({"error": str(e)}), 500


def get_indicators(strategy_id, side, user_id):
    """
    Busca indicadores do banco de dados.
    """
    query = load_query('select_indicators.sql')
    try:
        with get_db_connection() as db_client:
            # Obter resultados da consulta
            results = db_client.fetch_data(query, (strategy_id, side, user_id))
            # Transformar os resultados em dicionários
            indicators = [
                {
                    "id": row[0],  # ID do indicador
                    "strategy_id": row[1],  # ID da estratégia
                    "side": row[2],  # Lado (buy/sell)
                    "mandatory": row[3],  # Obrigatório (booleano ou equivalente)
                }
                for row in results
            ]
            return jsonify({"indicators": indicators}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500