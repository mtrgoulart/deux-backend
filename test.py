from celeryManager.tasks.sharing import process_sharing_operations

data={"share_id":1,
      "user_id":1,
      "symbol":'BTC-USDT',
      "side":'buy'
      }

massage=process_sharing_operations(data)
print(massage)