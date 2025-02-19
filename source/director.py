from .manager import OperationHandler, IntervalHandler, conditionHandler,TPSLHandler
from .pp import Market
from datetime import datetime
import pytz
import threading


class OperationManager:
    def __init__(self, user_id, data, strategy_id, exchange_id, api_key, instance_id):
        self.user_id = user_id
        self.data = data
        self.strategy_id = strategy_id
        self.stop_event = threading.Event()
        self.monitoring_thread = None
        self.tp_sl_thread = None
        self.operation_handler = None
        self.exchange_id = exchange_id
        self.api_key = api_key
        self.instance_id = instance_id

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
            percent=self.data['percent'],
            exchange_id=self.exchange_id,
            user_id=self.user_id,
            api_key=self.api_key,
            instance_id=self.instance_id,
            tp=self.data.get('tp'),
            sl=self.data.get('sl')
        )
        self.monitoring_thread = threading.Thread(target=self.monitor_interval,daemon=True)
        self.monitoring_thread.start()

        # Iniciar monitoramento de TP/SL apenas para operações do tipo "buy"
        if self.data['side'].lower() == 'buy':
            self.tp_sl_thread = threading.Thread(target=self.monitor_tp_sl,daemon=True)
            self.tp_sl_thread.start()

    def monitor_tp_sl(self):
        """
        Monitora o TP e SL da operação verificando o preço atual do ativo e comparando com os valores salvos.
        """
        tp_sl_handler = TPSLHandler(
            instance_id=self.instance_id,
            user_id=self.user_id,
            api_key=self.api_key,
            symbol=self.data['symbol'],
            exchange_id=self.exchange_id,
            side=self.data['side']
        )
        while not self.stop_event.is_set():
            tp_sl_handler.check_tp_sl_conditions()
            threading.Event().wait(3)  # Ajuste no tempo de verificação conforme necessário

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
        if self.monitoring_thread and self.monitoring_thread.is_alive() and self.tp_sl_thread.is_alive():
            self.stop_event.set()  # Sinaliza o evento de parada
            self.monitoring_thread.join()  # Aguarda a thread terminar
            self.tp_sl_thread.join()  # Aguarda a thread terminar
            
