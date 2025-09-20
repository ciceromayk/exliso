import streamlit as st
import requests
import pandas as pd
import time

# --- CONFIGURAÇÃO ---
COINMARKETCAP_API_URL = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/listings/latest"
API_REFRESH_INTERVAL = 60  # Segundos

st.set_page_config(
    page_title="Meme Coin Radar",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# --- FUNÇÕES DE LÓGICA E DADOS ---
@st.cache_data(ttl=API_REFRESH_INTERVAL)
def fetch_coin_data(api_key, retries=3):
    """
    Busca as 20 principais moedas por volume da CoinMarketCap.
    """
    headers = {
        'Accepts': 'application/json',
        'X-CMC_PRO_API_KEY': api_key,
    }
    params = {
        'start': '1',
        'limit': '20',
        'sort': 'volume_24h',
        'sort_dir': 'desc',
        'convert': 'BRL'
    }

    for attempt in range(retries):
        try:
            response = requests.get(COINMARKETCAP_API_URL, headers=headers, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if data['status']['error_code'] == 0:
                return data['data']
            else:
                st.error(f"Erro na API do CoinMarketCap: {data['status']['error_message']}")
                return []
        except requests.exceptions.RequestException as e:
            if attempt < retries - 1:
                st.warning(f"Tentativa {attempt + 1}/{retries} falhou. Tentando novamente em 5 segundos...")
                time.sleep(5)
            else:
                st.error(f"Erro ao carregar dados do CoinMarketCap após {retries} tentativas: {e}")
                return []
    return []

# --- RENDERIZAÇÃO DA PÁGINA ---
st.title("Top 20 Moedas por Volume 🚀")
st.write("Listagem das 20 moedas com maior volume de negociação nas últimas 24 horas.")

if "api_key" not in st.session_state:
    with st.form(key='api_key_form'):
        st.header("Insira a sua chave da API")
        st.write("Por favor, insira a sua chave da API do CoinMarketCap para carregar os dados. Você pode obtê-la gratuitamente em [https://pro.coinmarketcap.com/signup/](https://pro.coinmarketcap.com/signup/).")
        api_key_input = st.text_input("Chave da API", type="password")
        submit_button = st.form_submit_button(label='Acessar')
        if submit_button and api_key_input:
            st.session_state.api_key = api_key_input
            st.rerun()
else:
    with st.spinner("Carregando dados..."):
        coin_data = fetch_coin_data(st.session_state.api_key)
        
    if coin_data:
        # Extrair e formatar os dados para um DataFrame do Pandas
        df_data = []
        for coin in coin_data:
            df_data.append({
                "Nome": f"{coin['name']} ({coin['symbol']})",
                "Preço (R$)": f"R$ {coin['quote']['BRL']['price']:.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
                "Volume 24h (R$)": f"R$ {coin['quote']['BRL']['volume_24h'] / 1e9:.2f}B".replace(",", "X").replace(".", ",").replace("X", "."),
                "Variação 24h": f"{coin['quote']['BRL']['percent_change_24h']:.2f}%",
                "Capitalização de Mercado (R$)": f"R$ {coin['quote']['BRL']['market_cap'] / 1e9:.2f}B".replace(",", "X").replace(".", ",").replace("X", ".")
            })
        
        df = pd.DataFrame(df_data)
        st.dataframe(df, hide_index=True, use_container_width=True)
    else:
        st.warning("Não foi possível carregar os dados das moedas. Por favor, verifique sua chave da API ou tente novamente mais tarde.")
