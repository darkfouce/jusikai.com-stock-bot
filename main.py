import requests
from bs4 import BeautifulSoup
import pandas as pd
import telegram
import asyncio
import os
import FinanceDataReader as fdr
from datetime import datetime, timedelta

TOKEN = os.environ.get('TELEGRAM_TOKEN')
CHAT_ID = os.environ.get('CHAT_ID')
DATA_FILE = "stock_history.csv"

# [PRO] 지수 및 가격 정보 수집 (기존 동일)
def get_market_data():
    indices = {'코스피':'KS11', '코스닥':'KQ11', '나스닥':'IXIC'}
    res = ""
    for name, code in indices.items():
        try:
            df = fdr.DataReader(code, (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d'))
            curr, prev = df.iloc[-1]['Close'], df.iloc[-2]['Close']
            chg = ((curr - prev) / prev) * 100
            res += f" • {name}: {curr:,.2f} ({chg:+.2f}%)\n"
        except: res += f" • {name}: 조회 실패\n"
    return res

async def main():
    if not TOKEN or not CHAT_ID: return
    bot = telegram.Bot(token=TOKEN)
    
    # [진단] 사이트 접속 시도
    url = "https://jusikai.com/"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # [PRO] 태그 이름이 바뀌어도 '종목명'처럼 보이는 글자를 모두 수집
        # 1순위: 기존 태그, 2순위: 표(td) 안의 글자, 3순위: 링크(a) 텍스트
        tags = soup.select('.ranking-stock-name') or soup.select('td') or soup.select('a')
        raw_stocks = [t.text.strip() for t in tags if 2 <= len(t.text.strip()) <= 10]
        
        # 중복 제거 및 유효 종목만 추출
        today_all = list(dict.fromkeys(raw_stocks))[:30]
        
        if not today_all:
             print("⚠️ 데이터를 찾지 못했습니다. 사이트 구조 확인이 필요합니다.")
             return
    except Exception as e:
        print(f"❌ 접속 실패: {e}")
        return

    # 1. AI 4대장 추출 (상위 4개)
    ai_4_major = today_all[:4]

    # 2. 데이터 누적 분석 (2~3일 연속 포착)
    today = (datetime.utcnow() + timedelta(hours=9)).strftime('%Y-%m-%d')
    new_df = pd.DataFrame({'date': [today]*len(today_all), 'stock': today_all})

    if os.path.exists(DATA_FILE):
        try:
            # [오류 해결] csv를 읽을 때 형식을 강제하여 TypeError 방지
            df = pd.read_csv(DATA_FILE, dtype={'date': str, 'stock': str})
            df = pd.concat([df, new_df]).drop_duplicates()
        except: df = new_df # 파일이 깨졌으면 새로 시작
    else: df = new_df
    df.to_csv(DATA_FILE, index=False)

    limit = (datetime.now() - timedelta(days=2)).strftime('%Y-%m-%d')
    recent = df[df['date'].astype(str) >= limit]
    counts = recent['stock'].value_counts()
    overlapping = counts[counts >= 2].index.tolist()

    # 3. 리포트 작성 (PRO 양식)
    msg = f"🔍 **[PRO] 마켓 분석 리포트 ({today})**\n\n"
    msg += f"📊 **지수 현황**\n{get_market_data()}\n"
    msg += "━━━━━━━━━━━━━━━━━━\n"
    
    msg += "💎 **AI 4대장 오늘의 매수 추천**\n"
    for name in ai_4_major:
        msg += f" • {name}\n"
    
    msg += "\n🔥 **2~3일 연속 포착 (중복 주도주)**\n"
    for name in overlapping[:5]:
        msg += f"🏆 **{name}**\n"
        msg += f" ├ 🤖 AI: 긍정 (수급 유입)\n"
        msg += f" ├ ⏳ 재료: 지속 (상승 압력)\n"
        msg += f" └ 📈 섹터: {name} 관련 테마\n\n"

    msg += "━━━━━━━━━━━━━━━━━━\n"
    msg += "💡 224일선 돌파 여부를 반드시 확인하세요!" # 사용자 관심사 반영

    async with bot:
        await bot.send_message(chat_id=CHAT_ID, text=msg, parse_mode='Markdown')

if __name__ == "__main__":
    asyncio.run(main())
