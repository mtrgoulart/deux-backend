from source.client import OKXClient
from source.dbmanager import DatabaseClient, load_query

# --- Credenciais da OKX ---
credentials = {
    "api_key": "a4b8f73e-6cca-49bf-9ad6-aceaa7fb5df1",
    "passphrase": "Criandta0!",
    "secret_key": "E078FF54F0BC68654F90C90A631BCC07"
}

# --- Conexão com o banco ---
db_config = {
    "dbname": "deux_QA",
    "user": "consumer_adm",
    "password": "criandta0",
    "host": "149.102.154.104",
    "port": 5432
}

# Instanciando os clientes
okx_client = OKXClient(credentials)
db_client = DatabaseClient(**db_config)

# Carrega a query de inserção
insert_query = '''
INSERT INTO okx_operations (
    ord_id, trade_id, inst_id, side, fill_sz, fill_px, fee, ts, parsed_time
) VALUES (
    %s, %s, %s, %s, %s, %s, %s, %s, %s
)
ON CONFLICT (trade_id) DO NOTHING;
'''

# Coleta os trades
trades = okx_client.get_recent_trades_last_7_days()

# Insere os dados no banco
for trade in trades:
    params = (
        trade.get("ordId"),
        trade.get("tradeId"),
        trade.get("instId"),
        trade.get("side"),
        float(trade.get("fillSz", 0)),
        float(trade.get("fillPx", 0)),
        float(trade.get("fee", 0)),
        int(trade.get("ts", 0)),
        trade.get("parsed_time"),
    )
    db_client.insert_data(insert_query, params)
