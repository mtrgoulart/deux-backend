SELECT id, base_qty
FROM spot_position_entries
WHERE instance_id = %s AND user_id = %s AND symbol = %s AND status = 'open'
ORDER BY created_at ASC;
