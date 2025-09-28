# celeryManager/tasks/account_tasks.py

from celery import shared_task
from source.exchange_interface import get_exchange_interface
# Se você tiver um logger central, é uma boa ideia usá-lo aqui
# from log.log import general_logger

@shared_task(name="account.get_balance")
def get_account_balance(data: dict):
    """
    Busca o saldo da conta de um usuário em uma exchange específica.

    Esta tarefa recebe os IDs necessários, inicializa a interface da exchange
    correta e chama o método get_balance().

    Args:
        data (dict): Um dicionário contendo:
            - user_id (int): O ID do usuário.
            - exchange_id (int): O ID da exchange.
            - api_key_id (int): O ID da chave de API a ser usada.

    Returns:
        dict: Um dicionário com o status e o resultado da operação.
              Ex: {'status': 'success', 'balance': [...] } ou
                  {'status': 'error', 'message': '...' }
    """
    user_id = data.get("user_id")
    exchange_id = data.get("exchange_id")
    # A interface espera 'api_key', então renomeamos para clareza
    api_key_id = data.get("api_key_id")

    # Log para facilitar o debug
    print(f"[Task account.get_balance] Recebido para user:{user_id}, exchange:{exchange_id}")

    # Validação básica das entradas
    if not all([user_id, exchange_id, api_key_id]):
        return {
            "status": "error",
            "message": "Dados insuficientes. 'user_id', 'exchange_id' e 'api_key_id' são obrigatórios."
        }

    try:
        # 1. Usa sua função para obter a interface correta (real ou demo)
        interface = get_exchange_interface(
            exchange_id=exchange_id,
            user_id=user_id,
            api_key=api_key_id
        )

        # 2. Chama o método get_balance() da interface
        balance_result = interface.get_balance()

        # 3. Retorna o resultado com sucesso
        print(f"[Task account.get_balance] Saldo obtido com sucesso para user:{user_id}")
        return {
            "status": "success",
            "balance": balance_result
        }

    except Exception as e:
        # Em caso de qualquer erro (API fora do ar, chaves inválidas, etc.),
        # captura a exceção e retorna uma mensagem de erro clara.
        error_message = f"Falha ao buscar saldo para user:{user_id} na exchange:{exchange_id}. Erro: {e}"
        print(f"[Task account.get_balance] {error_message}")
        return {
            "status": "error",
            "message": error_message
        }