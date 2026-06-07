import streamlit as st
import pandas as pd
import ccxt
import plotly.graph_objects as go

st.set_page_config(layout="wide", page_title="Binance Global Realtime Dashboard")
st.title("📊 바이낸스 본진(Global) 실시간 시장 대시보드")

# [우회 조치] 클라우드 지역 제한(451 에러)을 우회하기 위한 프록시/예비 도메인 설정
exchange = ccxt.binance({
    'enableRateLimit': True,
    'urls': {
        'api': {
            'public': 'https://api1.binance.com/api/v3', # 메인 대신 api1 예비 도메인 명시
        },
    },
    'options': {
        'defaultType': 'spot',
        'adjustForTimeDifference': True # 클라우드 서버와 바이낸스 간 시간 차이 보정
    },
    # 일반 브라우저처럼 보이기 위한 헤더 강제 주입
    'headers': {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
})

@st.cache_data(ttl=15) # 15초 데이터 유지
def get_global_binance_ticker():
    # fetch_tickers 대신 지역 제한 체크를 덜 타는 24hr 전체 티커 API 직접 매핑 방식 사용
    tickers = exchange.public_get_ticker_24hr()
    
    usdt_data = []
    for ticker in tickers:
        symbol = ticker['symbol']
        # USDT 마켓만 필터링
        if symbol.endswith('USDT'):
            # 레버리지/이상 토큰 필터링
            if 'UP' in symbol or 'DOWN' in symbol or 'BEAR' in symbol or 'BULL' in symbol:
                continue
                
            usdt_data.append({
                '심볼': symbol,
                '현재가': float(ticker['lastPrice']),
                '24h 변동률(%)': float(ticker['priceChangePercent']),
                '거래량': float(ticker['volume']),
                '거래대금(USDT)': float(ticker['quoteVolume'])
            })
            
    df = pd.DataFrame(usdt_data)
    return df

def get_global_klines(symbol, interval='1h', limit=24):
    # 차트용 캔들 조회도 예비 도메인으로 우회 호출
    params = {'symbol': symbol, 'interval': interval, 'limit': limit}
    ohlcv = exchange.public_get_klines(params)
    closes = [float(candle[4]) for candle in ohlcv] # 종가 추출
    return closes

try:
    df = get_global_binance_ticker()
except Exception as e:
    st.error(f"글로벌 바이낸스 데이터를 가져오는 데 실패했습니다.\n\n원인: {e}")
    st.info("💡 만약 서버 국가 차단이 지속될 경우, 잠시 후 대시보드 우측 하단의 [Reboot]을 실행해 주세요.")
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
                st.warning("차트 데이터를 불러오지 못했습니다.")
else:
    st.info("표시할 데이터가 없습니다.")