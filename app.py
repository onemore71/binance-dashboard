import streamlit as st
import pandas as pd
import requests
import plotly.graph_objects as go
import time

st.set_page_config(layout="wide", page_title="Altcoin Scanner")
st.title("🚀 급등 주도 알트코인 실시간 스캐너")
st.caption("메이저 제외 / 거래대금 동반 / 코인게코 1,250개 자산 추적 대시보드")

@st.cache_data(ttl=60)  # 범위를 넓혔으므로 부하를 줄이기 위해 캐시 시간을 60초로 늘립니다.
def get_coingecko_market_data():
    crypto_data = []
    
    # 250개씩 총 5페이지를 요청하여 상위 1,250위까지 수집합니다.
    for page in range(1, 6):
        url = "https://api.coingecko.com/api/v3/coins/markets"
        params = {
            "vs_currency": "usd",
            "order": "market_cap_desc",
            "per_page": 250, 
            "page": page,
            "sparkline": "true",
            "price_change_percentage": "24h"
        }
        
        try:
            response = requests.get(url, params=params, timeout=5)
            if response.status_code == 200:
                data = response.json()
                if not data:
                    break
                for coin in data:
                    symbol = coin['symbol'].upper()
                    name = coin['name']
                    
                    price_change = coin.get('price_change_percentage_24h')
                    volume = coin.get('total_volume')
                    
                    if price_change is None or volume is None:
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
            else:
                # API 호출 한도 초과 등의 이유 대응
                st.warning(f"⚠️ 코인게코 API {page}페이지 로드 지연 (Status: {response.status_code})")
        except Exception as e:
            pass
            
        # 연속 호출 시 디노스(DDoS) 방지를 위한 미세한 시간 차 둠
        time.sleep(0.2)
        
    return pd.DataFrame(crypto_data)

try:
    df = get_coingecko_market_data()
except Exception as e:
    st.error(f"❌ 데이터 로드 실패: {e}")
    df = pd.DataFrame()

# ⚙️ 사이드바 필터 및 정렬 설정
st.sidebar.header("🔍 알트코인 필터링 조건")
exclude_majors = st.sidebar.checkbox("메이저 & 스테이블 코인 제외", value=True)

# 0으로 완전 완화할 수 있도록 최소 범위를 0으로 지정
min_volume_million = st.sidebar.slider("최소 24시간 거래대금 (백만 달러)", min_value=0.0, max_value=500.0, value=0.0, step=0.5)

st.sidebar.markdown("---")
sort_by = st.sidebar.selectbox("정렬 기준", ["24h 변동률(%)", "24h 거래대금(백만$)"], index=0)
order = st.sidebar.radio("정렬 순서", ["내림차순 (높은 순)", "오름차순 (낮은 순)"])
ascending = True if order == "오름차순 (낮은 순)" else False

st.sidebar.markdown("---")
refresh_rate = st.sidebar.selectbox("🔄 자동 새로고침 주기", ["끄기", "30초", "1분", "2분"], index=0)


if not df.empty:
    processed_df = df.copy()
    
    if exclude_majors:
        majors_and_stables = ['BTCUSDT', 'ETHUSDT', 'USDTUSDT', 'USDCUSDT', 'DAIUSDT', 'FDUSDUSDT', 'STETHUSDT', 'WETHUSDT', 'WBTCUSDT']
        processed_df = processed_df[~processed_df['심볼'].isin(majors_and_stables)]
        processed_df = processed_df[~processed_df['이름'].str.contains('USD|Wrapped|Tether', case=False)]

    processed_df = processed_df[processed_df['24h 거래대금(백만$)'] >= min_volume_million]
    
    # 상위 노출 개수를 100개로 확장하여 소형주 식별 용이하게 조절
    df_sorted = processed_df.sort_values(by=sort_by, ascending=ascending).head(100).reset_index(drop=True)
    
    st.subheader(f"🔥 조건 만족 주도 자산 TOP {len(df_sorted)} ({sort_by} 높은 순)")
    st.caption("💡 테이블에서 원하는 알트코인 행을 클릭하면 우측 7일 가격 차트가 연동됩니다.")
    
    if not df_sorted.empty:
        col1, col2 = st.columns([12, 10])
        
        with col1:
            display_df = df_sorted.drop(columns=['sparkline'])
            
            event = st.dataframe(
                display_df.style.format({
                    '현재가($)': '{:,.4f}',
                    '24h 변동률(%)': '{:+.2f}%',
                    '24h 거래대금(백만$)': '${:,.2f}M'
                }),
                use_container_width=True, 
                height=600,
                selection_mode="single-row", 
                on_select="rerun"
            )
            
        with col2:
            selected_row_index = 0
            if event and event.get("selection", {}).get("rows"):
                selected_row_index = event["selection"]["rows"][0]
            
            selected_row = df_sorted.iloc[selected_row_index]
            target_symbol = selected_row['심볼']
            sparkline_prices = selected_row['sparkline']
            
            st.markdown(f"### 📈 {target_symbol} 실시간 트렌드 (최근 7일)")
            
            if sparkline_prices and len(sparkline_prices) > 1:
                fig = go.Figure()
                is_positive = sparkline_prices[-1] >= sparkline_prices[0]
                line_color = '#10B981' if is_positive else '#EF4444'
                fill_color = 'rgba(16, 185, 129, 0.08)' if is_positive else 'rgba(239, 68, 68, 0.08)'
                
                fig.add_trace(go.Scatter(
                    y=sparkline_prices, mode='lines',
                    line=dict(color=line_color, width=3),
                    fill='tozeroy', fillcolor=fill_color, name="Price"
                ))
                
                fig.update_layout(
                    xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                    yaxis=dict(showgrid=True, zeroline=False, showticklabels=True, gridcolor='rgba(128,128,128,0.15)'),
                    margin=dict(l=25, r=25, t=10, b=10), height=380,
                    paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)'
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.warning("⚠️ 차트 데이터를 불러올 수 없습니다.")
                
            st.metric(
                label=f"{selected_row['이름']} 현재 가격", 
                value=f"${selected_row['현재가($)']:,.4f}", 
                delta=f"{selected_row['24h 변ble률(%)']:+.2f}%" if '24h 변ble률(%)' in selected_row else f"{selected_row['24h 변동률(%)']:+.2f}%"
            )

        if refresh_rate != "끄기":
            sec = 30 if refresh_rate == "30초" else (60 if refresh_rate == "1분" else 120)
            time.sleep(sec)
            st.rerun()
            
    else:
        st.warning("⚠️ 필터 조건을 만족하는 자산이 없습니다. '최소 거래대금' 슬라이더를 낮춰보세요.")
else:
    st.info("표시할 데이터가 없습니다.")
