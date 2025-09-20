import streamlit as st
import requests
import pandas as pd
import time

# --- CONFIGURAÇÃO ---
COINMARKETCAP_API_URL = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/listings/latest"
API_REFRESH_INTERVAL = 60  # Segundos

st.set_page_config(
    page_title="Coin Ranking",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# --- FUNÇÕES DE LÓGICA E DADOS ---
@st.cache_data(ttl=API_REFRESH_INTERVAL)
def fetch_coin_data(api_key, sort_by, limit=10, retries=3):
    """
    Busca dados de moedas da CoinMarketCap com base em um critério de ordenação.
    """
    headers = {
        'Accepts': 'application/json',
        'X-CMC_PRO_API_KEY': api_key,
    }
    params = {
        'start': '1',
        'limit': str(limit),
        'sort': sort_by,
        'convert': 'BRL'
    }

    if sort_by == 'percent_change_24h':
        params['sort_dir'] = 'desc'

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

def render_table_card(title, data, sort_by_desc=True):
    """
    Renderiza um painel com uma tabela de dados.
    """
    st.subheader(title)
    df_data = []
    if data:
        for coin in data:
            price = coin['quote']['BRL']['price']
            volume = coin['quote']['BRL']['volume_24h']
            change = coin['quote']['BRL']['percent_change_24h']
            
            df_data.append({
                "Nome": f"{coin['name']} ({coin['symbol']})",
                "Preço (R$)": f"R$ {price:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
                "Volume 24h (R$)": f"R$ {volume / 1e9:.2f}B".replace(",", "X").replace(".", ",").replace("X", ".") if volume > 1e9 else f"R$ {volume / 1e6:.2f}M".replace(",", "X").replace(".", ",").replace("X", "."),
                "Variação 24h": f"{change:,.2f}%".replace(",", "X").replace(".", ",").replace("X", "."),
            })

    if df_data:
        df = pd.DataFrame(df_data)
        st.dataframe(df, hide_index=True, use_container_width=True)
    else:
        st.info("Dados não disponíveis.")

# --- RENDERIZAÇÃO DA PÁGINA ---
st.title("Coin Ranking 🚀")
st.write("Visão geral do mercado de criptomoedas: Top Ganhadores, Top Perdedores e Maior Volume.")

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
        # Dados de Top Ganhadores e Perdedores (ordenados por percent_change_24h)
        top_gainers_data = fetch_coin_data(st.session_state.api_key, sort_by='percent_change_24h', limit=10)
        
        # Invertemos a lista para obter os perdedores
        top_losers_data = top_gainers_data[::-1] if top_gainers_data else []

        # Dados de Maior Volume (ordenados por volume_24h)
        top_volume_data = fetch_coin_data(st.session_state.api_key, sort_by='volume_24h', limit=10)
        
    st.write("---")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        render_table_card("Top Ganhadores", top_gainers_data)
        
    with col2:
        render_table_card("Top Perdedores", top_losers_data)
        
    with col3:
        render_table_card("Maior Volume", top_volume_data)

    st.write("---")
