from decimal import Decimal
from source.context import get_db_connection
from source.dbmanager import load_query
from log.log import general_logger


def get_open_position(instance_id, user_id, symbol):
    """
    Get total open position quantity and entry IDs for a given instance/user/symbol.

    Returns:
        tuple: (total_qty: Decimal, entry_ids: list[int])
    """
    query = load_query('select_open_position.sql')
    with get_db_connection() as db_client:
        db_client.cursor.execute(query, (instance_id, user_id, symbol))
        rows = db_client.cursor.fetchall()

    if not rows:
        return (Decimal('0'), [])

    total_qty = Decimal('0')
    entry_ids = []
    for row in rows:
        entry_ids.append(row[0])
        total_qty += Decimal(str(row[1]))

    return (total_qty, entry_ids)


def add_position_entry(operation_id, instance_id, user_id, symbol, base_currency, base_qty):
    """
    Insert a new open position entry for a buy operation.

    Returns:
        int: The new entry ID.
    """
    query = load_query('insert_position_entry.sql')
    with get_db_connection() as db_client:
        db_client.cursor.execute(query, (
            operation_id, instance_id, user_id, symbol, base_currency, str(base_qty)
        ))
        entry_id = db_client.cursor.fetchone()[0]
        db_client.conn.commit()

    general_logger.info(f"Position entry created (ID: {entry_id}) for operation {operation_id} | inst:{instance_id} user:{user_id} {symbol} qty:{base_qty}")
    return entry_id


def close_position_entries(entry_ids, sell_operation_id):
    """
    Close open position entries after a sell operation.

    Args:
        entry_ids: List of spot_position_entries IDs to close.
        sell_operation_id: The operation ID of the sell that consumed these entries.
    """
    if not entry_ids:
        return

    query = load_query('close_position_entries.sql')
    with get_db_connection() as db_client:
        db_client.cursor.execute(query, (sell_operation_id, entry_ids))
        db_client.conn.commit()

    general_logger.info(f"Closed {len(entry_ids)} position entries for sell operation {sell_operation_id}")
