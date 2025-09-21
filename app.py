import streamlit as st
import requests
import pandas as pd
import time

# --- CONFIGURAÇÃO ---
COINGECKO_API_URL = "https://api.coingecko.com/api/v3/coins/markets"
API_REFRESH_INTERVAL = 60  # Segundos

st.set_page_config(
    page_title="Coin Ranking",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# --- FUNÇÕES DE LÓGICA E DADOS ---
@st.cache_data(ttl=API_REFRESH_INTERVAL)
def fetch_coin_data(retries=3):
    """
    Busca os dados das moedas na CoinGecko.
    """
    params = {
        'vs_currency': 'brl',
        'order': 'market_cap_desc',
        'per_page': 250, 
        'page': 1,
        'sparkline': False,
        'price_change_percentage': '24h'
    }

    for attempt in range(retries):
        try:
            response = requests.get(COINGECKO_API_URL, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            return data
        except requests.exceptions.RequestException as e:
            if attempt < retries - 1:
                st.warning(f"Tentativa {attempt + 1}/{retries} falhou. Tentando novamente em 5 segundos...")
                time.sleep(5)
            else:
                st.error(f"Erro ao carregar dados do CoinGecko após {retries} tentativas: {e}")
                return []
    return []

def render_table_card(title, data, sort_key=None, sort_reverse=False):
    """
    Renderiza um painel com uma tabela de dados, com opção de ordenação.
    """
    st.subheader(title)
    df_data = []
    if data:
        for coin in data:
            price = coin.get('current_price')
            volume = coin.get('total_volume')
            change_percent = coin.get('price_change_percentage_24h_in_currency')
            
            # Formatação segura para valores que podem ser None
            price_formatted = f"R$ {price:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") if price is not None else "N/A"
            volume_formatted = f"R$ {volume / 1e9:.2f}B".replace(",", "X").replace(".", ",").replace("X", ".") if volume is not None and volume > 1e9 else (f"R$ {volume / 1e6:.2f}M".replace(",", "X").replace(".", ",").replace("X", ".") if volume is not None else "N/A")
            change_formatted = f"{change_percent:,.2f}%".replace(",", "X").replace(".", ",").replace("X", ".") if change_percent is not None else "N/A"

            df_data.append({
                "Nome": f"{coin.get('name')} ({coin.get('symbol').upper()})",
                "Preço (R$)": price_formatted,
                "Variação 24h (%)": change_formatted,
                "Volume 24h (R$)": volume_formatted,
            })
    
    if df_data:
        df = pd.DataFrame(df_data)
        st.dataframe(df, hide_index=True, use_container_width=True)
    else:
        st.info("Dados não disponíveis.")

# --- RENDERIZAÇÃO DA PÁGINA ---
st.title("Coin Ranking 🚀")
st.write("Visão geral do mercado de criptomoedas: as 250 moedas com maior capitalização de mercado.")

with st.spinner("Carregando dados do CoinGecko..."):
    coin_data = fetch_coin_data()

st.write("---")

if coin_data:
    # Filtra os dados de forma segura
    top_20_coins = coin_data[:20]
    # Ordena os ganhadores de forma segura, tratando valores nulos
    top_gainers = sorted(coin_data, key=lambda x: x.get('price_change_percentage_24h_in_currency') or -1000, reverse=True)[:10]
    anomalies_data = [coin for coin in coin_data if isinstance(coin.get('price_change_percentage_24h_in_currency'), (float, int)) and coin.get('price_change_percentage_24h_in_currency') > 30]

    # Renderiza em colunas
    col1, col2, col3 = st.columns(3)
    
    with col1:
        render_table_card("Moedas Principais (20+)", top_20_coins)
    
    with col2:
        render_table_card("Top Ganhadores", top_gainers)
    
    with col3:
        if anomalies_data:
            render_table_card("Anomalias de Preço (>30%)", anomalies_data)
        else:
            st.subheader("Anomalias de Preço (>30%)")
            st.info("Nenhuma anomalia de preço encontrada nas últimas 24h.")
else:
    st.warning("Não foi possível carregar os dados. Por favor, tente novamente mais tarde.")
