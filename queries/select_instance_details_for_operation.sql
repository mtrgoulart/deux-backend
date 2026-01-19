SELECT
    i.api_key,
    na.exchange_id,
    i.symbol
FROM
    instances i
JOIN
    neouser_apikeys na ON na.id = i.api_key
WHERE
    i.user_id = %s AND i.id = %s;
