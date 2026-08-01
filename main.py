import io
import os
from datetime import datetime
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import requests
import yfinance as yf

# =========================================================
# 1. 기본 설정 및 텔레그램 토큰 자동 감지 (Secrets / Colab / Scheduled 전용)
# =========================================================
FALLBACK_TOKEN = '8837799916:AAHmTA_2eSRb1WV3xtnmeE2mSyGr64ohNOg'
FALLBACK_CHAT_ID = '8611276891'

# Secrets 환경변수가 비어있거나 무효할 경우 무조건 직접 입력값 사용하도록 보장
env_token = os.getenv('TELEGRAM_BOT_TOKEN', '').strip()
env_chat_id = os.getenv('TELEGRAM_CHAT_ID', '').strip()

TELEGRAM_TOKEN = env_token if env_token else FALLBACK_TOKEN
CHAT_ID = env_chat_id if env_chat_id else FALLBACK_CHAT_ID

# Token / Chat ID 앞뒤 공백 및 'bot' 중복 제거
TELEGRAM_TOKEN = str(TELEGRAM_TOKEN).strip()
if TELEGRAM_TOKEN.startswith('bot'):
    TELEGRAM_TOKEN = TELEGRAM_TOKEN[3:]
CHAT_ID = str(CHAT_ID).strip()

START_DATE = '2019-01-01'
END_DATE = datetime.now().strftime('%Y-%m-%d')
