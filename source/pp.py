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

    def update_data_at_index(self, index, new_data_str):
        new_data = self._parse_data(new_data_str)
        query = self._load_query("update_webhook_data.sql")
        params = (new_data["key"], new_data["symbol"], new_data["side"], int(new_data["indicator"]), index)
        self.db_manager.insert_data(query, params)

    def update_market_object_at_index(self, id, new_data):
        query = self._load_query("update_market_object.sql")
        params = (
            new_data["symbol"],
            new_data["side"],
            new_data["indicator"],
            new_data["operation"],
            id,
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

    def save_operation_to_db(self, operation_data, price, instance_id, status="realizada"):
        try:
            query = self._load_query("insert_operation.sql")
            params = (
                datetime.now(),
                operation_data["symbol"],
                operation_data["size"],
                operation_data["side"],
                price,
                status,
                instance_id
            )
            opeartion_id=self.db_manager.insert_data_returning(query, params)
            if opeartion_id:
                return opeartion_id,None
            else:
                None,'No operation ID returned'
            
        except Exception as e:
            error=f'Erro ao salvar operação no banco: {e}'
            return None, error

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


    def save_tp_sl_to_db(self, instance_id, api_key, tp_price, sl_price,operation_id):
        """
        Salva os valores de Take Profit (TP) e Stop Loss (SL) na tabela `positions`.
        """
        try:
            query = self._load_query("insert_tp_sl.sql")  # Carregar a query correta
            
            if tp_price is not None:
                self.db_manager.insert_data(query, (instance_id, api_key, 'TP', float(tp_price), 'active',operation_id))

            if sl_price is not None:
                self.db_manager.insert_data(query, (instance_id, api_key, 'SL', float(sl_price), 'active',operation_id))

            return True, None

        except Exception as e:
            error = f'Erro ao salvar TP/SL no banco: {e}'
            return False, error


    def get_tp_sl_prices(self, instance_id, api_key):
        """
        Obtém os preços de Take Profit (TP) e Stop Loss (SL) para uma instância e símbolo.
        """
        try:
            query = self._load_query("select_tp_sl_prices.sql")
            results = self.db_manager.fetch_data(query, (instance_id, api_key))

            tp_price, sl_price = None, None
            tp_status, sl_status= None, None
            for record in results:
                if record[0] == "TP":
                    tp_price = float(record[1])
                    tp_status=record[2]
                elif record[0] == "SL":
                    sl_price = float(record[1])
                    sl_status=record[2]

            return tp_price, sl_price, tp_status, sl_status
        except Exception as e:
            print(f"Erro ao obter TP/SL do banco: {e}")
            return None, None, None, None

    def delete_tp_sl(self, instance_id, symbol):
        """
        Remove os registros de TP e SL da tabela `positions`.
        """
        try:
            query = self._load_query("delete_tp_sl.sql")
            rows_affected = self.db_manager.delete_data(query, (instance_id, symbol))
            return rows_affected
        except Exception as e:
            print(f"Erro ao deletar TP/SL do banco: {e}")
            return 0

    def update_tp_sl_status(self, instance_id, api_key, new_tp_status, new_sl_status):
        """
        Atualiza os status de TP e SL na tabela `positions` quando um dos dois é executado.
        """
        try:
            query = self._load_query("update_tp_sl_status.sql")

            self.db_manager.update_data(query, (new_tp_status, instance_id, api_key, 'TP'))
            self.db_manager.update_data(query, (new_sl_status, instance_id, api_key, 'SL'))

            return True
        except Exception as e:
            print(f"Erro ao atualizar status de TP/SL no banco: {e}")
            return False
        
    def update_sl_price(self, instance_id, api_key, new_sl_price):
        """
        Atualiza o preço do Stop Loss (SL) na tabela `positions`.
        """
        try:
            query = self._load_query("update_sl_price.sql")
            self.db_manager.update_data(query, (float(new_sl_price), instance_id, api_key))
            return True
        except Exception as e:
            print(f"Erro ao atualizar SL no banco: {e}")
            return False
