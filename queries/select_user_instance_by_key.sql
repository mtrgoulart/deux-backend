select i.user_id
,i.id
,i.symbol
,i2.id
,i2.delay_seconds
from instances i
join indicators i2
on i.user_id =i2.user_id
and i2.instance_id=i.id
where key=%s