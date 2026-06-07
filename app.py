import streamlit as st
import pandas as pd
import requests
import plotly.graph_objects as go

st.set_page_config(layout="wide", page_title="Altcoin Scanner")
st.title("🚀 급등 주도 알트코인 실시간 스캐너")
st.caption("메이저 제외 / 거래대금 동반 / 코인게코 IP 규제 프리 데이터 연동")

@st.cache_data(ttl=30)  # 30초마다 데이터 갱신
def get_coingecko_market_data():
    url = "https://api.coingecko.com/api/v3/coins/markets"
    params = {
        "vs_currency": "usd",
        "order": "market_cap_desc",
        "per_page": 250, 
        "page": 1,
        "sparkline": "true",  # 7일간의 트렌드 선 차트 데이터를 포함하여 수집
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
exclude_majors = st.sidebar.checkbox("메이저 & 스테이블 코인 제외", value=True)
min_volume_million = st.sidebar.slider("최소 24시간 거래대금 (백만 달러)", min_value=0, max_value=500, value=20, step=10)

st.sidebar.markdown("---")
sort_by = st.sidebar.selectbox("정렬 기준", ["24h 변동률(%)", "24h 거래대금(백만$)"], index=0)
order = st.sidebar.radio("정렬 순서", ["내림차순 (높은 순)", "오름차순 (낮은 순)"])
ascending = True if order == "오름차순 (낮은 순)" else False


if not df.empty:
    processed_df = df.copy()
    
    # [필터링 1] 메이저 및 스테이블 코인 제외
    if exclude_majors:
        majors_and_stables = ['BTCUSDT', 'ETHUSDT', 'USDTUSDT', 'USDCUSDT', 'DAIUSDT', 'FDUSDUSDT', 'STETHUSDT', 'WETHUSDT', 'WBTCUSDT']
        processed_df = processed_df[~processed_df['심볼'].isin(majors_and_stables)]
        processed_df = processed_df[~processed_df['이름'].str.contains('USD|Wrapped|Tether', case=False)]

    # [필터링 2] 최소 거래대금 적용
    processed_df = processed_df[processed_df['24h 거래대금(백만$)'] >= min_volume_million]
    
    # 정렬 및 상위 30개 종목 확정
    df_sorted = processed_df.sort_values(by=sort_by, ascending=ascending).head(30).reset_index(drop=True)
    
    st.subheader(f"🔥 조건 만족 주도 자산 TOP {len(df_sorted)} ({sort_by} 높은 순)")
    st.caption("💡 테이블에서 원하는 알트코인 행을 클릭하면 우측 7일 가격 차트가 연동됩니다.")
    
    if not df_sorted.empty:
        col1, col2 = st.columns([12, 10])
        
        with col1:
            # 화면 표시용 데이터프레임에서는 차트 원본 배열 데이터를 가려줍니다.
            display_df = df_sorted.drop(columns=['sparkline'])
            
            event = st.dataframe(
                display_df.style.format({
                    '현재가($)': '{:,.4f}',
                    '24h 변동률(%)': '{:+.2f}%',
                    '24h 거래대금(백만$)': '${:,.1f}M'
                }),
                use_container_width=True, 
                height=600,
                selection_mode="single-row", 
                on_select="rerun"
            )
            
        with col2:
            # 테이블 클릭 감지 (기본값은 리스트 1위 종목)
            selected_row_index = 0
            if event and event.get("selection", {}).get("rows"):
                selected_row_index = event["selection"]["rows"][0]
            
            selected_row = df_sorted.iloc[selected_row_index]
            target_symbol = selected_row['심볼']
            sparkline_prices = selected_row['sparkline']
            
            st.markdown(f"### 📈 {target_symbol} 실시간 트렌드 (최근 7일)")
            
            # 코인게코 선 차트 렌더링
            if sparkline_prices and len(sparkline_prices) > 1:
                fig = go.Figure()
                
                # 상승/하락 여부에 따른 차트 테마 설정 (초록/빨강)
                is_positive = sparkline_prices[-1] >= sparkline_prices[0]
                line_color = '#10B981' if is_positive else '#EF4444'
                fill_color = 'rgba(16, 185, 129, 0.08)' if is_positive else 'rgba(239, 68, 68, 0.08)'
                
                fig.add_trace(go.Scatter(
                    y=sparkline_prices, 
                    mode='lines',
                    line=dict(color=line_color, width=3),
                    fill='tozeroy', 
                    fillcolor=fill_color,
                    name="Price"
                ))
                
                fig.update_layout(
                    xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                    yaxis=dict(showgrid=True, zeroline=False, showticklabels=True, gridcolor='rgba(128,128,128,0.15)'),
                    margin=dict(l=25, r=25, t=10, b=10), 
                    height=380,
                    paper_bgcolor='rgba(0,0,0,0)', 
                    plot_bgcolor='rgba(0,0,0,0)'
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.warning("⚠️ 차트 데이터를 불러올 수 없습니다.")
                
            # 하단 현재 스탯 메트릭 노출
            st.metric(
                label=f"{selected_row['이름']} 현재 가격", 
                value=f"${selected_row['현재가($)']:,.4f}", 
                delta=f"{selected_row['24h 변동률(%)']:+.2f}%"
            )
    else:
        st.warning("⚠️ 필터 조건을 만족하는 자산이 없습니다. '최소 거래대금' 슬라이더를 낮춰보세요.")
else:
    st.info("표시할 데이터가 없습니다.")