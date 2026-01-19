UPDATE instances
SET status = %s,start_date=null
WHERE id = %s AND user_id=%s;
