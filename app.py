import streamlit as st
import requests
import pandas as pd
import time

# --- CONFIGURAÇÃO ---
BINANCE_API_URL = "https://api.binance.com/api/v3/ticker/24hr"
API_REFRESH_INTERVAL = 60  # Segundos

st.set_page_config(
    page_title="Coin Ranking",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# --- FUNÇÕES DE LÓGICA E DADOS ---
@st.cache_data(ttl=API_REFRESH_INTERVAL)
def fetch_binance_data(retries=3):
    """
    Busca os dados das 20 principais moedas por volume na Binance.
    """
    for attempt in range(retries):
        try:
            response = requests.get(BINANCE_API_URL, timeout=10)
            response.raise_for_status()
            all_tickers = response.json()
            
            # Filtrar pares que terminam com BRL e obter os 20 principais por volume
            brl_pairs = [
                ticker for ticker in all_tickers 
                if ticker['symbol'].endswith('BRL') and float(ticker['quoteVolume']) > 0
            ]
            
            # Ordenar por volume em ordem decrescente
            sorted_by_volume = sorted(brl_pairs, key=lambda x: float(x['quoteVolume']), reverse=True)
            
            return sorted_by_volume[:20]
        
        except requests.exceptions.RequestException as e:
            if attempt < retries - 1:
                st.warning(f"Tentativa {attempt + 1}/{retries} falhou. Tentando novamente em 5 segundos...")
                time.sleep(5)
            else:
                st.error(f"Erro ao carregar dados da Binance após {retries} tentativas: {e}")
                return []
    return []

def render_table_card(title, data):
    """
    Renderiza um painel com uma tabela de dados.
    """
    st.subheader(title)
    df_data = []
    if data:
        for ticker in data:
            name = ticker['symbol'].replace('BRL', '')
            price = float(ticker['lastPrice'])
            volume = float(ticker['quoteVolume'])
            change_percent = float(ticker['priceChangePercent'])
            
            df_data.append({
                "Nome": f"{name} (BRL)",
                "Preço (R$)": f"R$ {price:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
                "Variação 24h (%)": f"{change_percent:,.2f}%".replace(",", "X").replace(".", ",").replace("X", "."),
                "Volume 24h (R$)": f"R$ {volume / 1e9:.2f}B".replace(",", "X").replace(".", ",").replace("X", ".") if volume > 1e9 else f"R$ {volume / 1e6:.2f}M".replace(",", "X").replace(".", ",").replace("X", "."),
            })

    if df_data:
        df = pd.DataFrame(df_data)
        st.dataframe(df, hide_index=True, use_container_width=True)
    else:
        st.info("Dados não disponíveis.")

# --- RENDERIZAÇÃO DA PÁGINA ---
st.title("Top 20 Moedas na Binance 🚀")
st.write("Listagem das 20 principais moedas por volume de negociação na Binance, em BRL.")

with st.spinner("Carregando dados da Binance..."):
    binance_data = fetch_binance_data()
    
if binance_data:
    render_table_card("Moedas com Maior Volume", binance_data)
else:
    st.warning("Não foi possível carregar os dados. Por favor, tente novamente mais tarde.")
