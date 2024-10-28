import configparser
import psycopg2
from .dbmanager import DatabaseClient
from datetime import datetime


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
    _instance = None

    def __new__(cls, db_params):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, db_params):
        if not hasattr(self, 'db_client'):
            self.db_client = psycopg2.connect(**db_params)
            self.cursor = self.db_client.cursor()
            print("Conexão com o banco de dados estabelecida.")

    def fetch_data(self, query, params=()):
        try:
            self.cursor.execute(query, params)
            return self.cursor.fetchall()
        except Exception as e:
            print(f"Erro ao buscar dados: {e}")
            self.db_client.rollback()
            return []

    def execute_query(self, query, params=()):
        try:
            self.cursor.execute(query, params)
            self.db_client.commit()
        except Exception as e:
            print(f"Erro ao executar consulta: {e}")
            self.db_client.rollback()

    def add_data(self, data_str):
        data_dict = self._parse_data(data_str)
        query = """
            INSERT INTO webhook_data (key, symbol, side, indicator)
            VALUES (%s, %s, %s, %s)
        """
        params = (data_dict["key"], data_dict["symbol"], data_dict["side"], int(data_dict["indicator"]))
        self.execute_query(query, params)

    def add_object(self, market_object):
        if isinstance(market_object, Market):
            query = """
                INSERT INTO market_data (symbol, strategy, ...)
                VALUES (%s, %s, ...)
            """
            params = (market_object.symbol, market_object.strategy, ...)
            self.execute_query(query, params)
        else:
            raise TypeError("Expected an instance of Market class.")

    def get_data(self):
        query = "SELECT * FROM webhook_data"
        return self.fetch_data(query)

    def get_data_at_index(self, index):
        query = "SELECT * FROM webhook_data WHERE id = %s"
        return self.fetch_data(query, (index,))

    def get_market_objects(self, symbol=None, side=None, start_date=None):
        # Base da consulta
        query = """
            SELECT symbol, side, json_agg(row_to_json(webhook_data)) AS markets
            FROM webhook_data
            WHERE operation IS NULL
        """
        params = []

        # Adiciona filtros se `symbol` e `side` forem fornecidos
        if symbol:
            query += " AND symbol = %s"
            params.append(symbol)
        if side:
            query += " AND side = %s"
            params.append(side)
        if start_date:
            query += " AND created_at >= %s"
            params.append(start_date)
        
        # Agrupamento por `symbol` e `side`
        query += " GROUP BY symbol, side"
        
        return self.fetch_data(query, tuple(params))

    def get_market_object_at_index(self, index):
        query = "SELECT * FROM webhook_data WHERE id = %s"
        return self.fetch_data(query, (index,))

    def update_data_at_index(self, index, new_data_str):
        new_data = self._parse_data(new_data_str)
        query = """
            UPDATE webhook_data
            SET key = %s, symbol = %s, side = %s, indicator = %s
            WHERE id = %s
        """
        params = (new_data["key"], new_data["symbol"], new_data["side"], int(new_data["indicator"]), index)
        self.execute_query(query, params)

    def update_market_object_at_index(self, id, new_data):
        # Atualiza somente as colunas existentes na tabela webhook_data
        query = """
            UPDATE webhook_data
            SET symbol = %s, side = %s, indicator = %s, operation = %s
            WHERE id = %s
        """
        params = (
            new_data["symbol"], 
            new_data["side"],
            new_data["indicator"], 
            new_data["operation"], 
            id
        )
        self.execute_query(query, params)

    def _parse_data(self, data_str):
        data_items = data_str.split(',')
        data_dict = {}
        for item in data_items:
            key, value = item.split('=')
            data_dict[key.strip()] = value.strip()
        return data_dict

    def reset_data(self):
        self.execute_query("DELETE FROM webhook_data")
        self.execute_query("DELETE FROM market_data")

    def get_market_objects_as_models(self, symbol=None, side=None, start_date=None):
        grouped_data = self.get_market_objects(symbol, side, start_date)
        market_objects = []
        
        for symbol, side, markets in grouped_data:
            for market_data in markets:  # Itera sobre cada mercado no grupo
                market = Market(
                    id=market_data["id"],
                    key=market_data["key"],
                    symbol=market_data["symbol"],
                    side=market_data["side"],
                    indicator=market_data["indicator"],
                    created_at=market_data["created_at"],
                    operation=market_data["operation"]
                )
                market_objects.append(market.to_dict())
        
        return market_objects

    def save_operation_to_db(self, operation_data):
        query = """
            INSERT INTO operations (date, symbol, size, side)
            VALUES (%s, %s, %s, %s)
            RETURNING id
        """
        params = (
            datetime.now(),
            operation_data["symbol"],
            operation_data["size"],
            operation_data["side"]
        )
        try:
            self.cursor.execute(query, params)
            new_id = self.cursor.fetchone()[0]  # Captura o id gerado
            self.db_client.commit()
            return new_id
        except Exception as e:
            print(f"Erro ao salvar a operação: {e}")
            self.db_client.rollback()
            return None

    def get_last_operation_from_db(self, symbol):
        query = """
            SELECT id
            ,date
            ,symbol
            ,size
            ,side 
            FROM operations
            WHERE symbol = %s
            ORDER BY date DESC
            LIMIT 1;
        """
        last_op = self.fetch_data(query, (symbol,))
        
        # Defina os nomes das colunas conforme esperado na consulta
        columns = ["id", "date", "symbol", "size", "side"]
        
        # Retorne os dados no formato de dicionário
        return dict(zip(columns, last_op[0])) if last_op else None



class LastOperation:
    def __init__(self, fill_id, order_id, symbol, side, fill_size, fill_price, fee, time):
        self.fill_id = fill_id
        self.order_id = order_id
        self.symbol = symbol
        self.side = side
        self.fill_size = fill_size
        self.fill_price = fill_price
        self.fee = fee
        self.time = time  # O tempo da última operação