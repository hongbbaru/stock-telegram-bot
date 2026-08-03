import io
import os
import sys
from datetime import datetime
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import requests
import yfinance as yf

# =========================================================
# 1. 기본 설정 및 텔레그램 토큰 / Chat ID
# =========================================================
FALLBACK_TOKEN = '8837799916:AAHmTA_2eSRb1WV3xtnmeE2mSyGr64ohNOg'
FALLBACK_CHAT_ID = '8611276891'

env_token = os.getenv('TELEGRAM_BOT_TOKEN', '').strip()
env_chat_id = os.getenv('TELEGRAM_CHAT_ID', '').strip()

TELEGRAM_TOKEN = env_token if env_token else FALLBACK_TOKEN
CHAT_ID = env_chat_id if env_chat_id else FALLBACK_CHAT_ID

TELEGRAM_TOKEN = str(TELEGRAM_TOKEN).strip()
if TELEGRAM_TOKEN.startswith('bot'):
    TELEGRAM_TOKEN = TELEGRAM_TOKEN[3:]
CHAT_ID = str(CHAT_ID).strip()

START_DATE = '2019-01-01'
END_DATE = datetime.now().strftime('%Y-%m-%d')

# =========================================================
# 2. 텔레그램 메세지 및 이미지 발송 함수
# =========================================================
def send_telegram_message(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {'chat_id': CHAT_ID, 'text': text, 'parse_mode': 'HTML'}
    res = requests.post(url, data=payload)
    if not res.ok:
        print(f"[ERROR] 텔레그램 메시지 전송 실패: {res.text}")
    return res

def send_telegram_photo(fig, caption=""):
    buf = io.BytesIO()
    fig.savefig(buf, format='png', bbox_inches='tight', dpi=150)
    buf.seek(0)
    plt.close(fig)
    
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto"
    files = {'photo': ('chart.png', buf, 'image/png')}
    data = {'chat_id': CHAT_ID, 'caption': caption, 'parse_mode': 'HTML'}
    res = requests.post(url, files=files, data=data)
    if not res.ok:
        print(f"[ERROR] 텔레그램 사진 전송 실패: {res.text}")
    return res

# =========================================================
# 3. 데이터 수집 및 공포탐욕지수 (모멘텀 10 & 20) 계산
# =========================================================
def get_stock_data(ticker_symbol):
    df = yf.download(ticker_symbol, start=START_DATE, end=END_DATE)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    return df

def calculate_fear_and_greed(df, momentum_window=125):
    close = df['Close']
    
    # 1. Price Momentum
    ma_mom = close.rolling(window=momentum_window).mean()
    p_momentum = (close - ma_mom) / ma_mom
    
    # 2. Stock Price Strength (RSI 14)
    delta = close.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    
    # 3. Stock Price Breadth (52주 위치)
    high52 = close.rolling(window=252).max()
    low52 = close.rolling(window=252).min()
    p_range = (close - low52) / (high52 - low52)
    
    # 4. Market Volatility (변동성 역산)
    returns = close.pct_change()
    volatility = returns.rolling(window=30).std()
    vol_min = volatility.rolling(window=252).min()
    vol_max = volatility.rolling(window=252).max()
    p_volatility = 1 - ((volatility - vol_min) / (vol_max - vol_min))
    
    # 공포탐욕 종합 지수 (0~100)
    fg_index = (p_momentum * 0.3 + (rsi/100) * 0.3 + p_range * 0.2 + p_volatility * 0.2) * 100
    fg_index = fg_index.clip(0, 100)
    
    df_result = pd.DataFrame({
        'Close': close,
        'Fear_Greed': fg_index,
        'RSI': rsi,
        'MA': ma_mom
    }).dropna()
    
    return df_result

def create_report_chart(df, name, version_label):
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8), sharex=True, gridspec_kw={'height_ratios': [2, 1]})
    
    # 상단: 주가 및 이동평균선 차트
    ax1.plot(df.index, df['Close'], label='Close Price', color='#1f77b4', linewidth=1.5)
    ax1.plot(df.index, df['MA'], label=f'MA ({version_label})', color='#ff7f0e', linestyle='--', linewidth=1)
    ax1.set_title(f'[{name}] {version_label} Price & Fear & Greed Index', fontsize=14, fontweight='bold')
    ax1.set_ylabel('Price')
    ax1.legend(loc='upper left')
    ax1.grid(True, alpha=0.3)
    
    # 하단: 공포탐욕 지수 차트
    ax2.plot(df.index, df['Fear_Greed'], color='#2ca02c', linewidth=1.2)
    ax2.axhline(80, color='red', linestyle=':', label='Extreme Greed (80)')
    ax2.axhline(20, color='blue', linestyle=':', label='Extreme Fear (20)')
    ax2.fill_between(df.index, df['Fear_Greed'], 50, where=(df['Fear_Greed'] >= 50), color='red', alpha=0.1)
    ax2.fill_between(df.index, df['Fear_Greed'], 50, where=(df['Fear_Greed'] < 50), color='blue', alpha=0.1)
    ax2.set_ylabel('Fear & Greed')
    ax2.set_ylim(0, 100)
    ax2.legend(loc='upper left')
    ax2.grid(True, alpha=0.3)
    
    plt.tight_layout()
    return fig

# =========================================================
# 4. 메인 실행 함수 (SOXX & KOSPI / 불&얼음 컨셉)
# =========================================================
def main():
    print("▶ SOXX & KOSPI Fear & Greed 리포트 생성을 시작합니다...")
    
    targets = {
        'SOXX (미국 반도체 ETF)': 'SOXX',
        'KOSPI (코스피 지수)': '^KS11'
    }
    
    versions = [
        {'label': '10일 모멘텀 버전', 'window': 10},
        {'label': '20일 모멘텀 버전', 'window': 20}
    ]
    
    for name, ticker in targets.items():
        try:
            print(f"--> {name} 데이터 수집 중...")
            raw_df = get_stock_data(ticker)
            if raw_df.empty:
                print(f"[WARN] {name} 데이터를 불러오지 못했습니다.")
                continue
                
            for ver in versions:
                df = calculate_fear_and_greed(raw_df, momentum_window=ver['window'])
                last_row = df.iloc[-1]
                last_date = df.index[-1].strftime('%Y-%m-%d')
                
                fg_val = last_row['Fear_Greed']
                
                # 불🔥 & 얼음❄️ 컨셉 상태 설정
                if fg_val >= 80:
                    status = "🔥🔥 극도의 탐욕 (Extreme Greed)"
                elif fg_val >= 60:
                    status = "🔥 탐욕 (Greed)"
                elif fg_val >= 40:
                    status = "⚖️ 중립 (Neutral)"
                elif fg_val >= 20:
                    status = "🧊 공포 (Fear)"
                else:
                    status = "❄️ 극도의 공포 (Extreme Fear)"
                    
                caption = (
                    f"<b>📊 {name} Daily Report [{ver['label']}]</b>\n"
                    f"<i>기준일자: {last_date}</i>\n\n"
                    f"• <b>종가:</b> {last_row['Close']:,.2f}\n"
                    f"• <b>공포&탐욕 지수:</b> <code>{fg_val:.1f} / 100</code>\n"
                    f"• <b>현재 상태:</b> {status}\n"
                    f"• <b>RSI (14):</b> {last_row['RSI']:.1f}"
                )
                
                fig = create_report_chart(df, name, ver['label'])
                send_telegram_photo(fig, caption=caption)
                print(f"  └ {name} [{ver['label']}] 발송 완료")
                
        except Exception as e:
            print(f"[{name}] 처리 중 오류 발생: {e}")
            
    print("▶ 모든 4개 리포트 발송 완료!")

if __name__ == "__main__":
    main()
