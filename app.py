import streamlit as st
import requests
import json
import time

# --- CONFIGURAÇÃO ---
COINGECKO_API_URL = "https://api.coingecko.com/api/v3/coins/markets"
API_REFRESH_INTERVAL = 30  # Segundos

st.set_page_config(
    page_title="Meme Coin Radar",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# --- MAPA DAS MOEDAS ---
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

# --- FUNÇÕES DE LÓGICA E DADOS ---
@st.cache_data(ttl=API_REFRESH_INTERVAL)
def fetch_coin_data(retries=3):
    """
    Busca dados de moedas da CoinGecko com tentativas de re-conexão.
    Retries: número de tentativas antes de falhar.
    """
    coin_ids = ",".join(coin_map.keys())
    url = f"{COINGECKO_API_URL}?vs_currency=brl&ids={coin_ids}&price_change_percentage=1h,24h"
    
    for attempt in range(retries):
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            return {coin['id']: coin for coin in data}
        except requests.exceptions.RequestException as e:
            if attempt < retries - 1:
                st.warning(f"Tentativa {attempt + 1}/{retries} falhou. Tentando novamente em 5 segundos...")
                time.sleep(5)
            else:
                st.error(f"Erro ao carregar dados do CoinGecko após {retries} tentativas: {e}")
                return {}
    return {}

def check_for_alerts(current_data):
    """Detecta alertas de preço e volume."""
    alerts = {}
    for id, coin in current_data.items():
        alerts[id] = []
        
        price_change_1h = coin.get('price_change_percentage_1h_in_currency')
        if price_change_1h is not None and abs(price_change_1h) > 5:
            alert_type = 'Aumento' if price_change_1h > 0 else 'Queda'
            alerts[id].append(f"{alert_type} de preço de {abs(price_change_1h):.1f}% na última hora")
        
        # Lógica simplificada de pico de volume para demonstração
        if coin.get('total_volume') is not None and coin['total_volume'] > 100000000:
            alerts[id].append(f"Alto volume: {format_large_number(coin['total_volume'])}")
    return alerts

# --- FUNÇÕES DE FORMATAÇÃO DA UI ---
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

def render_coin_card(coin, alerts):
    with st.container(border=True):
        chain = coin_map.get(coin['id'], 'unknown')
        chain_name, color = get_chain_info(chain)

        st.subheader(f"{coin['name']} ({coin['symbol'].upper()})")
        st.markdown(f"<span style='background-color:{color}; padding: 4px 8px; border-radius: 5px; color: white; font-size: 12px;'>{chain_name}</span>", unsafe_allow_html=True)
        st.write("---")

        col1, col2 = st.columns(2)
        with col1:
            st.metric("Preço", format_currency(coin.get('current_price')))
        with col2:
            st.metric("Volume 24h", format_large_number(coin.get('total_volume')))

        if alerts:
            st.markdown(f"**Alertas Recentes:**")
            for alert in alerts:
                st.info(alert)
        else:
            st.markdown("*Nenhum alerta suspeito recente.*")
        
# --- RENDERIZAÇÃO DA PÁGINA ---
st.title("Meme Coin Radar 🚀")
st.write("Monitorando movimentos suspeitos no mercado de meme coins em tempo real.")

# Botões de filtro
st.write("---")
filter_container = st.container()
with filter_container:
    cols = st.columns(4)
    filters = {'all': 'Todos', 'eth': 'Ethereum', 'sol': 'Solana', 'base': 'Base'}
    for i, (key, label) in enumerate(filters.items()):
        with cols[i]:
            if st.button(label, type="primary" if st.session_state.get('active_filter', 'all') == key else "secondary"):
                st.session_state.active_filter = key
                st.rerun()

# Lógica para carregar os dados
with st.spinner("Carregando dados..."):
    coin_data = fetch_coin_data()
    st.session_state.alerts = check_for_alerts(coin_data)
    
# Exibição do Painel principal
col_count = st.columns(3)
idx = 0
for id, coin in coin_data.items():
    if st.session_state.get('active_filter', 'all') == 'all' or coin_map.get(id) == st.session_state.active_filter:
        with col_count[idx % 3]:
            render_coin_card(coin, st.session_state.alerts.get(id, []))
        idx += 1
