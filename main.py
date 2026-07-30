import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import requests
import io

# ====================================================
# 🔑 사용자 토큰 및 챗방 아이디
# ====================================================
TELEGRAM_TOKEN = '8837799916:AAHmTA_2eSRb1WV3xtnmeE2mSyGr64ohNOg'
CHAT_ID = '8611276891'

def get_soxx_report():
    data = yf.download(['SOXX', '^VXN', 'TLT'], period='6y', progress=False, auto_adjust=True)['Close'].ffill().bfill()
    soxx, vxn, tlt = data['SOXX'], data['^VXN'], data['TLT']
    
    m = np.clip(((soxx - soxx.rolling(125).mean())/soxx.rolling(125).mean() - (-0.20))/0.40 * 100, 0, 100)
    s = np.clip((soxx - soxx.rolling(252).min())/(soxx.rolling(252).max() - soxx.rolling(252).min()) * 100, 0, 100)
    v = np.clip((1 - (vxn - vxn.rolling(50).mean() - (-15))/30) * 100, 0, 100)
    sh = np.clip(((soxx.pct_change(20) - tlt.pct_change(20)) - (-0.12))/0.24 * 100, 0, 100)
    
    df = pd.DataFrame({'M': m, 'S': s, 'V': v, 'SH': sh, 'FG': (m+s+v+sh)/4}).dropna()
    last = df.iloc[-1]
    
    plt.figure(figsize=(10, 4))
    plt.plot(df.tail(252).index, df.tail(252)['FG'], color='#1f77b4', linewidth=1.8)
    plt.axhline(75, color='r', ls='--', alpha=0.5); plt.axhline(25, color='g', ls='--', alpha=0.5)
    plt.title('Semiconductor (SOXX) Fear & Greed Index (1 Year)', fontweight='bold')
    plt.ylim(0, 100); plt.grid(True, alpha=0.3); plt.tight_layout()
    
    buf = io.BytesIO(); plt.savefig(buf, format='png', dpi=120); buf.seek(0); plt.close()
    return round(last['FG'], 1), round(last['M'], 1), round(last['S'], 1), round(last['V'], 1), round(last['SH'], 1), buf

def get_kospi_report():
    data = yf.download(['^KS11', '^VXN', 'KRW=X'], period='6y', progress=False, auto_adjust=True)['Close'].ffill().bfill()
    kospi, vxn, usdkrw = data['^KS11'], data['^VXN'], data['KRW=X']
    
    m = np.clip(((kospi - kospi.rolling(125).mean())/kospi.rolling(125).mean() - (-0.15))/0.30 * 100, 0, 100)
    s = np.clip((kospi - kospi.rolling(252).min())/(kospi.rolling(252).max() - kospi.rolling(252).min()) * 100, 0, 100)
    v = np.clip((1 - (vxn - vxn.rolling(50).mean() - (-15))/30) * 100, 0, 100)
    sh = np.clip(((kospi.pct_change(20) - usdkrw.pct_change(20)) - (-0.08))/0.16 * 100, 0, 100)
    
    df = pd.DataFrame({'M': m, 'S': s, 'V': v, 'SH': sh, 'FG': (m+s+v+sh)/4}).dropna()
    last = df.iloc[-1]
    
    plt.figure(figsize=(10, 4))
    plt.plot(df.tail(252).index, df.tail(252)['FG'], color='#d62728', linewidth=1.8)
    plt.axhline(75, color='r', ls='--', alpha=0.5); plt.axhline(25, color='g', ls='--', alpha=0.5)
    plt.title('KOSPI Fear & Greed Index (1 Year)', fontweight='bold')
    plt.ylim(0, 100); plt.grid(True, alpha=0.3); plt.tight_layout()
    
    buf = io.BytesIO(); plt.savefig(buf, format='png', dpi=120); buf.seek(0); plt.close()
    return round(last['FG'], 1), round(last['M'], 1), round(last['S'], 1), round(last['V'], 1), round(last['SH'], 1), buf

def send_all_reports():
    print("텔레그램 발송 중...")
    
    # 1. SOXX 발송
    s_fg, s_m, s_s, s_v, s_sh, s_img = get_soxx_report()
    msg_soxx = f"📊 [반도체 SOXX 공포지수: {s_fg} / 100]\n• 모멘텀: {s_m}\n• 주가강도: {s_s}\n• 변동성: {s_v}\n• 안전자산: {s_sh}"
    requests.post("https://api.telegram.org/bot8837799916:AAHmTA_2eSRb1WV3xtnmeE2mSyGr64ohNOg/sendMessage", data={'chat_id': '8611276891', 'text': msg_soxx})
    requests.post("https://api.telegram.org/bot8837799916:AAHmTA_2eSRb1WV3xtnmeE2mSyGr64ohNOg/sendPhoto", data={'chat_id': '8611276891'}, files={'photo': s_img})
    
    # 2. KOSPI 발송
    k_fg, k_m, k_s, k_v, k_sh, k_img = get_kospi_report()
    msg_kospi = f"📊 [코스피 KOSPI 공포지수: {k_fg} / 100]\n• 모멘텀: {k_m}\n• 주가강도: {k_s}\n• 변동성: {k_v}\n• 환율수급: {k_sh}"
    requests.post("https://api.telegram.org/bot8837799916:AAHmTA_2eSRb1WV3xtnmeE2mSyGr64ohNOg/sendMessage", data={'chat_id': '8611276891', 'text': msg_kospi})
    requests.post("https://api.telegram.org/bot8837799916:AAHmTA_2eSRb1WV3xtnmeE2mSyGr64ohNOg/sendPhoto", data={'chat_id': '8611276891'}, files={'photo': k_img})
    
    print("🎉 전송 완료! 텔레그램 앱을 확인하세요.")

send_all_reports()
