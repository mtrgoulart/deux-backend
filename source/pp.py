import configparser
from datetime import datetime
import os


class ConfigLoader:
    def __init__(self, config_file='config.ini'):
        self.config_file = config_file
        self.config = configparser.ConfigParser()
        self.config.read(config_file)
    
    def get(self, section, key):
        return self.config.get(section, key)

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

    def get_market_objects(self, symbol=None, side=None, start_date=None):
        query = self._load_query("select_market_objects.sql")
        params = []
        if symbol:
            query += " AND symbol = %s"
            params.append(symbol)
        if side:
            query += " AND side = %s"
            params.append(side)
        if start_date:
            query += " AND created_at >= %s"
            params.append(start_date)
        query += " GROUP BY symbol, side"
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

    def get_market_objects_as_models(self, symbol=None, side=None, start_date=None):
        grouped_data = self.get_market_objects(symbol, side, start_date)
        market_objects = []
        for symbol, side, markets in grouped_data:
            for market_data in markets:
                market = Market(
                    id=market_data["id"],
                    key=market_data["key"],
                    symbol=market_data["symbol"],
                    side=market_data["side"],
                    indicator=market_data["indicator"],
                    created_at=market_data["created_at"],
                    operation=market_data["operation"],
                )
                market_objects.append(market.to_dict())
        return market_objects

class Operations:
    def __init__(self, db_manager):
        self.db_manager = db_manager

    def save_operation_to_db(self, operation_data, price, status="realizada"):
        query = self._load_query("insert_operation.sql")
        params = (
            datetime.now(),
            operation_data["symbol"],
            operation_data["size"],
            operation_data["side"],
            price,
            status,
        )
        return self.db_manager.insert_data(query, params)

    def get_last_operations_from_db(self, symbol, limit):
        query = self._load_query("select_last_operations.sql")
        last_ops = self.db_manager.fetch_data(query, (symbol, limit))
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
