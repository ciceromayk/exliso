#Main.py

import os
from dotenv import load_dotenv
from binance import ThreadedWebsocketManager
import pandas as pd
from strategies.rsi_strategy import RSIStrategy
import time

# Carrega as variáveis de ambiente do arquivo.env
load_dotenv()
API_KEY = os.getenv("BINANCE_API_KEY")
API_SECRET = os.getenv("BINANCE_API_SECRET")

# Configurações do bot
SYMBOL = 'PEPEUSDT'
TIMEFRAME = '1m' # 1 minuto
RSI_PERIOD = 14
RSI_OVERSOLD = 30
RSI_OVERBOUGHT = 70

# Inicializa a estratégia
rsi_bot = RSIStrategy(
    symbol=SYMBOL,
    timeframe=TIMEFRAME,
    rsi_period=RSI_PERIOD,
    rsi_oversold=RSI_OVERSOLD,
    rsi_overbought=RSI_OVERSOLD
)

def handle_socket_message(msg):
    """
    Função de callback para processar mensagens do WebSocket.
    Cada mensagem representa uma nova atualização de vela (kline).
    """
    try:
        # Apenas processa a vela quando ela está fechada (finalizada)
        if msg['e'] == 'kline' and msg['k']['x']:
            kline = msg['k']
            print(f"Vela recebida para {kline['s']} - Fechamento: {kline['c']}")

            rsi_bot.add_kline(kline)
            signal = rsi_bot.get_signal()
            
            # Lógica de decisão
            if signal == "BUY":
                print(f" SINAL DE COMPRA: RSI < {RSI_OVERSOLD}. Executar ordem de compra em {SYMBOL}!")
            elif signal == "SELL":
                print(f" SINAL DE VENDA: RSI > {RSI_OVERSOLD}. Executar ordem de venda em {SYMBOL}!")
            else:
                print(f" SINAL: HOLD. Nenhuma ação necessária.")

    except Exception as e:
        print(f"Erro ao processar mensagem: {e}")

def main():
    """Função principal para iniciar o bot."""
    print("Iniciando bot de trading...")
    
    # Gerenciador de WebSocket
    twm = ThreadedWebsocketManager(api_key=API_KEY, api_secret=API_SECRET)
    twm.start()

    # Inicia o socket para dados de velas (kline)
    twm.start_kline_socket(
        callback=handle_socket_message,
        symbol=SYMBOL,
        interval=TIMEFRAME
    )

    try:
        # Mantém o bot rodando
        twm.join()
    except KeyboardInterrupt:
        print("Bot encerrado pelo usuário.")
        twm.stop()

if __name__ == "__main__":
    main()
