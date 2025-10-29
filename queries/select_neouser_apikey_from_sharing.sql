select ns.user_id as user_id
,ns.api_key as api_key
,na.exchange_id as exchange_id
,is2.instance_id as instance_id
,ns.size_amount as max_amount_size
from instance_sharing is2 
join neouser_sharing ns
on ns.sharing_id =is2.id 
join neouser_apikeys na
on na.id=ns.api_key
where ns.active=true
group by ns.user_id
,ns.api_key
,na.exchange_id
,is2.instance_id
,ns.size_amount