import streamlit as st
import pandas as pd
import requests
import plotly.graph_objects as go

st.set_page_config(layout="wide", page_title="Binance Futures Realtime Dashboard")
st.title("🔥 바이낸스 USDT 무기한 선물(Perpetual) 대시보드")

@st.cache_data(ttl=15)
def get_binance_futures_ticker():
    # 기본 도메인이 막힐 경우를 대비해 바이낸스의 공식 대체 도메인(fapi1, fapi2 등)을 시도해볼 수 있습니다.
    # 우선 가장 안정적인 기본 메인넷 주소를 사용하되, 예외 처리를 강화합니다.
    url = "https://fapi.binance.com/fapi/v1/ticker/24hr"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    res_raw = requests.get(url, headers=headers)
    
    # HTTP 상태 코드가 200(정상)이 아닐 때 에러 발생시키기
    if res_raw.status_code != 200:
        raise Exception(f"바이낸스 서버 응답 에러 (Status Code: {res_raw.status_code}) - {res_raw.text}")
        
    response = res_raw.json()
    
    # 만약 response가 리스트 형식이 아니라 딕셔너리(에러 메시지)라면 예외 처리
    if isinstance(response, dict) and "msg" in response:
        raise Exception(f"바이낸스 API 에러: {response.get('msg')} (코드: {response.get('code')})")
    
    futures_data = []
    for ticker in response:
        # 안전하게 데이터가 딕셔너리인지 한 번 더 확인
        if not isinstance(ticker, dict):
            continue
            
        symbol = ticker.get('symbol', '')
        
        # 1. USDT 마켓만 필터링
        # 2. 분기별 선물 제외하고 오직 무기한(Perpetual)만 걸러내기
        if symbol.endswith('USDT') and ('_' not in symbol):
            
            # 간혹 거래대금이 없는 신규/테스트 쌍 제외
            if float(ticker.get('quoteVolume', 0)) == 0:
                continue
                
            futures_data.append({
                '심볼': symbol,
                '현재가': float(ticker.get('lastPrice', 0)),
                '24h 변동률(%)': float(ticker.get('priceChangePercent', 0)),
                '거래량': float(ticker.get('volume', 0)),
                '거래대금(USDT)': float(ticker.get('quoteVolume', 0))
            })
            
    df = pd.DataFrame(futures_data)
    return df

def get_binance_futures_klines(symbol, interval='1h', limit=24):
    url = f"https://fapi.binance.com/fapi/v1/klines?symbol={symbol}&interval={interval}&limit={limit}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    res_raw = requests.get(url, headers=headers)
    if res_raw.status_code == 200:
        res = res_raw.json()
        if isinstance(res, list):
            closes = [float(candle[4]) for candle in res]
            return closes
    return []

try:
    df = get_binance_futures_ticker()
except Exception as e:
    st.error(f"❌ 데이터 로드 실패: {e}")
    st.info("💡 팁: Streamlit Cloud 공용 서버의 IP가 바이낸스로부터 일시적으로 차단되었을 수 있습니다. 잠시 후 다시 시도하거나 주소를 변경해야 할 수 있습니다.")
    df = pd.DataFrame()

# 사이드바 설정
st.sidebar.header("⚙️ 정렬 및 필터 설정")
sort_by = st.sidebar.selectbox("정렬 기준을 선택하세요", ["24h 변동률(%)", "거래대금(USDT)", "거래량"])
order = st.sidebar.radio("정렬 순서", ["내림차순 (높은 순)", "오름차순 (낮은 순)"])
ascending = True if order == "오름차순 (낮은 순)" else False

if not df.empty:
    df_sorted = df.sort_values(by=sort_by, ascending=ascending).head(10).reset_index(drop=True)
    st.subheader(f"⚡ 퓨처스(Perpetual) {sort_by} {order} 상위 10개 자산")
    
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
        st.markdown("### 📈 선택한 선물 자산 24시간 흐름 (1시간 봉)")
        selected_symbol = st.selectbox("간략 차트를 볼 심볼 선택", df_sorted['심볼'].tolist())
        
        if selected_symbol:
            try:
                prices = get_binance_futures_klines(selected_symbol)
                if prices:
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
                else:
                    st.warning("차트 데이터를 비어있습니다.")
            except Exception as e:
                st.warning("차트 데이터를 불러오지 못했습니다.")
else:
    st.info("표시할 데이터가 없습니다. 위의 에러 메시지를 확인하세요.")