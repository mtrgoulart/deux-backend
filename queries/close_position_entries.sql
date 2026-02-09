UPDATE spot_position_entries
SET status = 'closed', sell_operation_id = %s, closed_at = NOW()
WHERE id = ANY(%s) AND status = 'open';
