SELECT
    i.api_key,
    na.exchange_id,
    i.symbol,
    is2.id
FROM
    instances i
JOIN
    neouser_apikeys na ON na.id = i.api_key
LEFT JOIN
    instance_sharing is2 ON is2.instance_id = i.id
WHERE
    i.user_id = %s AND i.id = %s;
