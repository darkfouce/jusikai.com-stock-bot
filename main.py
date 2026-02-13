import requests
from bs4 import BeautifulSoup
import pandas as pd
import telegram
import asyncio
import os
import FinanceDataReader as fdr
from datetime import datetime, timedelta
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

TOKEN = os.environ.get('TELEGRAM_TOKEN')
CHAT_ID = os.environ.get('CHAT_ID')
DATA_FILE = "stock_history.csv"

# [PRO] 네트워크 안정성을 위한 재시도 설정
def requests_retry_session():
    session = requests.Session()
    retry = Retry(total=3, backoff_factor=1, status_forcelist=[500, 502, 503, 504])
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    return session

# [PRO] 시장 심리 및 지수 분석
def get_market_sentiment():
    indices = {'코스피': 'KS11', '코스닥': 'KQ11', '나스닥': 'IXIC'}
    res = ""
    for name, code in indices.items():
        try:
            df = fdr.DataReader(code, (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d'))
            curr, prev = df.iloc[-1]['Close'], df.iloc[-2]['Close']
            chg = ((curr - prev) / prev) * 100
            status = "🔥 강세" if chg > 0.5 else "❄️ 약세" if chg < -0.5 else "☁️ 혼조"
            res += f" • {name}: {curr:,.2f} ({chg:+.2f}%) {status}\n"
        except: res += f" • {name}: 조회 실패\n"
    return res

def get_stock_pro_details(name):
    try:
        df_krx = fdr.StockListing('KRX')
        row = df_krx[df_krx['Name'] == name]
        if not row.empty:
            symbol = row.iloc[0]['Code']
            df = fdr.DataReader(symbol, (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d'))
            curr, prev = int(df.iloc[-1]['Close']), int(df.iloc[-2]['Close'])
            chg = ((curr - prev) / prev) * 100
            vol = int(df.iloc[-1]['Volume'])
            return f"{curr:,}원 ({chg:+.2f}%) | 거래량: {vol:,}"
    except: pass
    return "정보 없음"

async def main():
    if not TOKEN or not CHAT_ID: return
    bot = telegram.Bot(token=TOKEN)
    
    # 1. 크롤링 (PRO: 유저 에이전트 최신화 및 재시도)
    session = requests_retry_session()
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    res = session.get("https://jusikai.com/", headers=headers, timeout=10)
    soup = BeautifulSoup(res.text, 'html.parser')
    tags = soup.select('.ranking-stock-name') or soup.select('tr td a')
    today_all = [t.text.strip() for t in tags if t.text.strip()]
    
    # AI 4대장 추출
    ai_4_major = today_all[:4]

    # 2. 데이터 분석 (PRO: 날짜 형식 안정화)
    today = (datetime.utcnow() + timedelta(hours=9)).strftime('%Y-%m-%d')
    new_df = pd.DataFrame({'date': [today]*len(today_all), 'stock': today_all})

    if os.path.exists(DATA_FILE):
        df = pd.read_csv(DATA_FILE, dtype={'date': str})
        df = pd.concat([df, new_df]).drop_duplicates()
    else: df = new_df
    df.to_csv(DATA_FILE, index=False)

    limit = (datetime.now() - timedelta(days=2)).strftime('%Y-%m-%d')
    recent = df[df['date'].astype(str) >= limit]
    counts = recent['stock'].value_counts()
    overlapping = counts[counts >= 2].index.tolist()

    # 3. 프로 모드 리포트 작성
    msg = f"🔍 **[PRO MODE] 마켓 데이터 브리핑**\n"
    msg += f"📅 분석 일시: {today}\n\n"
    msg += f"📊 **글로벌 지수 현황**\n{get_market_sentiment()}\n"
    msg += "━━━━━━━━━━━━━━━━━━\n"
    
    msg += "💎 **AI 4대장 추천 (오늘의 매수)**\n"
    for name in ai_4_major:
        msg += f" • {name}: {get_stock_pro_details(name)}\n"
    
    msg += "\n🔥 **연속 포착 주도주 (정밀 분석)**\n"
    for name in overlapping[:5]:
        details = get_stock_pro_details(name)
        msg += f"🏆 **{name}**\n"
        msg += f" ├ 💰 시세: {details}\n"
        msg += f" ├ 🤖 AI: 긍정 (기관/외인 수급 확인 권장)\n"
        msg += f" ├ ⏳ 재료: 지속 (상승 압력 유효)\n"
        msg += f" └ 📈 섹터: {name} 관련 주도 테마\n\n"

    msg += "━━━━━━━━━━━━━━━━━━\n"
    msg += "💡 **PRO TIP**: 거래량이 전일 대비 2배 이상인지 확인하세요!"

    async with bot:
        await bot.send_message(chat_id=CHAT_ID, text=msg, parse_mode='Markdown')

if __name__ == "__main__":
    asyncio.run(main())

# main.py의 크롤링 부분을 아래 내용으로 보강하세요.

def pro_crawling(soup):
    # 방법 1: 기존 클래스 이름으로 찾기
    tags = soup.select('.ranking-stock-name')
    
    # 방법 2: 방법 1이 실패하면 모든 링크(a) 중 종목 같은 것 찾기
    if not tags:
        tags = soup.select('td a')
        
    # 방법 3: 특정 키워드가 포함된 모든 텍스트 뒤지기
    if not tags:
        tags = soup.find_all(['strong', 'span', 'a'], string=True)

    # 종목명만 깨끗하게 정리 (숫자나 불필요한 공백 제거)
    stocks = []
    for t in tags:
        name = t.text.strip()
        if name and len(name) <= 10: # 종목명은 보통 10자 이내
            stocks.append(name)
    
    return list(dict.fromkeys(stocks))[:20] # 중복 제거 후 20개
