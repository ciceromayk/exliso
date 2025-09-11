#bot_core.py

import os
from dotenv import load_dotenv
from binance import ThreadedWebsocketManager
import pandas as pd
from strategies.rsi_strategy import RSIStrategy
import queue
import time
import ta

# Carrega as variáveis de ambiente do arquivo.env
load_dotenv()
API_KEY = os.getenv("BINANCE_API_KEY")
API_SECRET = os.getenv("BINANCE_API_SECRET")

class TradingBot:
    def __init__(self, symbol, timeframe, rsi_period=14, rsi_oversold=30, rsi_overbought=70):
        self.symbol = symbol
        self.timeframe = timeframe
        self.rsi_period = rsi_period
        self.rsi_oversold = rsi_oversold
        self.rsi_overbought = rsi_overbought
        self.twm = ThreadedWebsocketManager(api_key=API_KEY, api_secret=API_SECRET)
        self.twm.start()
        self.data_queue = queue.Queue()
        self.rsi_strategy = RSIStrategy(
            symbol=self.symbol,
            timeframe=self.timeframe,
            rsi_period=self.rsi_period,
            rsi_oversold=self.rsi_oversold,
            rsi_overbought=self.rsi_oversold
        )
        self.historical_data_loaded = False
        self.running = False

    def _handle_socket_message(self, msg):
        """
        Função de callback para processar mensagens do WebSocket.
        """
        if msg['e'] == 'kline':
            kline = msg['k']
            is_closed = kline['x']
            
            # Adiciona os dados da vela fechada ao dataframe da estratégia
            self.rsi_strategy.add_kline(kline)
            
            # Se a vela está fechada, avalia a estratégia e coloca o resultado na fila
            if is_closed:
                # Calcula o RSI para exibir no dashboard
                if len(self.rsi_strategy.dataframe) > self.rsi_period:
                    self.rsi_strategy.dataframe = self.rsi_strategy.dataframe.astype({'close': 'float64'})
                    rsi_indicator = ta.momentum.RSIIndicator(self.rsi_strategy.dataframe['close'], window=self.rsi_period)
                    last_rsi = rsi_indicator.rsi().iloc[-1]
                else:
                    last_rsi = None

                signal = self.rsi_strategy.get_signal()
                last_price = float(kline['c'])

                # Coloca todos os dados importantes na fila para o Streamlit consumir
                self.data_queue.put({
                    'timestamp': kline['t'],
                    'open': float(kline['o']),
                    'high': float(kline['h']),
                    'low': float(kline['l']),
                    'close': float(kline['c']),
                    'volume': float(kline['v']),
                    'rsi': last_rsi,
                    'signal': signal
                })

    def start_bot(self):
        """Inicia a conexão com o WebSocket da Binance."""
        if self.running:
            return

        print(f"Iniciando bot de trading para {self.symbol}...")
        
        self.twm.start_kline_socket(
            callback=self._handle_socket_message,
            symbol=self.symbol,
            interval=self.timeframe
        )
        self.running = True

    def stop_bot(self):
        """Para o bot e o WebSocket."""
        if not self.running:
            return
        
        self.twm.stop()
        self.twm.join()
        print("Bot encerrado.")
        self.running = False

    def get_data(self):
        """Retorna os dados da fila de forma segura."""
        if not self.data_queue.empty():
            return self.data_queue.get_nowait()
        return None

    def get_historical_data(self):
        """Busca dados históricos da Binance para preencher o gráfico inicial."""
        if self.historical_data_loaded:
            return self.rsi_strategy.dataframe

        client = self.twm.get_client()
        klines = client.get_historical_klines(self.symbol, self.timeframe, "1 day ago UTC")
        
        # Limpa o dataframe antes de adicionar os novos dados
        self.rsi_strategy.dataframe = pd.DataFrame(columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        
        for kline in klines:
            new_row = {
                'timestamp': pd.to_datetime(kline, unit='ms'),
                'open': float(kline[1]),
                'high': float(kline[2]),
                'low': float(kline[3]),
                'close': float(kline[4]),
                'volume': float(kline[5])
            }
            new_df = pd.DataFrame([new_row])
            self.rsi_strategy.dataframe = pd.concat([self.rsi_strategy.dataframe, new_df], ignore_index=True)

        # Calcula o RSI para os dados históricos
        if len(self.rsi_strategy.dataframe) > self.rsi_period:
            self.rsi_strategy.dataframe = self.rsi_strategy.dataframe.astype({'close': 'float64'})
            rsi_indicator = ta.momentum.RSIIndicator(self.rsi_strategy.dataframe['close'], window=self.rsi_period)
            self.rsi_strategy.dataframe['rsi'] = rsi_indicator.rsi()
            
        self.historical_data_loaded = True
        return self.rsi_strategy.dataframe
