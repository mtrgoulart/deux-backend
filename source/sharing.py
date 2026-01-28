from typing import Optional
from log.log import general_logger
from source.celery_client import get_client
from functools import lru_cache
from pydantic import BaseModel, ValidationError
from source.sharing_serivce import get_neouser_apikey_from_sharing


# --- Validador de payload com Pydantic ---
class OperationPayload(BaseModel):
    user_id: int
    api_key: int
    exchange_id: int
    symbol: str
    side: str
    perc_balance_operation: float = 100.0
    instance_id: int
    max_amount_size: Optional[float] = None
    size_mode: str = "percentage"
    flat_value: Optional[float] = None


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
    
    def set_perc_size(self, perc_size):
        self._operation_data["perc_size"] = perc_size
        return self

    def set_side(self, side):
        self._operation_data["side"] = side
        return self

    def set_size_mode(self, size_mode):
        """Set the sizing mode (percentage or flat_value)."""
        self._operation_data["size_mode"] = size_mode
        return self

    def set_flat_value(self, flat_value):
        """Set the flat value amount for flat_value mode."""
        self._operation_data["flat_value"] = flat_value
        return self

    def fetch_sharing_info_all(self):
        builders = []

        sharing_data_list = get_cached_sharing_info(
            self._operation_data["share_id"],
            self._operation_data["user_id"]
        )

        if not sharing_data_list:
            raise ValueError("Nenhum compartilhamento encontrado.")

        size_mode = self._operation_data.get("size_mode", "percentage")
        flat_value = self._operation_data.get("flat_value")

        for data in sharing_data_list:
            subscriber_max = data["max_amount_size"]

            # Cap flat_value to subscriber's max_amount_size if configured
            effective_flat_value = flat_value
            if size_mode == "flat_value" and flat_value is not None and subscriber_max is not None:
                if flat_value > subscriber_max:
                    effective_flat_value = subscriber_max
                    general_logger.info(
                        f"Subscriber {data['user_id']} flat_value capped: {flat_value} -> {subscriber_max}"
                    )

            builder = OperationBuilder()
            builder._operation_data = {
                "user_id": data["user_id"],
                "api_key": data["api_key"],
                "exchange_id": data["exchange_id"],
                "perc_balance_operation": self._operation_data["perc_size"],
                "symbol": self._operation_data["symbol"],
                "side": self._operation_data["side"],
                "instance_id": data["instance_id"],
                "max_amount_size": subscriber_max,
                "size_mode": size_mode,
                "flat_value": effective_flat_value
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
            get_client().send_task("trade.execute_operation", kwargs={"data": payload}, queue="ops", countdown=countdown)
            general_logger.info(f"Operação enviada com sucesso para trade.execute_operation: {payload}")
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
