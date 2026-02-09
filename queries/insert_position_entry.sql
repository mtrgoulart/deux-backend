INSERT INTO spot_position_entries (operation_id, instance_id, user_id, symbol, base_currency, base_qty)
VALUES (%s, %s, %s, %s, %s, %s)
RETURNING id;
