import requests
import json
import time
from datetime import datetime, timedelta, timezone
from source.dbmanager import DatabaseClient

SYMBOLS_FILE = 'view/symbols.json'
FALLBACK_START_DATE = datetime(2025, 3, 20, 0, 0, 0, tzinfo=timezone.utc)

db = DatabaseClient(
    dbname='deux_QA',
    user='consumer_adm',
    password='criandta0',
    host='149.102.154.104',
    port=5432
)

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

def load_symbols():
    with open(SYMBOLS_FILE, 'r') as f:
        data = json.load(f)
        return data['symbols']

def get_last_timestamp(symbol):
    query = """
        SELECT MAX(date) FROM public.hourly_prices WHERE symbol = %s;
    """
    result = db.fetch_data(query, (symbol,))
    if result and result[0][0]:
        last_dt = result[0][0]
        if last_dt.tzinfo is None:
            last_dt = last_dt.replace(tzinfo=timezone.utc)
        return last_dt + timedelta(hours=1)
    return FALLBACK_START_DATE

def get_hourly_candles(symbol: str, start: datetime):
    candles = []
    dt = start
    after = int(dt.timestamp() * 1000)
    url = f"https://www.okx.com/api/v5/market/candles?instId={symbol}&bar=1H&after={after}&limit=100"
    response = requests.get(url)    
    if response.status_code == 200:
        data = response.json().get("data", [])
        data = sorted(data, key=lambda x: int(x[0]))
        if not data:
            print('not data') 
        for candle in data:
            ts = int(candle[0]) // 1000
            date = datetime.fromtimestamp(ts, tz=timezone.utc)
            o, h, l, c = map(float, candle[1:5])
            avg_price = round((o + h + l + c) / 4, 6)
            candles.append((date, symbol, avg_price))
            print(date) 
    else:
        print(f"Erro ao buscar dados de {symbol}: {response.status_code} - {response.text}")
    time.sleep(0.8)

    return candles

def save_prices(prices):
    query = """
        INSERT INTO public.hourly_prices (date, symbol, price)
        VALUES (%s, %s, %s)
        ON CONFLICT (date, symbol)
        DO UPDATE SET price = EXCLUDED.price;
    """
    for row in prices:
        db.insert_data(query, row)

if __name__ == "__main__":
    create_table()
    symbols = load_symbols()
    now = datetime.now(tz=timezone.utc)

    for symbol in symbols:
        start_date = get_last_timestamp(symbol)
        print(f"🔄 Buscando {symbol} de {now}...")
        candles = get_hourly_candles(symbol, now)
        print(f"1º - ✅ {symbol}: {len(candles)} registros pegos pela API.")
        save_prices(candles)
        print(f"2º - ✅ {symbol}: {len(candles)} registros salvos.\n")

    print("🏁 Finalizado com sucesso.")
