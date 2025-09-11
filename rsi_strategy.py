#rsi_strategy.py

import pandas as pd
import ta
import time

class RSIStrategy:
    def __init__(self, symbol, timeframe, rsi_period=14, rsi_oversold=30, rsi_overbought=70):
        self.symbol = symbol
        self.timeframe = timeframe
        self.rsi_period = rsi_period
        self.rsi_oversold = rsi_oversold
        self.rsi_overbought = rsi_overbought
        self.open_position = False
        self.dataframe = pd.DataFrame(columns=['open', 'high', 'low', 'close', 'volume', 'timestamp'])

    def add_kline(self, kline):
        """Adiciona uma nova vela (kline) ao dataframe."""
        new_row = {
            'open': float(kline['o']),
            'high': float(kline['h']),
            'low': float(kline['l']),
            'close': float(kline['c']),
            'volume': float(kline['v']),
            'timestamp': kline
        }
        
        # Converte para DataFrame e concatena
        new_df = pd.DataFrame([new_row])
        self.dataframe = pd.concat([self.dataframe, new_df], ignore_index=True)
        
        # Limita o tamanho do dataframe para economizar memória
        if len(self.dataframe) > 500:
            self.dataframe = self.dataframe.iloc[-500:]

    def get_signal(self):
        """Calcula o RSI e retorna um sinal de trading."""
        if len(self.dataframe) < self.rsi_period:
            return "NO_SIGNAL"

        # Garante que os dados sejam numéricos para o cálculo
        self.dataframe = self.dataframe.astype({'close': 'float64'})
        
        # Calcula o RSI
        rsi = ta.momentum.RSIIndicator(self.dataframe['close'], window=self.rsi_period)
        last_rsi = rsi.rsi().iloc[-1]
        
        # Lógica da estratégia
        if last_rsi < self.rsi_oversold and not self.open_position:
            self.open_position = True
            return "BUY"
        elif last_rsi > self.rsi_overbought and self.open_position:
            self.open_position = False
            return "SELL"
        else:
            return "HOLD"
