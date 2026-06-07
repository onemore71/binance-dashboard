import streamlit as st
import pandas as pd
import ccxt
import plotly.graph_objects as go
from datetime import datetime

st.set_page_config(layout="wide", page_title="Binance Global Realtime Dashboard")
st.title("📊 바이낸스 본진(Global) 실시간 시장 대시보드")

# CCXT 바이낸스 객체 생성 (전 세계 공통 binance.com 본진 데이터)
exchange = ccxt.binance({
    'enableRateLimit': True,
    'options': {
        'defaultType': 'spot' # 스팟(현물) 마켓 기준
    }
})

@st.cache_data(ttl=10) # 10초 캐싱
def get_global_binance_ticker():
    # CCXT를 통해 바이낸스 본진의 모든 티커를 한 번에 호출 (차단 우회 최적화 내장)
    tickers = exchange.fetch_tickers()
    
    usdt_data = []
    for symbol, ticker in tickers.items():
        # USDT 마켓만 필터링 (예: BTC/USDT)
        if symbol.endswith('/USDT'):
            # 레버리지 토큰(UP/DOWN) 제외하여 노이즈 제거
            if 'UP/' in symbol or 'DOWN/' in symbol:
                continue
                
            usdt_data.append({
                '심볼': symbol.replace('/', ''), # 대시보드 표시용 (BTCUSDT)
                '현재가': ticker['last'],
                '24h 변동률(%)': ticker['percentage'], # 글로벌 본진 변동률
                '거래량': ticker['baseVolume'],
                '거래대금(USDT)': ticker['quoteVolume'] # 글로벌 본진 거래대금
            })
            
    df = pd.DataFrame(usdt_data)
    return df

def get_global_klines(symbol_display, interval='1h', limit=24):
    # 디스플레이용 심볼을 CCXT용 심볼(BTC/USDT)로 역변환
    ccxt_symbol = f"{symbol_display[:-4]}/{symbol_display[-4:]}"
    # 캔들 데이터 수집
    ohlcv = exchange.fetch_ohlcv(ccxt_symbol, timeframe=interval, limit=limit)
    closes = [candle[4] for candle in ohlcv] # 종가만 추출
    return closes

try:
    df = get_global_binance_ticker()
except Exception as e:
    st.error(f"글로벌 바이낸스 데이터를 가져오는 데 실패했습니다. (원인: {e})")
    df = pd.DataFrame()

# 사이드바 설정
st.sidebar.header("⚙️ 정렬 및 필터 설정")
sort_by = st.sidebar.selectbox("정렬 기준을 선택하세요", ["24h 변동률(%)", "거래대금(USDT)", "거래량"])
order = st.sidebar.radio("정렬 순서", ["내림차순 (높은 순)", "오름차순 (낮은 순)"])
ascending = True if order == "오름차순 (낮은 순)" else False

if not df.empty:
    df_sorted = df.sort_values(by=sort_by, ascending=ascending).head(10).reset_index(drop=True)
    st.subheader(f"🔥 글로벌 본진 {sort_by} {order} 상위 10개 자산")
    
    col1, col2 = st.columns([3, 2])
    with col1:
        st.dataframe(
            df_sorted.style.format({
                '현재가': '{:,.4f}',
                '24h 변동률(%)': '{:+.2f}%',
                '거래량': '{:,.0f}',
                '거래대금(USDT)': '${:,.0f}'
            }),
            use_container_width=True, height=450
        )
        
    with col2:
        st.markdown("### 📈 선택한 자산 24시간 흐름 (1시간 봉)")
        selected_symbol = st.selectbox("간략 차트를 볼 심볼 선택", df_sorted['심볼'].tolist())
        
        if selected_symbol:
            try:
                prices = get_global_klines(selected_symbol)
                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    y=prices, mode='lines', 
                    line=dict(color='#10B981' if prices[-1] >= prices[0] else '#EF4444', width=3),
                    fill='tozeroy',
                    fillcolor='rgba(16, 185, 129, 0.1)' if prices[-1] >= prices[0] else 'rgba(239, 68, 68, 0.1)'
                ))
                fig.update_layout(
                    xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                    yaxis=dict(showgrid=True, zeroline=False, showticklabels=True),
                    margin=dict(l=20, r=20, t=10, b=10), height=300,
                    paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)'
                )
                st.plotly_chart(fig, use_container_width=True)
            except Exception as e:
                st.warning(f"차트 데이터를 불러오지 못했습니다. ({e})")
else:
    st.info("표시할 데이터가 없습니다.")