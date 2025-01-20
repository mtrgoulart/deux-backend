from flask import jsonify, request
from source.dbmanager import load_query
from source.context import get_db_connection
from log.log import general_logger


from flask import jsonify, request, Response
from source.dbmanager import load_query
from source.context import get_db_connection
from log.log import general_logger
import csv
import io


def get_instance_operations(data):
    """
    Busca as operações com base no `instance_id` e gera um arquivo CSV para download.
    """
    instance_id = data.get("instance_id")

    if not instance_id :
        return jsonify({"error": "Instance ID are required"}), 400

    query = load_query("select_operations_by_instance.sql")

    try:
        with get_db_connection() as db_client:
            # Executa a consulta com o instance_id
            operations = db_client.fetch_data(query, (instance_id,))
            
            if not operations:
                return jsonify({"error": "No operations found for the provided instance ID"}), 404

            # Criação do arquivo CSV em memória
            output = io.StringIO()
            writer = csv.writer(output)

            # Adiciona cabeçalhos
            writer.writerow(["ID", "Date", "Symbol", "Size", "Side", "Price", "Status"])

            # Adiciona linhas com os dados
            for op in operations:
                writer.writerow([
                    op[0],  # ID
                    op[1].isoformat() if op[1] else None,  # Date
                    op[2],  # Symbol
                    float(op[3]) if op[3] else 0.0,  # Size
                    op[4],  # Side
                    float(op[5]) if op[5] else 0.0,  # Price
                    op[6],  # Status
                ])

            # Finaliza a escrita no buffer
            output.seek(0)

            # Cria a resposta Flask para o download
            response = Response(output, mimetype="text/csv")
            response.headers["Content-Disposition"] = f"attachment; filename=instance_{instance_id}_operations.csv"
            return response

    except Exception as e:
        general_logger.error(f"Error fetching operations for instance {instance_id}: {str(e)}")
        return jsonify({"error": str(e)}), 500
