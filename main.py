import io
import os
from datetime import datetime
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import requests
import yfinance as yf

# =========================================================
# 1. 기본 설정 및 텔레그램 토큰 자동 감지 (Secrets / Colab 겸용)
# =========================================================
FALLBACK_TOKEN = '8837799916:AAHmTA_2eSRb1WV3xtnmeE2mSyGr64ohNOg'
FALLBACK_CHAT_ID = '8611276891'

TELEGRAM_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN') or FALLBACK_TOKEN
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID') or FALLBACK_CHAT_ID

TELEGRAM_TOKEN = str(TELEGRAM_TOKEN).strip()
if TELEGRAM_TOKEN.startswith('bot'):
    TELEGRAM_TOKEN = TELEGRAM_TOKEN[3:]
CHAT_ID = str(CHAT_ID).strip()

START_DATE = '2019-01-01'
END_DATE = datetime.now().strftime('%Y-%m-%d')


# ---------------------------------------------------------
# 2. 공통 계산 및 리포트 생성 함수 (120일선 기준 수학적 정밀 계산)
# ---------------------------------------------------------
def get_single_report(ticker_type, max_dev=20.0):
    if ticker_type == 'SOXX':
        data = (
            yf.download(
                ['SOXX', '^VXN', 'TLT'],
                start=START_DATE,
                end=END_DATE,
                progress=False,
                auto_adjust=True,
            )['Close']
            .ffill()
            .bfill()
        )
        main_asset, vxn, sub_asset = (
            data['SOXX'],
            data['^VXN'],
            data['TLT'],
        )
        title_prefix = '[SOXX]'
        chart_color = '#1f77b4'
        sh_label = '안전자산'
    else:  # KOSPI
        data = (
            yf.download(
                ['^KS11', '^VXN', 'KRW=X'],
                start=START_DATE,
                end=END_DATE,
                progress=False,
                auto_adjust=True,
            )['Close']
            .ffill()
            .bfill()
        )
        main_asset, vxn, sub_asset = (
            data['^KS11'],
            data['^VXN'],
            data['KRW=X'],
        )
        title_prefix = '[KOSPI]'
        chart_color = '#d62728'
        sh_label = '환율수급'

    # [1] 모멘텀(M): 120일선 기준 이격도 정밀 계산 (120일선 밑 = 무조건 < 50점)
    sma120 = main_asset.rolling(120).mean()
    dev_pct = ((main_asset - sma120) / sma120) * 100
    
    # 0% (120일선) = 50점, +max_dev% = 100점, -max_dev% = 0점
    m_raw = 50 + (dev_pct / max_dev) * 50
    m = pd.Series(np.clip(m_raw, 0, 100), index=main_asset.index)

    # [2] 주가강도(S)
    s = np.clip(
        (main_asset - main_asset.rolling(252).min())
        / (main_asset.rolling(252).max() - main_asset.rolling(252).min())
        * 100,
        0,
        100,
    )

    # [3] 변동성안정(V)
    v_raw = vxn - vxn.rolling(50).mean()
    v = np.clip(
        100
        - (
            (v_raw - v_raw.rolling(504).min())
            / (v_raw.rolling(504).max() - v_raw.rolling(504).min())
            * 100
        ),
        0,
        100,
    )

    # [4] 수급/안전자산(SH)
    sh_raw = main_asset.pct_change(20) - sub_asset.pct_change(20)
    sh = np.clip(
        (sh_raw - sh_raw.rolling(504).min())
        / (sh_raw.rolling(504).max() - sh_raw.rolling(504).min())
        * 100,
        0,
        100,
    )

    # 종합 지수(FG) 계산
    df = pd.DataFrame(
        {'M': m, 'S': s, 'V': v, 'SH': sh, 'FG': (m + s + v + sh) / 4}
    ).dropna()
    last = df.iloc[-1]

    # 차트 생성
    plt.close('all')
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8))

    dev_label = f'±{int(max_dev)}%'
    ax1.plot(df.index, df['FG'], color=chart_color, linewidth=1.2)
    ax1.axhline(75, color='r', ls='--', alpha=0.5)
    ax1.axhline(25, color='g', ls='--', alpha=0.5)
    ax1.set_title(
        f'{title_prefix} 5-Year Fear & Greed Index (M: {dev_label})',
        fontweight='bold',
        fontsize=12,
    )
    ax1.set_ylim(0, 100)
    ax1.grid(True, alpha=0.3)

    df_1y = df.tail(252)
    ax2.plot(df_1y.index, df_1y['FG'], color=chart_color, linewidth=1.8)
    ax2.axhline(75, color='r', ls='--', alpha=0.5)
    ax2.axhline(25, color='g', ls='--', alpha=0.5)
    ax2.set_title(
        f'{title_prefix} 1-Year Fear & Greed Index (M: {dev_label})',
        fontweight='bold',
        fontsize=12,
    )
    ax2.set_ylim(0, 100)
    ax2.grid(True, alpha=0.3)

    plt.tight_layout()
    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=150, bbox_inches='tight')
    buf.seek(0)
    plt.close('all')

    return (
        round(last['FG'], 1),
        round(last['M'], 1),
        round(last['S'], 1),
        round(last['V'], 1),
        round(last['SH'], 1),
        buf,
        sh_label,
    )


# ---------------------------------------------------------
# 3. 상태 이모지 판정 함수 (화산 분출 적용)
# ---------------------------------------------------------
def get_state_emoji(score):
    if score >= 80:
        return '🌋 (극단적 탐욕)'
    elif score >= 60:
        return '🔥 (탐욕)'
    elif score >= 40:
        return '⚖️ (중립)'
    elif score >= 20:
        return '🧊 (공포)'
    else:
        return '❄️ (극단적 공포)'


# ---------------------------------------------------------
# 4. 텔레그램 전송 헬퍼 함수
# ---------------------------------------------------------
def send_telegram_msg_and_photo(text, img_buf, filename):
    url_msg = f'https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage'
    url_photo = f'https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto'

    res_msg = requests.post(
        url_msg, data={'chat_id': CHAT_ID, 'text': text}
    )
    res_photo = requests.post(
        url_photo,
        data={'chat_id': CHAT_ID},
        files={'photo': (filename, img_buf, 'image/png')},
    )

    if res_msg.status_code == 200 and res_photo.status_code == 200:
        print(f'  └  {filename} 발송 성공!')
    else:
        print(f'  └ ❌ 발송 에러 발생: {res_msg.text} / {res_photo.text}')


# ---------------------------------------------------------
# 5. 발송 메인 함수 (20% 세트 -> 10% 세트 순차 발송)
# ---------------------------------------------------------
def send_all_reports():
    print('🚀 텔레그램 공포탐욕지수 발송 프로세스 시작...')

    # =========================================================
    # [SECTION 1] 모멘텀 ±20% 버전 (중장기 관점)
    # =========================================================
    print('[1/2] ±20% 중장기 버전 생성 및 발송 중...')

    # SOXX (20%)
    fg, m, s, v, sh, img, sh_lbl = get_single_report('SOXX', max_dev=20.0)
    msg = (
        f'📊 [반도체 SOXX 공포지수 (±20% 중장기): {fg} / 100 {get_state_emoji(fg)}]\n'
        f'• 모멘텀(±20% 이격): {m}\n'
        f'• 주가강도: {s}\n'
        f'• 변동성안정: {v}\n'
        f'• {sh_lbl}: {sh}'
    )
    send_telegram_msg_and_photo(msg, img, 'soxx_20.png')

    # KOSPI (20%)
    fg, m, s, v, sh, img, sh_lbl = get_single_report('KOSPI', max_dev=20.0)
    msg = (
        f'📊 [코스피 KOSPI 공포지수 (±20% 중장기): {fg} / 100 {get_state_emoji(fg)}]\n'
        f'• 모멘텀(±20% 이격): {m}\n'
        f'• 주가강도: {s}\n'
        f'• 변동성안정: {v}\n'
        f'• {sh_lbl}: {sh}'
    )
    send_telegram_msg_and_photo(msg, img, 'kospi_20.png')

    # =========================================================
    # [SECTION 2] 모멘텀 ±10% 버전 (단기 민감 관점)
    # =========================================================
    print('[2/2] ±10% 단기 민감 버전 생성 및 발송 중...')

    # SOXX (10%)
    fg, m, s, v, sh, img, sh_lbl = get_single_report('SOXX', max_dev=10.0)
    msg = (
        f'📊 [반도체 SOXX 공포지수 (±10% 단기): {fg} / 100 {get_state_emoji(fg)}]\n'
        f'• 모멘텀(±10% 이격): {m}\n'
        f'• 주가강도: {s}\n'
        f'• 변동성안정: {v}\n'
        f'• {sh_lbl}: {sh}'
    )
    send_telegram_msg_and_photo(msg, img, 'soxx_10.png')

    # KOSPI (10%)
    fg, m, s, v, sh, img, sh_lbl = get_single_report('KOSPI', max_dev=10.0)
    msg = (
        f'📊 [코스피 KOSPI 공포지수 (±10% 단기): {fg} / 100 {get_state_emoji(fg)}]\n'
        f'• 모멘텀(±10% 이격): {m}\n'
        f'• 주가강도: {s}\n'
        f'• 변동성안정: {v}\n'
        f'• {sh_lbl}: {sh}'
    )
    send_telegram_msg_and_photo(msg, img, 'kospi_10.png')

    print('🎉 [완료] 총 4개 리포트(±20% 2개 + ±10% 2개) 텔레그램 전송 완료!')


if __name__ == '__main__':
    send_all_reports()
