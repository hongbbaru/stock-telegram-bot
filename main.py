import os
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import requests
import yfinance as yf

# ---------------------------------------------------------
# 1. 환경 변수 (Telegram Token & Chat ID)
# ---------------------------------------------------------
BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

# ---------------------------------------------------------
# 2. 공통 지표 계산 함수
# ---------------------------------------------------------


def fetch_and_calculate(ticker):
    """주가 데이터를 받아오고 공포&탐욕 지수 하위 지표들을 계산합니다."""
    df = yf.download(ticker, period='2y')

    if isinstance(df.columns, pd.MultiIndex):
        df = df['Close']
    else:
        df = df[['Close']]

    df = pd.DataFrame(df)
    df.columns = ['Close']
    df = df.dropna()

    # [지표 1] 모멘텀 (125일 이평선 대비 ±20% 괴리율 기반 0~100점)
    df['SMA125'] = df['Close'].rolling(window=125).mean()
    df['Dev_pct'] = ((df['Close'] - df['SMA125']) / df['SMA125']) * 100
    max_dev = 20.0  # ±20% 범위
    df['Momentum'] = (
        (df['Dev_pct'] - (-max_dev)) / (max_dev - (-max_dev))
    ) * 100
    df['Momentum'] = np.clip(df['Momentum'], 0, 100)

    # [지표 2] 변동성 (20일 변동성의 1년(252일) 상대 위치)
    df['Log_Ret'] = np.log(df['Close'] / df['Close'].shift(1))
    df['Vol20'] = df['Log_Ret'].rolling(window=20).std() * np.sqrt(252)
    vol_min = df['Vol20'].rolling(window=252).min()
    vol_max = df['Vol20'].rolling(window=252).max()
    # 변동성은 높을수록 공포(낮은 점수)이므로 역산
    df['Volatility'] = 100 - (
        ((df['Vol20'] - vol_min) / (vol_max - vol_min)) * 100
    )
    df['Volatility'] = np.clip(df['Volatility'], 0, 100)

    # [지표 3] RSI (14일 상대강도지수)
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))
    df['RSI'] = np.clip(df['RSI'], 0, 100)

    # [종합] 공포&탐욕 종합 지수 (3개 지표 평균)
    df['Fear_Greed_Index'] = (
        df['Momentum'] + df['Volatility'] + df['RSI']
    ) / 3.0

    return df.dropna()


# ---------------------------------------------------------
# 3. 차트 생성 함수 (5년 전체 + 1년 확대)
# ---------------------------------------------------------


def create_chart(df, title_name, filename):
    """지수 추이 차트를 생성하여 이미지 파일로 저장합니다."""
    fig, (ax1, ax2) = plt.subplots(
        2, 1, figsize=(10, 8), gridspec_kw={'height_ratios': [2, 1]}
    )

    # 상단: 주가 추이
    ax1.plot(df.index, df['Close'], label='Close Price', color='#1f77b4')
    ax1.plot(
        df.index,
        df['SMA125'],
        label='125-day SMA',
        color='#ff7f0e',
        linestyle='--',
    )
    ax1.set_title(f'{title_name} Price & 125 SMA', fontsize=12, fontweight='bold')
    ax1.set_ylabel('Price')
    ax1.legend(loc='upper left')
    ax1.grid(True, alpha=0.3)

    # 하단: 공포 탐욕 지수
    ax2.plot(
        df.index,
        df['Fear_Greed_Index'],
        label='Fear & Greed Index',
        color='#2ca02c',
    )
    ax2.axhline(80, color='red', linestyle=':', label='Extreme Greed (80)')
    ax2.axhline(20, color='blue', linestyle=':', label='Extreme Fear (20)')
    ax2.axhline(50, color='gray', linestyle='-', alpha=0.5)
    ax2.set_title(f'{title_name} Fear & Greed Index', fontsize=12)
    ax2.set_ylabel('Index (0-100)')
    ax2.set_ylim(0, 100)
    ax2.legend(loc='upper left')
    ax2.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(filename, dpi=150)
    plt.close()


# ---------------------------------------------------------
# 4. 텔레그램 메시지 & 이미지 발송
# ---------------------------------------------------------


def send_telegram_photo(caption, photo_path):
    """텔레그램 봇으로 이미지와 캡션을 발송합니다."""
    url = f'https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto'
    with open(photo_path, 'rb') as photo:
        payload = {'chat_id': CHAT_ID, 'caption': caption, 'parse_mode': 'HTML'}
        files = {'photo': photo}
        requests.post(url, data=payload, files=files)


# ---------------------------------------------------------
# 5. 메인 실행부
# ---------------------------------------------------------


def main():
    targets = [('SOXX', 'SOXX (Semiconductor ETF)'), ('^KS11', 'KOSPI')]

    for ticker, name in targets:
        try:
            df = fetch_and_calculate(ticker)
            latest = df.iloc[-1]
            date_str = df.index[-1].strftime('%Y-%m-%d')

            # 지수 단계 판단
            score = latest['Fear_Greed_Index']
            if score >= 80:
                state = '🔥 극단적 탐욕 (Extreme Greed)'
            elif score >= 60:
                state = '📈 탐욕 (Greed)'
            elif score >= 40:
                state = '⚖️ 중립 (Neutral)'
            elif score >= 20:
                state = '📉 공포 (Fear)'
            else:
                state = '🧊 극단적 공포 (Extreme Fear)'

            # 텔레그램 캡션 텍스트 구성
            caption = f"""
<b>📊 {name} Daily Fear & Greed Report</b>
📅 기준일자: {date_str}

<b>종합 지수: {score:.1f} / 100 ({state})</b>

<b>[세부 지표 현황]</b>
• 현재가: {latest['Close']:,.2f}
• 125일 이평선: {latest['SMA125']:,.2f}
• 모멘텀(±20% 이격): <b>{latest['Momentum']:.1f}</b> / 100
• 변동성 지수: <b>{latest['Volatility']:.1f}</b> / 100
• RSI (14일): <b>{latest['RSI']:.1f}</b> / 100
"""

            # 차트 이미지 생성
            filename = f'{ticker}_report.png'
            create_chart(df, name, filename)

            # 발송
            send_telegram_photo(caption, filename)
            print(f'{name} 리포트 발송 성공!')

            # 임시 파일 삭제
            if os.path.exists(filename):
                os.remove(filename)

        except Exception as e:
            print(f'{name} 처리 중 에러 발생: {e}')


if __name__ == '__main__':
    main()
