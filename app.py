import streamlit as st
import requests
import json
import time

# --- Configuração da Página ---
st.set_page_config(
    page_title="Meme Coin Radar",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# --- Constantes e Variáveis de Estado ---
GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"] if "GEMINI_API_KEY" in st.secrets else ""
COINGECKO_API_URL = "https://api.coingecko.com/api/v3/coins/markets"
API_REFRESH_INTERVAL = 30  # Segundos

coin_map = {
    'dogwifhat': 'sol',
    'pepe': 'eth',
    'book-of-meme': 'sol',
    'brett': 'base',
    'bonk': 'sol',
    'mog-coin': 'eth',
    'toshi': 'base',
    'floki': 'eth',
    'silly-goose': 'sol',
    'shiba-inu': 'eth',
    'baby-doge-coin': 'eth'
}

if 'active_filter' not in st.session_state:
    st.session_state.active_filter = 'all'
if 'selected_coin' not in st.session_state:
    st.session_state.selected_coin = None
if 'alerts' not in st.session_state:
    st.session_state.alerts = {}
if 'coin_data' not in st.session_state:
    st.session_state.coin_data = {}

# --- Funções de Formatação ---
def format_currency(value):
    if value is None:
        return "N/A"
    if value < 0.01:
        return f"R$ {value:,.8f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def format_large_number(value):
    if value is None:
        return "N/A"
    if value >= 1e9:
        return f"R$ {value/1e9:.2f}B"
    if value >= 1e6:
        return f"R$ {value/1e6:.2f}M"
    if value >= 1e3:
        return f"R$ {value/1e3:.2f}K"
    return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def get_chain_info(chain):
    chains = {
        'eth': ('Ethereum', '#8B5CF6'),
        'sol': ('Solana', '#A855F7'),
        'base': ('Base', '#0EA5E9'),
        'unknown': ('Unknown', '#94A3B8')
    }
    return chains.get(chain, chains['unknown'])

# --- Funções de API (com cache) ---
@st.cache_data(ttl=API_REFRESH_INTERVAL)
def fetch_coin_data():
    coin_ids = ",".join(coin_map.keys())
    url = f"{COINGECKO_API_URL}?vs_currency=brl&ids={coin_ids}&price_change_percentage=1h,24h"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        return {coin['id']: coin for coin in data}
    except requests.exceptions.RequestException as e:
        st.error(f"Erro ao carregar dados do CoinGecko: {e}")
        return {}

def generate_gemini_analysis(coin_data):
    user_prompt = f"""
    Atue como um analista de mercado de criptomoedas profissional. Com base nos seguintes dados para a meme coin {coin_data['name']} ({coin_data['symbol'].upper()}), forneça uma análise muito breve, concisa e acionável. Foque nos alertas de atividade suspeita e nas principais métricas como preço, volume e capitalização de mercado. A resposta deve ser em português.

    Meme Coin: {coin_data['name']} ({coin_data['symbol'].upper()})
    Preço Atual: {format_currency(coin_data['current_price'])}
    Mudança 24h: {coin_data['price_change_percentage_24h']:.1f}%
    Volume 24h: {format_large_number(coin_data['total_volume'])}
    Capitalização de Mercado: {format_large_number(coin_data['market_cap'])}
    Alertas Recentes: {', '.join(st.session_state.alerts[coin_data['id']]) if st.session_state.alerts[coin_data['id']] else 'Nenhuma atividade suspeita.'}
    
    Forneça um breve resumo e uma visão acionável para um potencial comprador.
    """
    
    payload = {
        "contents": [{"parts": [{"text": user_prompt}]}],
    }

    try:
        response = requests.post(
            f"{st.secrets['GEMINI_API_URL']}?key={GEMINI_API_KEY}",
            headers={'Content-Type': 'application/json'},
            data=json.dumps(payload),
            timeout=30
        )
        response.raise_for_status()
        result = response.json()
        analysis = result['candidates'][0]['content']['parts'][0]['text']
        return analysis
    except requests.exceptions.RequestException as e:
        return f"Erro ao gerar análise: {e}"

# --- Funções Auxiliares para Análise ---
def check_for_alerts(current_data, previous_data):
    for id, coin in current_data.items():
        if id not in st.session_state.alerts:
            st.session_state.alerts[id] = []
        
        previous_coin = previous_data.get(id)
        if not previous_coin:
            continue

        price_change_1h = coin.get('price_change_percentage_1h_in_currency')
        if price_change_1h is not None and abs(price_change_1h) > 5:
            alert_type = 'Aumento' if price_change_1h > 0 else 'Queda'
            st.session_state.alerts[id].append(f"{alert_type} de preço de {abs(price_change_1h):.1f}% na última hora")
        
        current_volume = coin.get('total_volume', 0)
        previous_volume = previous_coin.get('total_volume', 0)
        if previous_volume > 0:
            volume_change = (current_volume - previous_volume) / previous_volume
            if volume_change > 0.5:
                st.session_state.alerts[id].append(f"Pico de volume de {volume_change * 100:.0f}%")
        
        if len(st.session_state.alerts[id]) > 5:
            st.session_state.alerts[id] = st.session_state.alerts[id][-5:]

def render_coin_card(coin, chain_info, alerts):
    with st.container(border=True):
        st.subheader(f"{coin['name']} ({coin['symbol'].upper()})")
        
        chain_name, color = chain_info
        st.markdown(f"<span style='background-color:{color}; padding: 4px 8px; border-radius: 5px; color: white; font-size: 12px;'>{chain_name}</span>", unsafe_allow_html=True)
        
        st.write("---")
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Preço", format_currency(coin['current_price']))
        with col2:
            st.metric("Volume 24h", format_large_number(coin['total_volume']))
        
        if alerts:
            st.markdown(f"**Alertas Recentes:**")
            for alert in alerts:
                st.info(alert)
        else:
            st.markdown("*Nenhum alerta suspeito recente.*")
        
        st.write("---")
        if st.button("Analisar", key=f"btn_{coin['id']}"):
            st.session_state.selected_coin = coin['id']
            st.rerun()

# --- Renderização Principal do Aplicativo ---
st.title("Meme Coin Radar 🚀")
st.write("Monitorando movimentos suspeitos no mercado de meme coins em tempo real.")

# Botões de Filtro
st.write("---")
filter_container = st.container()
with filter_container:
    col_all, col_eth, col_sol, col_base = st.columns(4)
    with col_all:
        if st.button("Todos", type="primary" if st.session_state.active_filter == 'all' else "secondary"):
            st.session_state.active_filter = 'all'
            st.session_state.selected_coin = None
            st.rerun()
    with col_eth:
        if st.button("Ethereum", type="primary" if st.session_state.active_filter == 'eth' else "secondary"):
            st.session_state.active_filter = 'eth'
            st.session_state.selected_coin = None
            st.rerun()
    with col_sol:
        if st.button("Solana", type="primary" if st.session_state.active_filter == 'sol' else "secondary"):
            st.session_state.active_filter = 'sol'
            st.session_state.selected_coin = None
            st.rerun()
    with col_base:
        if st.button("Base", type="primary" if st.session_state.active_filter == 'base' else "secondary"):
            st.session_state.active_filter = 'base'
            st.session_state.selected_coin = None
            st.rerun()

# Lógica para carregar os dados
previous_coin_data = st.session_state.get('coin_data', {})
with st.spinner("Carregando dados..."):
    coin_data = fetch_coin_data()
    st.session_state.coin_data = coin_data
    check_for_alerts(coin_data, previous_coin_data)

# Exibição do "Modal" de detalhes da moeda
if st.session_state.selected_coin:
    selected_coin_data = coin_data.get(st.session_state.selected_coin)
    if selected_coin_data:
        st.subheader(f"Detalhes de {selected_coin_data['name']}")
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Preço Atual", format_currency(selected_coin_data['current_price']))
        with col2:
            st.metric("Mudança 24h", f"{selected_coin_data['price_change_percentage_24h']:.1f}%")
        
        st.metric("Volume 24h", format_large_number(selected_coin_data['total_volume']))
        st.metric("Capitalização de Mercado", format_large_number(selected_coin_data['market_cap']))
        
        st.markdown("---")
        
        if st.button("Gerar Análise com ✨Gemini"):
            with st.spinner("Gerando análise..."):
                analysis_text = generate_gemini_analysis(selected_coin_data)
                st.session_state.gemini_analysis = analysis_text
        
        if 'gemini_analysis' in st.session_state:
            st.subheader("Análise de Mercado com Gemini")
            st.write(st.session_state.gemini_analysis)
        
        st.write("---")
        if st.button("Voltar para o painel"):
            st.session_state.selected_coin = None
            st.session_state.gemini_analysis = None
            st.rerun()

# Exibição do Painel principal
else:
    col_count = st.columns(3)
    idx = 0
    for id, coin in coin_data.items():
        if st.session_state.active_filter == 'all' or coin_map.get(id) == st.session_state.active_filter:
            with col_count[idx % 3]:
                chain_info = get_chain_info(coin_map.get(id))
                render_coin_card(coin, chain_info, st.session_state.alerts.get(id, []))
            idx += 1
