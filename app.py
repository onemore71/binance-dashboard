import streamlit as st
import pandas as pd
import requests
import plotly.graph_objects as go

st.set_page_config(layout="wide", page_title="Altcoin Scanner")
st.title("🚀 급등 주도 알트코인 실시간 스캐너")
st.caption("메이저 제외 / 거래대금 동반 / 고변동성 알트코인 발굴 대시보드")

@st.cache_data(ttl=30)  # 30초마다 갱신
def get_coingecko_market_data():
    # 시가총액 상위 300개 코인을 긁어와 알트코인 풀을 넓힙니다.
    url = "https://api.coingecko.com/api/v3/coins/markets"
    params = {
        "vs_currency": "usd",
        "order": "market_cap_desc",
        "per_page": 300,
        "page": 1,
        "sparkline": "true",
        "price_change_percentage": "24h"
    }
    
    response = requests.get(url, params=params)
    if response.status_code != 200:
        raise Exception(f"코인게코 API 로드 실패 (Status: {response.status_code})")
        
    data = response.json()
    
    crypto_data = []
    for coin in data:
        symbol = coin['symbol'].upper()
        name = coin['name']
        
        # 데이터 정제 및 예외 처리
        price_change = coin.get('price_change_percentage_24h')
        volume = coin.get('total_volume')
        
        if price_change is None or volume is None or volume == 0:
            continue
            
        crypto_data.append({
            '심볼': f"{symbol}USDT",
            '이름': name,
            '현재가($)': float(coin.get('current_price', 0)),
            '24h 변동률(%)': float(price_change),
            '24h 거래대금(USD)': float(volume),
            'sparkline': coin.get('sparkline_in_7d', {}).get('price', [])
        })
        
    return pd.DataFrame(crypto_data)

try:
    df = get_coingecko_market_data()
except Exception as e:
    st.error(f"❌ 데이터 로드 실패: {e}")
    df = pd.DataFrame()

# ⚙️ 사이드바 필터 및 정렬 설정
st.sidebar.header("🔍 알트코인 필터링 조건")

# 1. 메이저 코인 및 스테이블 코인 제외 토글
exclude_majors = st.sidebar.checkbox("메이저 & 스테이블 코인 제외", value=True, 
                                    help="BTC, ETH 및 주요 스테이블코인(USDT, USDC, DAI 등)을 리스트에서 숨깁니다.")

# 2. 최소 거래대금 필터 (단위: 백만 달러)
# 10M = 천만 달러 (약 130억 원), 50M = 5천만 달러
min_volume_million = st.sidebar.slider(
    "최소 24시간 거래대금 (백만 달러)", 
    min_value=0, max_value=500, value=20, step=10,
    help="돈이 몰리지 않은 거래량 전무한 코인을 필터링합니다."
)

st.sidebar.separator()

# 3. 정렬 기준 설정 (기본값을 24h 변동률로 설정하여 급등주 우선 배치)
sort_by = st.sidebar.selectbox("정렬 기준", ["24h 변동률(%)", "24h 거래대금(USD)"], index=0)
order = st.sidebar.radio("정렬 순서", ["내림차순 (높은 순)", "오름차순 (낮은 순)"])
ascending = True if order == "오름차순 (낮은 순)" else False


if not df.empty:
    processed_df = df.copy()
    
    # [필터링 1] 메이저 및 스테이블 코인 제외 로직
    if exclude_majors:
        majors_and_stables = [
            'BTCUSDT', 'ETHUSDT', 'USDTUSDT', 'USDCUSDT', 
            'DAIUSDT', 'FDUSDUSDT', 'STETHUSDT', 'WETHUSDT', 'WBTCUSDT'
        ]
        processed_df = processed_df[~processed_df['심볼'].isin(majors_and_stables)]
        # 이름 기반으로 랩핑된 자산이나 스테이블 추가 차단
        processed_df = processed_df[~processed_df['이름'].str.contains('USD|Wrapped|Tether', case=False)]

    # [필터링 2] 최소 거래대금 적용 (설정한 백만 달러 단위 거르기)
    min_volume_bytes = min_volume_million * 1_000_000
    processed_df = processed_df[processed_df['24h 거래대금(USD)'] >= min_volume_bytes]

    # [정렬 및 상위 15개 추출]
    df_sorted = processed_df.sort_values(by=sort_by, ascending=ascending).head(15).reset_index(drop=True)
    
    st.subheader(f"🔥 조건 만족 주도 알트코인 TOP 15 ({sort_by} 높은 순)")
    
    if not df_sorted.empty:
        col1, col2 = st.columns([13, 9])
        
        with col1:
            # 유저 화면에 노출할 데이터프레임 포맷팅 (차트 데이터 제외)
            display_df = df_sorted.drop(columns=['sparkline'])
            st.dataframe(
                display_df.style.format({
                    '현재가($)': '{:,.4f}',
                    '24h 변동률(%)': '{:+.2f}%',
                    '24h 거래대금(USD)': '${:,.0f}'
                }),
                use_container_width=True, height=520
            )
            
        with col2:
            st.markdown("### 📈 주도 알트코인 실시간 트렌드 (7일)")
            selected_symbol = st.selectbox("상세 차트를 볼 알트코인 선택", df_sorted['심볼'].tolist())
            
            if selected_symbol:
                selected_row = df_sorted[df_sorted['심볼'] == selected_symbol].iloc[0]
                prices = selected_row['sparkline']
                
                if prices and len(prices) > 1:
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
                        margin=dict(l=25, r=25, t=10, b=10), height=320,
                        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)'
                    )
                    st.plotly_chart(fig, use_container_width=True)
                    
                    # 실시간 초간단 트레이딩 팁 메타데이터 출력
                    st.metric(label="현재 가격", value=f"${selected_row['현재가($)']:,.4f}", delta=f"{selected_row['24h 변동률(%)']:+.2f}%")
                else:
                    st.warning("차트 데이터를 불러오지 못했습니다.")
    else:
        st.warning("⚠️ 필터 조건을 만족하는 알트코인이 없습니다. '최소 거래대금' 슬라이더를 낮춰보세요.")
else:
    st.info("표시할 데이터가 없습니다.")