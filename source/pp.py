import configparser
from datetime import datetime
import os


from dotenv import load_dotenv
import os

load_dotenv()


class ConfigLoader:
    def __init__(self, config_file='config.ini'):
        self.config = configparser.ConfigParser()
        self.config.read(config_file)

        # Mapeamento opcional: [seção][chave] -> VARIÁVEL_ENV
        self.env_mapping = {
            'database': {
                'dbname': 'DB_NAME',
                'user': 'DB_USER',
                'password': 'DB_PASSWORD',
                'host': 'DB_HOST',
                'port': 'DB_PORT'
            },
            'logging': {
                'log_file': 'LOG_FILE',
                'log_level': 'LOG_LEVEL'
            },
            'data': {
                'regex_pattern': 'REGEX_PATTERN',
                'data_fields': 'DATA_FIELDS'
            },
            'table': {
                'table_name': 'TABLE_NAME'
            },
            'rabbitmq': {
                'host': 'RABBITMQ_HOST',
                'queue_name': 'RABBITMQ_QUEUE',
                'user': 'RABBITMQ_USER',
                'pwd': 'RABBITMQ_PWD'
            }
        }

    def get(self, section, key):
        # Prioriza variável de ambiente, se mapeada e presente
        env_key = self.env_mapping.get(section, {}).get(key)
        if env_key:
            env_value = os.getenv(env_key)
            if env_value is not None:
                return env_value
        raise KeyError(f"Configuração '{section}.{key}' não encontrada no .env")

class Market:
    def __init__(self, id=None, key=None, symbol=None, side=None, indicator=None, created_at=None, operation=None, size=None, order_type=None, price=None):
        self.id = id
        self.key = key
        self.symbol = symbol
        self.side = side
        self.indicator = indicator
        self.created_at = created_at
        self.operation = operation
        self.size = size
        self.order_type = order_type
        self.price = price

    def to_dict(self):
        return {
            "id": self.id,
            "key": self.key,
            "symbol": self.symbol,
            "side": self.side,
            "indicator": self.indicator,
            "created_at": self.created_at,
            "operation": self.operation,
            "size": self.size,
            "order_type": self.order_type,
            "price": self.price
        }

class Condition:
    def __init__(self,tp,sl,open_operations_condition,size,signals_condition):
        self.tp=tp
        self.sl=sl
        self.open_operations_condition=open_operations_condition
        self.size=size
        self.signals_condition=signals_condition
    

class WebhookData:
    def __init__(self, db_manager):
        self.db_manager = db_manager
        self.queries_path = os.path.join(os.path.dirname(__file__), "queries")

    def _load_query(self, query_file):
        """
        Carrega a query SQL do arquivo especificado.
        """
        # Construir o caminho absoluto para o arquivo
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        filepath = os.path.join(project_root, "queries", query_file)

        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Query file not found: {filepath}")

        with open(filepath, "r") as file:
            return file.read()

    def get_data(self):
        query = self._load_query("select_webhook_data.sql")
        return self.db_manager.fetch_data(query)

    def get_data_at_index(self, index):
        query = self._load_query("select_webhook_data_by_id.sql")
        return self.db_manager.fetch_data(query, (index,))    
    
    def get_market_objects(self, instance_id,symbol, side, start_date):
        query = self._load_query("select_market_objects.sql")
        params=(instance_id,symbol,side,start_date)
        
        return self.db_manager.fetch_data(query, tuple(params))

    def update_market_object_at_index(self, webhook_id, data):
        query = self._load_query("update_market_object.sql")
        params = (
            data["operation_task_id"],
            webhook_id,
        )
        self.db_manager.insert_data(query, params)

    def _parse_data(self, data_str):
        data_items = data_str.split(',')
        data_dict = {}
        for item in data_items:
            key, value = item.split('=')
            data_dict[key.strip()] = value.strip()
        return data_dict

    def get_market_objects_as_models(self, instance_id,symbol, side, start_date):
        grouped_data = self.get_market_objects(instance_id,symbol, side, start_date)
        market_objects = []
        for symbol, side, markets in grouped_data:
            for market_data in markets:
                market = Market(
                    id=market_data["id"],
                    key=market_data["key"],
                    symbol=market_data["symbol"],
                    side=market_data["side"],
                    indicator=market_data["indicator_id"],
                    created_at=market_data["created_at"],
                    operation=market_data["operation"],
                )
                market_objects.append(market.to_dict())
        return market_objects
    

class Operations:
    def __init__(self, db_manager):
        self.db_manager = db_manager    

    def get_last_operations_from_db(self, instance_id, symbol, limit):
        query = self._load_query("select_last_operations.sql")
        last_ops = self.db_manager.fetch_data(query, (instance_id,symbol, limit))
        columns = ["id", "date", "symbol", "size", "side"]
        return [dict(zip(columns, op)) for op in last_ops] if last_ops else []

    def _load_query(self, query_file):
        """
        Carrega a query SQL do arquivo especificado.
        """
        # Construir o caminho absoluto para o arquivo
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        filepath = os.path.join(project_root, "queries", query_file)

        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Query file not found: {filepath}")

        with open(filepath, "r") as file:
            return file.read()


    