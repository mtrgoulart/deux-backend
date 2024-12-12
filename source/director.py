from .manager import OperationHandler, IntervalHandler, conditionHandler
from .pp import Market
from datetime import datetime
import pytz
import threading

class OperationManager:
    def __init__(self, user_id, data,strategy_id):
        self.user_id = user_id
        self.data = data
        self.strategy_id = strategy_id
        self.stop_event = threading.Event()
        self.monitoring_thread = None
        self.operation_handler = None

    def start_operation(self):
        self.market = Market(
            symbol=self.data['symbol'],
            side=self.data['side']
        )
        self.condition_handler = conditionHandler(self.data['condition_limit'])
        self.operation_handler = OperationHandler(
            market_manager=self.market,
            condition_handler=self.condition_handler,
            interval=self.data['interval'],
            symbol=self.data['symbol'],
            side=self.data['side'],
            percent=self.data['percent']
        )
        self.monitoring_thread = threading.Thread(target=self.monitor_interval)
        self.monitoring_thread.start()

    def monitor_interval(self):
        interval_handler = IntervalHandler(
            self.data['interval'],
            self.data['symbol'],
            self.data['side'],
            self.data['simultaneous_operations']
        )
        while not self.stop_event.is_set():
            if interval_handler.check_interval():
                if not self.operation_handler._is_running:
                    self.operation_handler.start(datetime.now(pytz.UTC))
            threading.Event().wait(3)  # Aguarda 3 segundos antes de nova verificação

    def stop_operation(self):
        if self.operation_handler:
            self.operation_handler.stop()
        if self.monitoring_thread and self.monitoring_thread.is_alive():
            self.stop_event.set()  # Sinaliza o evento de parada
            self.monitoring_thread.join()  # Aguarda a thread terminar
