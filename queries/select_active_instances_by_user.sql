-- select_active_instances_by_user.sql
SELECT
    id
FROM instances
WHERE user_id = %s AND status = 2;
