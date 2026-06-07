import streamlit as st
import pandas as pd
import requests
import plotly.graph_objects as go

# 페이지 레이아웃 설정
st.set_page_config(layout="wide", page_title="Binance Crypto Dashboard")
st.title("📊 바이낸스 실시간 시장 대시보드")

@st.cache_data(ttl=15)
def get_binance_ticker():
    # [우회핵심 1] 클라우드 서버 차단이 덜한 미국 전용 도메인(binance.us)으로 타겟 변경
    url = "https://api.binance.us/api/v3/ticker/24hr"
    
    # [우회핵심 2] 파이썬 봇이 아니라 일반 크롬 브라우저 유저인 것처럼 헤더(User-Agent) 위장
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    response = requests.get(url, headers=headers).json()
    
    # USDT 마켓만 필터링
    usdt_data = [ticker for ticker in response if ticker['symbol'].endswith('USDT')]
    
    df = pd.DataFrame(usdt_data)
    df = df[['symbol', 'lastPrice', 'priceChangePercent', 'volume', 'quoteVolume']]
    df.columns = ['심볼', '현재가', '24h 변동률(%)', '거래량', '거래대금(USDT)']
    
    df['현재가'] = pd.to_numeric(df['현재가'])
    df['24h 변동률(%)'] = pd.to_numeric(df['24h 변동률(%)'])
    df['거래량'] = pd.to_numeric(df['거래량'])
    df['거래대금(USDT)'] = pd.to_numeric(df['거래대금(USDT)'])
    
    return df

def get_klines(symbol, interval='1h', limit=24):
    url = f"https://api.binance.us/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    res = requests.get(url, headers=headers).json()
    closes = [float(candle[4]) for candle in res]
    return closes

# 데이터 로딩 시도 및 예외처리 메시지 상세화
try:
    df = get_binance_ticker()
except Exception as e:
    st.error(f"데이터를 가져오는 중 오류가 발생했습니다. (원인: {e})")
    df = pd.DataFrame()

# 사이드바 설정
st.sidebar.header("⚙️ 정렬 및 필터 설정")
sort_by = st.sidebar.selectbox("정렬 기준을 선택하세요", ["24h 변동률(%)", "거래대금(USDT)", "거래량"])
order = st.sidebar.radio("정렬 순서", ["내림차순 (높은 순)", "오름차순 (낮은 순)"])
ascending = True if order == "오름차순 (낮은 순)" else False

if not df.empty:
    df_sorted = df.sort_values(by=sort_by, ascending=ascending).head(10).reset_index(drop=True)
    st.subheader(f"🔥 {sort_by} {order} 상위 10개 자산")
    
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
                prices = get_klines(selected_symbol)
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
            except:
                st.warning("차트 데이터를 불러오지 못했습니다.")
else:
    st.info("표시할 데이터가 없습니다.")