from .manager import OperationHandler,IntervalHandler,conditionHandler,OKX_interface
from .pp import Market,WebhookData,ConfigLoader
import time
import threading
from datetime import datetime


class OperationManager():
    def __init__(self, percent, avaiable_size, condition_limit, interval, symbol,side):
        config_loader = ConfigLoader()
        
        # Carrega os parâmetros de conexão do banco de dados a partir do config.ini
        db_params = {
            'dbname': config_loader.get('database', 'dbname'),
            'user': config_loader.get('database', 'user'),
            'password': config_loader.get('database', 'password'),
            'host': config_loader.get('database', 'host'),
            'port': config_loader.get('database', 'port')
        }
        
        # Inicializa o WebhookData com os parâmetros do banco de dados
        self.webhook_data_manager = WebhookData(db_params)
        self.percent = percent
        self.avaiable_size = avaiable_size
        self.condition_limit = condition_limit
        self.interval = interval
        self.symbol = symbol
        self.operation_active = False  # Flag para saber se a operação está ativa
        self.monitoring_thread = None  # Para armazenar a thread de monitoramento
        self.stop_event = threading.Event()  # Para sinalizar quando parar o monitoramento
        self.side=side

    def start_operation(self):
        

        # Calcular o unit_size e criar instâncias das classes necessárias
        self.unit_size = float(self.percent) * float(self.avaiable_size)
        self.market = Market(symbol=self.symbol,side=self.side,size=self.unit_size)
        self.condition_handler = conditionHandler(self.condition_limit)

        # Instanciar o OperationHandler, mas não iniciar ainda
        self.operation_handler = OperationHandler(self.webhook_data_manager,
                                                  self.market, 
                                                  self.condition_handler, 
                                                  self.interval, 
                                                  self.symbol,
                                                  self.side)

        # Iniciar o monitoramento do intervalo em uma thread
        self.start_monitoring()

    def start_monitoring(self):
        """Inicia o monitoramento do intervalo em uma thread separada."""
        print("Iniciando monitoramento do intervalo...")
        self.stop_event.clear()  # Garantir que o stop_event esteja limpo
        self.monitoring_thread = threading.Thread(target=self.monitor_interval)
        self.monitoring_thread.start()

    def stop_monitoring(self):
        """Para o monitoramento do intervalo e a operação imediatamente."""
        print("Parando monitoramento do intervalo...")
        self.stop_event.set()  # Aciona o evento para parar a thread de monitoramento
        # Remove o join(), pois a thread daemon será finalizada automaticamente
        self.operation_active = False

    

    def monitor_interval(self):
        """Método que monitora o intervalo e inicia/paralisa a operação quando necessário."""
        self.interval_handler = IntervalHandler(self.interval, self.symbol, self.webhook_data_manager,self.side)

        while not self.stop_event.is_set():  # Continua enquanto o evento de parada não for acionado
            last_operation_higher_than_interval = self.interval_handler.check_interval()
            
            if last_operation_higher_than_interval:  # Verifica o intervalo
                if not self.operation_active:
                    print('\n***********************\n Intervalo válido, iniciando webhook....')

                    current_time = datetime.now()

                    self.operation_handler.start(current_time)  # Inicia a operação
                    self.operation_active = True

                    # Agora espera até que a operação seja completada no OperationHandler
                    self.wait_for_operation_completion()

                    # Após a conclusão da operação, volta ao monitoramento
                    self.operation_active = False

            time.sleep(3)  # Pausa antes de verificar o intervalo novamente

    def wait_for_operation_completion(self):
        """Método para aguardar até que a operação no OperationHandler seja concluída."""
        while self.operation_handler._is_running:  # Chama o método is_running corretamente
            time.sleep(1)  # Aguarda até que a operação seja concluída
        print("Operação concluída, voltando ao monitoramento.")

    def stop_operation(self):
        """Método para parar completamente a operação e o monitoramento."""
        if self.operation_active:
            print("Parando todas as operações...")
            self.operation_handler.stop()
            self.operation_active = False

        # Chama o método para parar o monitoramento
        self.stop_monitoring()
