select ns.user_id as user_id
,ns.api_key as api_key
,ns.perc_balance_operation as perc_balance_operation
,na.exchange_id as exchange_id
,is2.instance_id as instance_id
from instance_sharing is2 
join neouser_sharing ns
on ns.sharing_id =is2.id 
join neouser_apikeys na
on na.id=ns.api_key
where is2.id=%s
and is2.user_id=%s
and ns.active=true
group by ns.user_id
,ns.api_key
,ns.perc_balance_operation
,na.exchange_id
,is2.instance_id