-- select_active_instances_by_user.sql
-- Active PSL instances for a user within one environment. Panic is now
-- environment-scoped: a live panic touches only live instances, a demo panic
-- only demo instances. Params: (user_id, environment)
SELECT
    i.id
FROM instances i
JOIN neouser_apikeys nak ON i.api_key = nak.id
WHERE i.user_id = %s
  AND i.status = 2
  AND i.participate_psl = TRUE
  AND nak.environment = %s;
