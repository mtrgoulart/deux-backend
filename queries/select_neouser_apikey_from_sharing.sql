SELECT ns.user_id AS user_id
      ,ns.api_key AS api_key
      ,na.exchange_id AS exchange_id
      ,is2.instance_id AS instance_id
      ,ns.size_amount AS subscriber_size_value
      ,ns.size_mode AS subscriber_size_mode
      ,cs_sub.size_amount AS max_usdt_cap
FROM instance_sharing is2
JOIN neouser_sharing ns ON ns.sharing_id = is2.id
JOIN neouser_apikeys na ON na.id = ns.api_key
JOIN copytrading_sharing cts ON cts.sharing_id = is2.id
JOIN copytrading_subscription cs_sub
  ON cs_sub.copytrading_id = cts.copytrading_id AND cs_sub.user_id = ns.user_id
WHERE ns.active = true
  AND is2.id = %s AND is2.user_id = %s
GROUP BY ns.user_id
        ,ns.api_key
        ,na.exchange_id
        ,is2.instance_id
        ,ns.size_amount
        ,ns.size_mode
        ,cs_sub.size_amount
