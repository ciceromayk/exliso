import streamlit as st
import requests
import pandas as pd
import json
import time

# --- CONFIGURAÇÃO ---
COINMARKETCAP_API_URL = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/listings/latest"
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-05-20:generateContent"
API_REFRESH_INTERVAL = 5  # Segundos

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

def analyze_with_gemini(gemini_api_key, coin_info):
    """
    Gera uma análise de mercado usando a API Gemini.
    """
    prompt = f"Analise os seguintes dados do mercado de criptomoedas e forneça um resumo conciso em português sobre movimentos suspeitos de preço e volume. Foco em pump-and-dump. Dados da moeda {coin_info['name']}: Preço: R${coin_info['price']:.2f}, Volume 24h: R${coin_info['volume']:.2f}, Variação 24h: {coin_info['change']:.2f}%."
    
    headers = {
        'Content-Type': 'application/json',
    }
    payload = {
        "contents": [{"parts": [{"text": prompt}]}]
    }
    
    try:
        response = requests.post(f"{GEMINI_API_URL}?key={gemini_api_key}", headers=headers, json=payload, timeout=20)
        response.raise_for_status()
        result = response.json()
        
        if result['candidates'] and result['candidates'][0]['content']['parts'][0]['text']:
            return result['candidates'][0]['content']['parts'][0]['text']
        else:
            return "Não foi possível gerar a análise. Tente novamente mais tarde."
            
    except requests.exceptions.RequestException as e:
        return f"Erro ao conectar com a API Gemini: {e}"

def render_table_card(title, data):
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
    
    # Adicionar o botão de análise para a primeira moeda
    if data:
        st.write("---")
        with st.container():
            st.markdown(f"**Analisar {data[0]['name']}**")
            with st.expander("Clique para Análise de IA", expanded=False):
                if st.session_state.get('gemini_api_key'):
                    with st.spinner("Gerando análise com Gemini..."):
                        analysis = analyze_with_gemini(st.session_state.gemini_api_key, {
                            'name': data[0]['name'],
                            'price': data[0]['quote']['BRL']['price'],
                            'volume': data[0]['quote']['BRL']['volume_24h'],
                            'change': data[0]['quote']['BRL']['percent_change_24h']
                        })
                        st.info(analysis)
                else:
                    st.error("Por favor, insira sua chave da API do Gemini para gerar uma análise.")

# --- RENDERIZAÇÃO DA PÁGINA ---
st.title("Coin Ranking 🚀")
st.write("Visão geral do mercado de criptomoedas: Top Ganhadores, Top Perdedores e Maior Volume.")

if "coinmarketcap_api_key" not in st.session_state:
    with st.form(key='api_key_form'):
        st.header("Insira suas chaves de API")
        st.write("Para carregar os dados, insira sua chave da API do **CoinMarketCap**. Para análises, insira sua chave da API do **Gemini** (opcional).")
        cmc_key_input = st.text_input("Chave da API do CoinMarketCap", type="password")
        gemini_key_input = st.text_input("Chave da API do Gemini (opcional)", type="password")
        submit_button = st.form_submit_button(label='Acessar')
        if submit_button and cmc_key_input:
            st.session_state.coinmarketcap_api_key = cmc_key_input
            if gemini_key_input:
                st.session_state.gemini_api_key = gemini_key_input
            st.rerun()
else:
    with st.spinner("Carregando dados..."):
        # Dados de Top Ganhadores e Perdedores (ordenados por percent_change_24h)
        top_gainers_data = fetch_coin_data(st.session_state.coinmarketcap_api_key, sort_by='percent_change_24h', limit=10)
        
        # Invertemos a lista para obter os perdedores
        top_losers_data = top_gainers_data[::-1] if top_gainers_data else []

        # Dados de Maior Volume (ordenados por volume_24h)
        top_volume_data = fetch_coin_data(st.session_state.coinmarketcap_api_key, sort_by='volume_24h', limit=10)
        
    st.write("---")
    
    col1, col2 = st.columns(2)
    
    with col1:
        render_table_card("Top Ganhadores", top_gainers_data)
        
    with col2:
        render_table_card("Top Perdedores", top_losers_data)
        
    with st.container():
        render_table_card("Maior Volume", top_volume_data)

    st.write("---")
