import streamlit as st
import pandas as pd
import requests
import plotly.graph_objects as go

# Streamlit 페이지 설정
st.set_page_config(layout="wide", page_title="Binance Crypto Dashboard")
st.title("📊 바이낸스 실시간 시장 대시보드")

# 1. 바이낸스 24시간 Ticker 데이터 가져오기 (USDT 마켓 기준)
@st.cache_data(ttl=10)  # 10초마다 데이터 캐싱 갱신
def get_binance_ticker():
    # 기존 주소(api.binance.com) 대신 api3 또는 api1, api2 사용
    url = "https://api3.binance.com/api/v3/ticker/24hr"
    response = requests.get(url).json()
    # ... 이하 기존 코드 동일
    
    # USDT 마켓만 필터링
    usdt_data = [ticker for ticker in response if ticker['symbol'].endswith('USDT')]
    
    df = pd.DataFrame(usdt_data)
    # 필요한 컬럼만 추출 및 타입 변환
    df = df[['symbol', 'lastPrice', 'priceChangePercent', 'volume', 'quoteVolume']]
    df.columns = ['심볼', '현재가', '24h 변동률(%)', '거래량', '거래대금(USDT)']
    
    df['현재가'] = pd.to_numeric(df['현재가'])
    df['24h 변동률(%)'] = pd.to_numeric(df['24h 변동률(%)'])
    df['거래량'] = pd.to_numeric(df['거래량'])
    df['거래대금(USDT)'] = pd.to_numeric(df['거래대금(USDT)'])
    
    return df

# 2. 특정 심볼의 최근 캔들 데이터 가져오기 (간략 차트용)
def get_klines(symbol, interval='1h', limit=24):
    # 여기도 마찬가지로 api3로 변경
    url = f"https://api3.binance.com/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}"
    res = requests.get(url).json()
    # ... 이하 기존 코드 동일
    # 종가(Close Price)만 추출
    closes = [float(candle[4]) for candle in res]
    return closes

# 데이터 로드
try:
    df = get_binance_ticker()
except Exception as e:
    st.error("데이터를 가져오는 중 오류가 발생했습니다.")
    df = pd.DataFrame()

# 사이드바 - 정렬 기준 선택
st.sidebar.header("⚙️ 정렬 및 필터 설정")
sort_by = st.sidebar.selectbox(
    "정렬 기준을 선택하세요",
    ["24h 변동률(%)", "거래대금(USDT)", "거래량"]
)
order = st.sidebar.radio("정렬 순서", ["내림차순 (높은 순)", "오름차순 (낮은 순)"])
ascending = True if order == "오름차순 (낮은 순)" else False

# 데이터 정렬 및 상위 10개 추출
if not df.empty:
    df_sorted = df.sort_values(by=sort_by, ascending=ascending).head(10).reset_index(drop=True)
    
    # 메인 화면 레이아웃 구성
    st.subheader(f"🔥 {sort_by} {order} 상위 10개 자산")
    
    # 테이블 표기용 컬럼과 차트 표기용 컬럼을 나누어 레이아웃 배치
    col1, col2 = st.columns([3, 2])
    
    with col1:
        # 데이터프레임 포맷팅하여 출력
        st.dataframe(
            df_sorted.style.format({
                '현재가': '{:,.4f}',
                '24h 변동률(%)': '{:+.2f}%',
                '거래량': '{:,.0f}',
                '거래대금(USDT)': '${:,.0f}'
            }),
            use_container_width=True,
            height=450
        )
        
    with col2:
        st.markdown("### 📈 선택한 자산 24시간 흐름 (1시간 봉)")
        # 유저가 리스트에서 차트로 보고 싶은 심볼 선택
        selected_symbol = st.selectbox("간략 차트를 볼 심볼 선택", df_sorted['심볼'].tolist())
        
        if selected_symbol:
            prices = get_klines(selected_symbol)
            
            # Plotly를 이용한 간략한 라인 차트 (Sparkline 스타일)
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                y=prices, 
                mode='lines', 
                line=dict(color='#10B981' if prices[-1] >= prices[0] else '#EF4444', width=3),
                fill='tozeroy',
                fillcolor='rgba(16, 185, 129, 0.1)' if prices[-1] >= prices[0] else 'rgba(239, 68, 68, 0.1)'
            ))
            
            fig.update_layout(
                xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                yaxis=dict(showgrid=True, zeroline=False, showticklabels=True),
                margin=dict(l=20, r=20, t=10, b=10),
                height=300,
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)'
            )
            st.plotly_chart(fig, use_container_width=True)

else:
    st.info("표시할 데이터가 없습니다.")