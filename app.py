import streamlit as st
import pandas as pd
import time
import plotly.graph_objects as go
from bot_core import TradingBot
import ta
from datetime import datetime

# Configurações iniciais do Streamlit
st.set_page_config(layout="wide", page_title="Bot de Trading de Memecoins")

# Título do dashboard
st.title("Dashboard de Trading de Memecoins em Tempo Real")

# Inicializa o bot na `Session State` do Streamlit para persistir o estado
if 'bot' not in st.session_state:
    st.session_state.bot = TradingBot(symbol='PEPEUSDT', timeframe='1m')

# Sidebar para controles do bot
st.sidebar.header("Controles do Bot")
symbol = st.sidebar.selectbox(
    "Selecione a Criptomoeda",
    ('PEPEUSDT', 'DOGEUSDT', 'SHIBUSDT'),
    key='symbol_select'
)
timeframe = st.sidebar.selectbox(
    "Selecione o Timeframe",
    ('1m', '5m', '15m'),
    key='timeframe_select'
)
if st.sidebar.button("Iniciar Bot"):
    st.session_state.bot.stop_bot()
    st.session_state.bot = TradingBot(symbol=symbol, timeframe=timeframe)
    st.session_state.bot.start_bot()
    st.sidebar.success("Bot iniciado com sucesso!")

if st.sidebar.button("Parar Bot"):
    st.session_state.bot.stop_bot()
    st.sidebar.warning("Bot parado.")


# placeholders para dados em tempo real
status_placeholder = st.empty()
chart_placeholder = st.empty()
metrics_placeholder = st.empty()
signal_placeholder = st.empty()
dataframe_placeholder = st.empty()

# Dicionário para armazenar o histórico de dados para o gráfico
if 'data_history' not in st.session_state:
    st.session_state.data_history = pd.DataFrame(columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'rsi'])
    # Carrega dados históricos para preencher o gráfico inicial
    st.session_state.data_history = st.session_state.bot.get_historical_data()

# Loop para atualização contínua do dashboard
while True:
    data = st.session_state.bot.get_data()
    
    if data:
        # Adiciona novos dados ao histórico
        new_row = {
            'timestamp': pd.to_datetime(data['timestamp'], unit='ms'),
            'open': data['open'],
            'high': data['high'],
            'low': data['low'],
            'close': data['close'],
            'volume': 0, # Volume não é fornecido por este stream, por isso colocamos 0.
            'rsi': data['rsi']
        }
        new_df = pd.DataFrame([new_row])
        st.session_state.data_history = pd.concat([st.session_state.data_history, new_df], ignore_index=True)

        # Limita o tamanho do histórico para economizar memória e manter o gráfico rápido
        st.session_state.data_history = st.session_state.data_history.iloc[-500:]

        # Lógica de exibição das métricas e sinais
        current_price = data['close']
        current_rsi = data['rsi']
        signal = data['signal']

        # Atualiza os placeholders
        with metrics_placeholder.container():
            col1, col2 = st.columns(2)
            col1.metric("Preço Atual", f"{current_price:.6f} USDT")
            col2.metric("RSI (14)", f"{current_rsi:.2f}" if current_rsi else "Calculando...")
        
        with signal_placeholder.container():
            if signal == "BUY":
                st.success(f"SINAL DETECTADO: {signal} em {symbol}")
            elif signal == "SELL":
                st.error(f"SINAL DETECTADO: {signal} em {symbol}")
            else:
                st.info(f"SINAL: {signal}")

        # Cria e atualiza o gráfico de candlestick
        with chart_placeholder:
            fig = go.Figure(data=[go.Candlestick(
                x=st.session_state.data_history['timestamp'],
                open=st.session_state.data_history['open'],
                high=st.session_state.data_history['high'],
                low=st.session_state.data_history['low'],
                close=st.session_state.data_history['close']
            )])
            fig.update_layout(xaxis_rangeslider_visible=False, title=f"Preço de {symbol} - Timeframe: {timeframe}")
            
            if current_rsi:
                # Adiciona o RSI como um subplot
                fig_rsi = go.Figure(data=,
                    y=st.session_state.data_history['rsi'],
                    mode='lines',
                    name='RSI',
                    line=dict(color='purple')
                )])
                fig_rsi.update_layout(title="Indicador RSI")
                st.plotly_chart(fig, use_container_width=True)
                st.plotly_chart(fig_rsi, use_container_width=True)
            else:
                st.plotly_chart(fig, use_container_width=True)

    # Pequena pausa para evitar sobrecarga de CPU e controlar a frequência de atualização
    time.sleep(1)
