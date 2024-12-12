INSERT INTO operations (date, symbol, size, side, price, status)
VALUES (%s, %s, %s, %s, %s, %s)
RETURNING id;
