select es.symbol
from neouser_apikeys na
join exchange e 
on e.id=na.exchange_id 
join exchange e_oficial
on e_oficial.id =e.oficial_exchange
join exchange_symbols es
on es.exchange_id=e_oficial.id
WHERE na.id = %s AND LOWER(es.symbol) LIKE LOWER(%s)
group by es.symbol
ORDER BY es.symbol
LIMIT %s;