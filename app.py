import streamlit as st
import pandas as pd
import requests
import plotly.graph_objects as go

st.set_page_config(layout="wide", page_title="Altcoin Scanner")
st.title("🚀 급등 주도 알트코인 실시간 스캐너")
st.caption("메이저 제외 / 거래대금 동반 / 고변동성 알트코인 발굴 대시보드")

@st.cache_data(ttl=30)  # 30초마다 갱신
def get_coingecko_market_data():
    url = "https://api.coingecko.com/api/v3/coins/markets"
    params = {
        "vs_currency": "usd",
        "order": "market_cap_desc",
        "per_page": 250, # 시총 상위 250개 추적
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
        
        price_change = coin.get('price_change_percentage_24h')
        volume = coin.get('total_volume')
        
        if price_change is None or volume is None or volume == 0:
            continue
            
        # 가독성을 위해 거래대금을 '백만 달러(Million)' 단위로 변환
        volume_in_million = float(volume) / 1_000_000
            
        crypto_data.append({
            '심볼': f"{symbol}USDT",
            '이름': name,
            '현재가($)': float(coin.get('current_price', 0)),
            '24h 변동률(%)': float(price_change),
            '24h 거래대금(백만$)': volume_in_million,
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
                                    help="BTC, ETH 및 주요 스테이블코인을 리스트에서 숨깁니다.")

# 2. 최소 거래대금 필터 (단위: 백만 달러)
min_volume_million = st.sidebar.slider(
    "최소 24시간 거래대금 (백만 달러)", 
    min_value=0, max_value=500, value=20, step=10,
    help="설정한 금액 미만으로 거래된 소외 코인들을 필터링합니다. (10M = 약 130억 원)"
)

st.sidebar.markdown("---")

# 3. 정렬 기준 설정
sort_by = st.sidebar.selectbox("정렬 기준", ["24h 변동률(%)", "24h 거래대금(백만$)"], index=0)
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
        processed_df = processed_df[~processed_df['이름'].str.contains('USD|Wrapped|Tether', case=False)]

    # [필터링 2] 최소 거래대금 적용
    processed_df = processed_df[processed_df['24h 거래대금(백만$)'] >= min_volume_million]

    # [정렬 및 상위 개수 확장] 기존 15개 -> 30개로 늘려서 매칭 확인을 쉽게 만듭니다.
    df_sorted = processed_df.sort_values(by=sort_by, ascending=ascending).head(30).reset_index(drop=True)
    
    st.subheader(f"🔥 조건 만족 주도 자산 TOP {len(df_sorted)} ({sort_by} 높은 순)")
    
    if not df_sorted.empty:
        col1, col2 = st.columns([13, 9])
        
        with col1:
            display_df = df_sorted.drop(columns=['sparkline'])
            st.dataframe(
                display_df.style.format({
                    '현재가($)': '{:,.4f}',
                    '24h 변동률(%)': '{:+.2f}%',
                    '24h 거래대금(백만$)': '${:,.1f}M'
                }),
                use_container_width=True, height=600
            )
            
        with col2:
            st.markdown("### 📈 선택 자산 실시간 트렌드 (7일)")
            selected_symbol = st.selectbox("상세 차트를 볼 자산 선택", df_sorted['심볼'].tolist())
            
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
                    
                    st.metric(label="현재 가격", value=f"${selected_row['현재가($)']:,.4f}", delta=f"{selected_row['24h 변동률(%)']:+.2f}%")
                else:
                    st.warning("차트 데이터를 불러오지 못했습니다.")
    else:
        st.warning("⚠️ 필터 조건을 만족하는 자산이 없습니다. '최소 거래대금' 슬라이더를 낮춰보세요.")
else:
    st.info("표시할 데이터가 없습니다.")