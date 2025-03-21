import requests
import json
import time
from datetime import datetime, timedelta,timezone
from source.dbmanager import DatabaseClient

# Configuração do caminho do JSON e data de início
SYMBOLS_FILE = 'view/symbols.json'
START_DATE = datetime(2025, 3, 20, 0, 0, 0)

# Configurações do banco
db = DatabaseClient(
    dbname='deux_QA',
    user='consumer_adm',
    password='criandta0',
    host='149.102.154.104',
    port=5432
)

# Cria a tabela se não existir
def create_table():
    query = """
        CREATE TABLE IF NOT EXISTS public.hourly_prices (
            date TIMESTAMP NOT NULL,
            symbol VARCHAR(55) NOT NULL,
            price NUMERIC NOT NULL,
            CONSTRAINT hourly_prices_pkey PRIMARY KEY (date, symbol)
        );
    """
    db.insert_data(query, None)

# Carrega os símbolos do arquivo JSON
def load_symbols():
    with open(SYMBOLS_FILE, 'r') as f:
        data = json.load(f)
        return data['symbols']

# Busca candles de 1h da OKX a partir de um período
def get_hourly_candles(symbol: str, start: datetime, end: datetime):
    candles = []
    dt = start

    while dt < end:
        end_dt = dt + timedelta(hours=1000)
        if end_dt > end:
            end_dt = end

        after = int(dt.timestamp() * 1000)
        limit = min(1000, int((end_dt - dt).total_seconds() // 3600))

        url = f"https://www.okx.com/api/v5/market/candles?instId={symbol}&bar=1H&after={after}&limit={limit}"
        response = requests.get(url)

        if response.status_code == 200:
            data = response.json().get("data", [])
            for candle in data:
                ts = int(candle[0]) // 1000
                date = datetime.fromtimestamp(ts, tz=timezone.utc)
                o, h, l, c = map(float, candle[1:5])
                avg_price = round((o + h + l + c) / 4, 6)
                candles.append((date, symbol, avg_price))
        else:
            print(f"Erro ao buscar dados de {symbol}: {response.status_code} - {response.text}")
        dt = end_dt
        time.sleep(0.8)

    return candles

# Salva os dados no banco com upsert
def save_prices(prices):
    query = """
        INSERT INTO public.hourly_prices (date, symbol, price)
        VALUES (%s, %s, %s)
        ON CONFLICT (date, symbol)
        DO UPDATE SET price = EXCLUDED.price;
    """
    for row in prices:
        db.insert_data(query, row)

# Execução principal
if __name__ == "__main__":
    create_table()
    symbols = load_symbols()
    now = datetime.now(tz=timezone.utc)

    for symbol in symbols:
        print(f"🔄 Buscando {symbol} de {START_DATE} até {now}...")
        candles = get_hourly_candles(symbol, START_DATE, now)
        save_prices(candles)
        print(f"✅ {symbol}: {len(candles)} registros salvos.\n")

    print("🏁 Finalizado com sucesso.")
