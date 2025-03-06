UPDATE instances
SET status = %s,start_date=NOW()
WHERE id = %s;