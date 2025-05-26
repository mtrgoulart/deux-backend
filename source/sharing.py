from log.log import general_logger
from source.celery_client import get_client
from source.exchange_interface import get_exchange_interface
from functools import lru_cache
from pydantic import BaseModel, ValidationError
from source.serivce import get_neouser_apikey_from_sharing


# --- Validador de payload com Pydantic ---
class OperationPayload(BaseModel):
    user_id: int                
    api_key: int             
    exchange_id:int
    symbol: str
    side: str
    perc_balance_operation: float = 100.0
    instance_id: int


# --- Função com cache para evitar múltiplas consultas iguais ---
@lru_cache(maxsize=128)
def get_cached_sharing_info(share_id: int, user_id: int):
    return get_neouser_apikey_from_sharing(user_id, share_id)

# --- Builder ---
class OperationBuilder:
    def __init__(self):
        self._operation_data = {}

    def set_share_context(self, share_id, user_id):
        self._operation_data["share_id"] = share_id
        self._operation_data["user_id"] = user_id
        return self

    def set_symbol(self, symbol):
        self._operation_data["symbol"] = symbol
        return self

    def set_side(self, side):
        self._operation_data["side"] = side
        return self

    def fetch_sharing_info_all(self):
        builders = []

        sharing_data_list = get_cached_sharing_info(
            self._operation_data["share_id"],
            self._operation_data["user_id"]  
        )

        if not sharing_data_list:
            raise ValueError("Nenhum compartilhamento encontrado.")

        for data in sharing_data_list:
            builder = OperationBuilder()
            builder._operation_data = {
                "user_id": data["user_id"],
                "api_key": data["api_key"],
                "exchange_id":data["exchange_id"],
                "perc_balance_operation": data.get("perc_balance_operation", 100),
                "symbol": self._operation_data["symbol"],
                "side": self._operation_data["side"],
                "instance_id":data["instance_id"] 
            }
            builders.append(builder)

        return builders

    def build(self):
        try:
            payload = OperationPayload(**self._operation_data)
            return payload.dict()
        except ValidationError as e:
            general_logger.error(f"Payload inválido: {e}")
            raise

    def send(self, countdown=1):
        try:
            payload = self.build()
            get_client().send_task("process_operation", kwargs={"data": payload},queue="ops", countdown=countdown)
            general_logger.info(f"Operação enviada com sucesso: {payload}")
        except Exception as e:
            general_logger.error(f"Erro ao enviar operação: {e}")
            raise

    @staticmethod
    def send_all(builders, countdown=1):
        for builder in builders:
            try:
                builder.send(countdown=countdown)
            except Exception as e:
                general_logger.warning(f"Erro ao enviar operação do lote: {e}")
