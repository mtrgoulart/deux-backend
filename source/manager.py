from .client import OKXClient
import threading
import time
from .pp import ConfigLoader,Market
from collections import defaultdict
from datetime import datetime


class OKX_interface():
    def __init__(self,config: object):
        self.config=config
        self.okx_client=OKXClient(self.config)

    def place_order(self,symbol,side,type,size,price):
        response = self.okx_client.place_order(symbol, side, type, size, price)
        return response
    
    def cancel_order(self,symbol,order):
        response = self.okx_client.cancel_order(symbol,order)
        return response
    
    def get_open_order(self,symbol):
        response = self.okx_client.get_open_orders(symbol)
        return response
    
    def get_order_status(self,symbol,order_id):
        response = self.okx_client.get_order_status(symbol,order_id)
        return response
    
    def get_last_trade(self,symbol):
        response = self.okx_client.get_last_trade(symbol)
        return response
    
    def get_balance(self, ccy=None):
        response = self.okx_client.get_balance(ccy)
        
        if 'data' in response and isinstance(response['data'], list) and response['data']:
            details = response['data'][0].get('details', [])
            
            # Filtrar a moeda correta
            for detail in details:
                if detail.get('ccy') == ccy:
                    eq = detail.get('eq', None)
                    
                    # Verificar se eq não é vazio ou None
                    if eq and eq != '':
                        return round(float(eq), 6)  # Retorna o valor de eq arredondado para 6 casas decimais
                    
        return None  # Retorna None se não encontrar o valor ou se não for possível convertê-lo
    
    def get_order_execution_price(self, symbol, order_id):
        # Consulta o status da ordem usando o 'ordId'
        order_status = self.okx_client.get_order_status(symbol, order_id)
        
        
        # Captura o preço de execução (fillPx)
        execution_price = float(order_status['data'][0].get('fillPx', 0))
        return execution_price

class IntervalHandler:
    def __init__(self, interval, symbol, db_manager,side):
        self.interval = float(interval)
        self.symbol = symbol
        self.db_manager = db_manager  # Passa o gerenciador de banco de dados
        self.side=side

    def get_last_op(self):
        """
        Busca a última operação do banco de dados para o símbolo especificado.
        """
        last_operation = self.db_manager.get_last_operation_from_db(self.symbol)
        return last_operation

    def check_interval(self):
        """
        Verifica se o intervalo entre a última operação e o horário atual atende ao intervalo mínimo.
        """
        last_operation = self.get_last_op()
        if last_operation is not None:
            if last_operation['side']!=self.side:
                return True
            else:
                valid_interval = self._interval_logic(last_operation['date'])
                return valid_interval
        else:
            return True

    def get_application_interval(self, last_operation_time):
        """
        Calcula o intervalo em minutos entre a última operação e o horário atual.
        """
        if last_operation_time:
            current_time = datetime.now()
            return (current_time - last_operation_time).total_seconds() / 60
        return None

    def _interval_logic(self, last_operation_time):
        last_operation_interval = self.get_application_interval(last_operation_time)
        print(f"Intervalo decorrido: {last_operation_interval} minutos")
        if self.interval == 0:
            return True
        else:
            return last_operation_interval >= self.interval
    
class OperationHandler:
    def __init__(self, webhook_data_manager,market_manager,condition_handler,interval,symbol,side):
        self.webhook_data_manager = webhook_data_manager
        self.market_manager=market_manager
        self.stop_event = threading.Event()
        self.condition_handler=condition_handler
        self.interval=interval
        self.symbol=symbol
        self._is_running = False
        self.side=side

    def start(self, start_date):
        self.stop_event.clear()
        self.thread = threading.Thread(target=self.run, args=(start_date,))
        self.thread.start()
        self._is_running = True

    def stop(self):
        self.stop_event.set()
        self.thread.join()

    def run(self,start_date):
        while not self.stop_event.is_set():
            # Recupera objetos agrupados do banco de dados
            data = self.webhook_data_manager.get_market_objects_as_models(self.symbol,self.side,start_date)

            operation_performed = False
            if self.check_conditions(data) and len(data) > 1:
                last_market_data = data[-1]  # Pega o último item

                # Cria o objeto Market para realizar a operação
                market_to_operation = Market(
                    symbol=last_market_data["symbol"],
                    order_type='market',
                    side=last_market_data["side"],
                    size=self.market_manager.size
                )
                self.perform_operation(market_to_operation)

                # Salva a operação no banco e captura o ID
                operation_id = self.webhook_data_manager.save_operation_to_db(market_to_operation.to_dict())

                # Atualiza o status da operação no banco de dados
                self.update_webhook_operation(data, operation_id)
                operation_performed = True

                time.sleep(2)
                self._is_running = False

            if operation_performed:
                break

            time.sleep(3)

    def is_running(self):
        """Retorna se a operação ainda está em execução."""
        return self._is_running

    def update_webhook_operation(self, filtered_data,operation_id):
        for market_object in filtered_data:
            # Cria um dicionário de novos dados para a operação "Done"
            new_data = {
                "symbol": market_object["symbol"],
                "side": market_object["side"],
                "indicator": market_object.get("indicator"),
                "operation": operation_id  # Define como "Done"
            }

            # Atualiza o banco de dados usando o `id` do objeto
            try:
                self.webhook_data_manager.update_market_object_at_index(market_object["id"], new_data)
                print(f"Objeto {market_object['id']} atualizado com sucesso.")
            except Exception as e:
                print(f"Erro ao atualizar o objeto {market_object['id']}: {e}")

    def check_conditions(self, data):
        return self.condition_handler.check_condition(data)

    def perform_operation(self, market_data):
        config = ConfigLoader()
        client = OKX_interface(config)
        #print(f'\nsymbol={market_data.symbol},order_type={market_data.order_type},side={market_data.side},size={market_data.size}')
        order=client.place_order(
            symbol=market_data.symbol,
            type=market_data.order_type,
            side=market_data.side,
            size=market_data.size,
            price=market_data.price
        )
        return order
    
    def perform_operation_with_stop_take(self, market_data, stop_loss_percent=0.5, take_profit_percent=0.5):
        config = ConfigLoader()
        client = OKX_interface(config)
        
        # Envia a ordem à mercado e captura o 'ordId'
        market_order = client.place_order(
            symbol=market_data.symbol,
            type='market',
            side=market_data.side,
            size=market_data.size,
            price=None  # Preço não é necessário para uma ordem de mercado
        )
        order_id = market_order['data'][0]['ordId']  # Captura o 'ordId' da resposta
        print(f'Market order placed: {market_order}')
        
        # Captura o preço de execução da ordem usando o 'ordId'
        execution_price = self.get_execution_price(client,market_data.symbol, order_id)
        print(f'Execution price: {execution_price}')
        
        # Valor em USD da operação (tamanho da posição em USD)
        total_usd = execution_price * market_data.size
        
        # Calcula a perda em USD para o Stop Loss e o ganho para o Take Profit
        stop_loss_usd = total_usd * stop_loss_percent
        take_profit_usd = total_usd * take_profit_percent
        
        # Calcula os preços de Stop Loss e Take Profit com base nos valores em USD
        if market_data.side == 'buy':
            stop_loss_price = execution_price - (stop_loss_usd / market_data.size)
            take_profit_price = execution_price + (take_profit_usd / market_data.size)
        else:  # Para ordens de venda
            stop_loss_price = execution_price + (stop_loss_usd / market_data.size)
            take_profit_price = execution_price - (take_profit_usd / market_data.size)
        
        # Define o lado oposto para as ordens de stop loss e take profit
        opposite_side = 'sell' if market_data.side == 'buy' else 'buy'
        
        # Envia a ordem de Stop Loss
        stop_loss_order = client.place_order(
            symbol=market_data.symbol,
            type='limit',  # Ordem limitada
            side=opposite_side,
            size=market_data.size,
            price=stop_loss_price  # Preço calculado para o stop loss
        )
        print(f'Stop Loss order placed at {stop_loss_price}: {stop_loss_order}')
        
        # Envia a ordem de Take Profit
        take_profit_order = client.place_order(
            symbol=market_data.symbol,
            type='limit',  # Ordem limitada
            side=opposite_side,
            size=market_data.size,
            price=take_profit_price  # Preço calculado para o take profit
        )
        print(f'Take Profit order placed at {take_profit_price}: {take_profit_order}')
        
        return market_order, stop_loss_order, take_profit_order

    def get_execution_price(self, client,symbol, order_id):
        # Consulta o status da ordem usando o 'ordId'
        order_status = client.get_order_status(symbol, order_id)
        
        # Supondo que a resposta da API contenha 'fillPx', que é o preço de execução
        execution_price = float(order_status['data'][0].get('fillPx', 0))
        
        if execution_price == 0:
            raise ValueError("Preço de execução não encontrado ou inválido.")
        
        return execution_price

class conditionHandler:
    def __init__(self, length_condition):
        self.length_condition = length_condition
    
    def check_condition(self, market_list):
        # Dicionário para armazenar os símbolos e tipos com suas estratégias correspondentes
        symbol_type_dict = {}

        for market in market_list:
            key = (market["symbol"], market["side"])  # Chave combinada de symbol e side
            
            if key not in symbol_type_dict:
                symbol_type_dict[key] = []  # Inicializa como lista
            
            # Verifica se a estratégia (indicator) já está na lista, se não estiver, adiciona
            if market["indicator"] not in symbol_type_dict[key]:
                symbol_type_dict[key].append(market["indicator"])

        # Agora verificamos se há pelo menos duas estratégias diferentes para cada combinação de symbol e side
        for key, strategies in symbol_type_dict.items():
            if len(strategies) < int(self.length_condition):
                return False  # Se alguma combinação não tiver pelo menos duas estratégias diferentes, retorna False

        return True # Se todas as combinações tiverem duas ou mais estratégias diferentes, retorna True
