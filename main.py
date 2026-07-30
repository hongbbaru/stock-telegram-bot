import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import requests
import io
from datetime import datetime

# ====================================================
# 🔑 사용자 토큰 및 챗방 아이디
# ====================================================
TELEGRAM_TOKEN = '8837799916:AAHmTA_2eSRb1WV3xtnmeE2mSyGr64ohNOg'
CHAT_ID = '8611276891'

# 날짜 직접 지정 (yfinance 안정화)
START_DATE = '2019-01-01'
END_DATE = datetime.now().strftime('%Y-%m-%d')

def get_soxx_report():
    data = yf.download(['SOXX', '^VXN', 'TLT'], start=START_DATE, end=END_DATE, progress=False, auto_adjust=True)['Close'].ffill().bfill()
    soxx, vxn, tlt = data['SOXX'], data['^VXN'], data['TLT']
    
    # 2년 Rolling Min-Max 상대적 지표 계산
    m_raw = (soxx - soxx.rolling(125).mean()) / soxx.rolling(125).mean()
    m = np.clip((m_raw - m_raw.rolling(504).min()) / (m_raw.rolling(504).max() - m_raw.rolling(504).min()) * 100, 0, 100)
    
    s = np.clip((soxx - soxx.rolling(252).min()) / (soxx.rolling(252).max() - soxx.rolling(252).min()) * 100, 0, 100)
    
    v_raw = vxn - vxn.rolling(50).mean()
    v = np.clip(100 - ((v_raw - v_raw.rolling(504).min()) / (v_raw.rolling(504).max() - v_raw.rolling(504).min()) * 100), 0, 100)
    
    sh_raw = soxx.pct_change(20) - tlt.pct_change(20)
    sh = np.clip((sh_raw - sh_raw.rolling(504).min()) / (sh_raw.rolling(504).max() - sh_raw.rolling(504).min()) * 100, 0, 100)
    
    df = pd.DataFrame({'M': m, 'S': s, 'V': v, 'SH': sh, 'FG': (m+s+v+sh)/4}).dropna()
    last = df.iloc[-1]
    
    plt.close('all')
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8))
    
    # 상단: 5년 장기 차트
    ax1.plot(df.index, df['FG'], color='#1f77b4', linewidth=1.2)
    ax1.axhline(75, color='r', ls='--', alpha=0.5)
    ax1.axhline(25, color='g', ls='--', alpha=0.5)
    ax1.set_title('[SOXX] 5-Year Long-Term Fear & Greed Index', fontweight='bold', fontsize=12)
    ax1.set_ylim(0, 100)
    ax1.grid(True, alpha=0.3)
    
    # 하단: 1년 단기 차트
    df_1y = df.tail(252)
    ax2.plot(df_1y.index, df_1y['FG'], color='#1f77b4', linewidth=1.8)
    ax2.axhline(75, color='r', ls='--', alpha=0.5)
    ax2.axhline(25, color='g', ls='--', alpha=0.5)
    ax2.set_title('[SOXX] 1-Year Recent Fear & Greed Index', fontweight='bold', fontsize=12)
    ax2.set_ylim(0, 100)
    ax2.grid(True, alpha=0.3)
    
    plt.tight_layout()
    
    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=150, bbox_inches='tight')
    buf.seek(0)
    plt.close('all')
    
    return round(last['FG'], 1), round(last['M'], 1), round(last['S'], 1), round(last['V'], 1), round(last['SH'], 1), buf

def get_kospi_report():
    data = yf.download(['^KS11', '^VXN', 'KRW=X'], start=START_DATE, end=END_DATE, progress=False, auto_adjust=True)['Close'].ffill().bfill()
    kospi, vxn, usdkrw = data['^KS11'], data['^VXN'], data['KRW=X']
    
    m_raw = (kospi - kospi.rolling(125).mean()) / kospi.rolling(125).mean()
    m = np.clip((m_raw - m_raw.rolling(504).min()) / (m_raw.rolling(504).max() - m_raw.rolling(504).min()) * 100, 0, 100)
    
    s = np.clip((kospi - kospi.rolling(252).min()) / (kospi.rolling(252).max() - kospi.rolling(252).min()) * 100, 0, 100)
    
    v_raw = vxn - vxn.rolling(50).mean()
    v = np.clip(100 - ((v_raw - v_raw.rolling(504).min()) / (v_raw.rolling(504).max() - v_raw.rolling(504).min()) * 100), 0, 100)
    
    sh_raw = kospi.pct_change(20) - usdkrw.pct_change(20)
    sh = np.clip((sh_raw - sh_raw.rolling(504).min()) / (sh_raw.rolling(504).max() - sh_raw.rolling(504).min()) * 100, 0, 100)
    
    df = pd.DataFrame({'M': m, 'S': s, 'V': v, 'SH': sh, 'FG': (m+s+v+sh)/4}).dropna()
    last = df.iloc[-1]
    
    plt.close('all')
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8))
    
    # 상단: 5년 장기 차트
    ax1.plot(df.index, df['FG'], color='#d62728', linewidth=1.2)
    ax1.axhline(75, color='r', ls='--', alpha=0.5)
    ax1.axhline(25, color='g', ls='--', alpha=0.5)
    ax1.set_title('[KOSPI] 5-Year Long-Term Fear & Greed Index', fontweight='bold', fontsize=12)
    ax1.set_ylim(0, 100)
    ax1.grid(True, alpha=0.3)
    
    # 하단: 1년 단기 차트
    df_1y = df.tail(252)
    ax2.plot(df_1y.index, df_1y['FG'], color='#d62728', linewidth=1.8)
    ax2.axhline(75, color='r', ls='--', alpha=0.5)
    ax2.axhline(25, color='g', ls='--', alpha=0.5)
    ax2.set_title('[KOSPI] 1-Year Recent Fear & Greed Index', fontweight='bold', fontsize=12)
    ax2.set_ylim(0, 100)
    ax2.grid(True, alpha=0.3)
    
    plt.tight_layout()
    
    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=150, bbox_inches='tight')
    buf.seek(0)
    plt.close('all')
    
    return round(last['FG'], 1), round(last['M'], 1), round(last['S'], 1), round(last['V'], 1), round(last['SH'], 1), buf

def send_all_reports():
    print("텔레그램 발송 시작...")
    
    # 1. SOXX 발송
    s_fg, s_m, s_s, s_v, s_sh, s_img = get_soxx_report()
    msg_soxx = f"📊 [반도체 SOXX 공포지수: {s_fg} / 100]\n• 모멘텀(상대): {s_m}\n• 주가강도: {s_s}\n• 변동성안정: {s_v}\n• 안전자산: {s_sh}"
    requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", data={'chat_id': CHAT_ID, 'text': msg_soxx})
    requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto", data={'chat_id': CHAT_ID}, files={'photo': ('soxx.png', s_img, 'image/png')})
    
    # 2. KOSPI 발송
    k_fg, k_m, k_s, k_v, k_sh, k_img = get_kospi_report()
    msg_kospi = f"📊 [코스피 KOSPI 공포지수: {k_fg} / 100]\n• 모멘텀(상대): {k_m}\n• 주가강도: {k_s}\n• 변동성안정: {k_v}\n• 환율수급: {k_sh}"
    requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", data={'chat_id': CHAT_ID, 'text': msg_kospi})
    requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto", data={'chat_id': CHAT_ID}, files={'photo': ('kospi.png', k_img, 'image/png')})
    
    print("🎉 NEW 5년+1년 차트 발송 성공!")

send_all_reports()
