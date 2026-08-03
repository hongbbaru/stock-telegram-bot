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
# 1. 기본 설정 및 텔레그램 토큰/챗ID
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
# 3. 메인 실행 스크립트
# =========================================================
def main():
    print("▶ 텔레그램 리포트 생성을 시작합니다...")
    
    # 간단 테스트용 안내 메시지 전송
    test_res = send_telegram_message("🚀 [시스템 알림] Stock Fear & Greed 리포트 데이터 수집을 시작합니다.")
    
    try:
        # 데이터 수집 예시 (SOXX, KOSPI)
        tickers = {'SOXX': 'SOXX', 'KOSPI': '^KS11'}
        data = yf.download(list(tickers.values()), start=START_DATE, end=END_DATE)['Close']
        
        # 데이터 수집 성공 보고
        msg = f"<b>📊 증시 마감 데이터 수집 완료</b>\n\n"
        for name, ticker in tickers.items():
            if ticker in data.columns and not data[ticker].dropna().empty:
                last_price = data[ticker].dropna().iloc[-1]
                msg += f"• {name}: {last_price:,.2f}\n"
        
        send_telegram_message(msg)
        print("▶ 성공적으로 텔레그램으로 리포트를 발송했습니다!")
        
    except Exception as e:
        error_msg = f"❌ 실행 중 오류가 발생했습니다:\n{str(e)}"
        print(error_msg)
        send_telegram_message(error_msg)
        sys.exit(1)

if __name__ == "__main__":
    main()
