from .manager import OperationHandler, IntervalHandler
from .pp import Market
import threading
from log.log import general_logger 


class OperationManager:
    def __init__(self, user_id, data,  exchange_id, api_key, instance_id,share_id):
        self.user_id = user_id
        self.data = data
        self.strategy_id = self.data['strategy_id']
        self.operation_handler = None
        self.exchange_id = exchange_id
        self.api_key = api_key
        self.instance_id = instance_id
        self.share_id=share_id
    
    def execute_operation_handler(self,start_date):
        interval_handler = IntervalHandler(
            self.data['interval'],
            self.data['symbol'],
            self.data['side'],
            self.instance_id,
            self.data['simultaneous_operations']            
        )
        if interval_handler.check_interval():
            general_logger.info('Intervalo valido!')
            market = Market(
            symbol=self.data['symbol'],
            side=self.data['side']
            )
            operation_handler = OperationHandler(
                market_manager=market,
                condition_limit=self.data['condition_limit'],
                interval=self.data['interval'],
                symbol=self.data['symbol'],
                side=self.data['side'],
                percent=self.data['percent'],
                exchange_id=self.exchange_id,
                user_id=self.user_id,
                api_key=self.api_key,
                instance_id=self.instance_id,
                share_id=self.share_id
            )
            result=operation_handler.execute_condition(start_date)
            return result

            
