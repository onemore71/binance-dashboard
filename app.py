import streamlit as st
import pandas as pd
import requests
import plotly.graph_objects as go
from datetime import datetime

st.set_page_config(layout="wide", page_title="Altcoin Scanner with Candlestick")
st.title("🚀 급등 주도 알트코인 실시간 스캐너 (캔들차트 연동)")
st.caption("메이저 제외 / 거래대금 동반 / Bybit 1시간 봉 캔들차트 제공")

@st.cache_data(ttl=30)  # 30초마다 갱신
def get_coingecko_market_data():
    url = "https://api.coingecko.com/api/v3/coins/markets"
    params = {
        "vs_currency": "usd",
        "order": "market_cap_desc",
        "per_page": 250, 
        "page": 1,
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
            '24h 거래대금(백만$)': volume_in_million
        })
        
    return pd.DataFrame(crypto_data)

def get_bybit_candles(symbol, interval='60', limit=24):
    url = f"https://api.bybit.com/v5/market/kline?category=linear&symbol={symbol}&interval={interval}&limit={limit}"
    try:
        res = requests.get(url).json()
        if res.get('retCode') == 0 and res.get('result', {}).get('list'):
            raw_candles = res['result']['list']
            df_candles = pd.DataFrame(raw_candles, columns=['time', 'open', 'high', 'low', 'close', 'volume', 'turnover'])
            df_candles = df_candles.iloc[::-1].reset_index(drop=True)
            
            for col in ['open', 'high', 'low', 'close', 'volume']:
                df_candles[col] = df_candles[col].astype(float)
                
            df_candles['time'] = pd.to_datetime(df_candles['time'].astype(float), unit='ms')
            return df_candles
    except Exception:
        pass
    return pd.DataFrame()

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

    # [정렬 및 상위 개수 추출]
    df_sorted = processed_df.sort_values(by=sort_by, ascending=ascending).head(30).reset_index(drop=True)
    
    st.subheader(f"🔥 조건 만족 주도 자산 TOP {len(df_sorted)} ({sort_by} 높은 순)")
    st.caption("💡 테이블의 종목을 클릭하면 우측에 Bybit 실시간 1시간 봉 캔들차트가 연동됩니다.")
    
    if not df_sorted.empty:
        col1, col2 = st.columns([12, 10])
        
        with col1:
            display_df = df_sorted.drop(columns=['sparkline']) if 'sparkline' in df_sorted.columns else df_sorted.copy()
            
            # [수정 완료] selection_mode를 하이픈 표기법 "single-row"로 변경
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
            # 테이블 선택 감지
            selected_row_index = 0
            if event and event.get("selection", {}).get("rows"):
                selected_row_index = event["selection"]["rows"][0]
            
            selected_row = df_sorted.iloc[selected_row_index]
            target_symbol = selected_row['심볼']
            
            st.markdown(f"### 📊 {target_symbol} 실시간 1시간 봉 (최근 24시간)")
            
            candle_df = get_bybit_candles(target_symbol, interval='60', limit=24)
            
            if not candle_df.empty:
                from plotly.subplots import make_subplots
                
                fig = make_subplots(rows=2, cols=1, shared_xaxes=True, 
                                    vertical_spacing=0.1, 
                                    row_width=[0.3, 0.7])
                
                fig.add_trace(go.Candlestick(
                    x=candle_df['time'],
                    open=candle_df['open'], high=candle_df['high'],
                    low=candle_df['low'], close=candle_df['close'],
                    name="가격",
                    increasing_line_color='#FF4D4D', decreasing_line_color='#1261C4',
                    increasing_fillcolor='#FF4D4D', decreasing_fillcolor='#1261C4'
                ), row=1, col=1)
                
                colors = ['#FF4D4D' if c >= o else '#1261C4' for o, c in zip(candle_df['open'], candle_df['close'])]
                fig.add_trace(go.Bar(
                    x=candle_df['time'],
                    y=candle_df['volume'],
                    name="거래량",
                    marker_color=colors,
                    opacity=0.8
                ), row=2, col=1)
                
                fig.update_layout(
                    xaxis_rangeslider_visible=False,
                    margin=dict(l=20, r=20, t=10, b=10),
                    height=400,
                    showlegend=False,
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)'
                )
                
                fig.update_xaxes(showgrid=True, gridcolor='rgba(128,128,128,0.15)')
                fig.update_yaxes(showgrid=True, gridcolor='rgba(128,128,128,0.15)')
                
                st.plotly_chart(fig, use_container_width=True)
                
                st.metric(
                    label=f"{selected_row['이름']} 실시간 시세 (CoinGecko 기준)", 
                    value=f"${selected_row['현재가($)']:,.4f}", 
                    delta=f"{selected_row['24h 변동률(%)']:+.2f}%"
                )
            else:
                st.warning(f"⚠️ {target_symbol} 종목은 Bybit 무기한 선물 마켓에 상장되어 있지 않거나 데이터를 가져올 수 없습니다.")
    else:
        st.warning("⚠️ 필터 조건을 만족하는 자산이 없습니다. '최소 거래대금' 슬라이더를 낮춰보세요.")
else:
    st.info("표시할 데이터가 없습니다.")