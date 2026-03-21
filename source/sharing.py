from typing import Optional
from log.log import general_logger
from source.celery_client import get_client
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

        sharing_data_list = get_neouser_apikey_from_sharing(
            self._operation_data["user_id"],
            self._operation_data["share_id"]
        )

        if not sharing_data_list:
            raise ValueError("Nenhum compartilhamento encontrado.")

        for data in sharing_data_list:
            sub_mode = data.get("size_mode", "percentage")
            sub_value = data["subscriber_size_value"]
            max_cap = data.get("max_usdt_cap")

            if sub_mode == "flat_value":
                if max_cap is not None and sub_value is not None and sub_value > max_cap:
                    general_logger.warning(
                        f"Subscriber {data['user_id']} flat_value {sub_value} > max USDT cap {max_cap}. Skipping."
                    )
                    continue  # skip this subscriber

                builder = OperationBuilder()
                builder._operation_data = {
                    "user_id": data["user_id"],
                    "api_key": data["api_key"],
                    "exchange_id": data["exchange_id"],
                    "symbol": self._operation_data["symbol"],
                    "side": self._operation_data["side"],
                    "instance_id": data["instance_id"],
                    "size_mode": "flat_value",
                    "flat_value": sub_value,
                    "max_amount_size": max_cap,
                    "perc_balance_operation": 100.0
                }
            else:  # percentage
                builder = OperationBuilder()
                builder._operation_data = {
                    "user_id": data["user_id"],
                    "api_key": data["api_key"],
                    "exchange_id": data["exchange_id"],
                    "symbol": self._operation_data["symbol"],
                    "side": self._operation_data["side"],
                    "instance_id": data["instance_id"],
                    "size_mode": "percentage",
                    "flat_value": None,
                    "perc_balance_operation": sub_value / 100.0 if sub_value else 1.0,
                    "max_amount_size": max_cap
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
