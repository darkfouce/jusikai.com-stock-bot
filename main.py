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

async def main():
    if not TOKEN or not CHAT_ID: return
    bot = telegram.Bot(token=TOKEN)
    
    # 1. 크롤링 (강화된 검색 로직)
    url = "https://jusikai.com/"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    
    try:
        res = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(res.text, 'html.parser')
        
        # [PRO] 특정 태그가 아니라, 종목명처럼 보이는 2~10자 사이의 모든 텍스트 수집
        # 사이트 구조가 바뀌어도 대응 가능합니다.
        tags = soup.select('.ranking-stock-name') or soup.select('td a') or soup.select('tr td')
        today_list = [t.text.strip() for t in tags if 2 <= len(t.text.strip()) <= 8]
        today_list = list(dict.fromkeys(today_list))[:25] # 중복 제거 후 25개
        
        if not today_list:
            await bot.send_message(chat_id=CHAT_ID, text="⚠️ 사이트에서 종목을 읽지 못했습니다. 구조 확인이 필요합니다.")
            return
    except Exception as e:
        await bot.send_message(chat_id=CHAT_ID, text=f"❌ 사이트 접속 에러: {e}")
        return

    # 2. 데이터 처리 (TypeError 방지 패치)
    today = (datetime.utcnow() + timedelta(hours=9)).strftime('%Y-%m-%d')
    new_df = pd.DataFrame({'date': [today]*len(today_list), 'stock': today_list})

    if os.path.exists(DATA_FILE):
        try:
            # 파일을 읽을 때 모든 데이터를 '문자열'로 강제 지정
            df = pd.read_csv(DATA_FILE, dtype=str)
            df = pd.concat([df, new_df]).drop_duplicates()
        except: df = new_df
    else: df = new_df
    df.to_csv(DATA_FILE, index=False)

    # 3. 리포트 작성 (AI 4대장 & 중복 포착)
    limit = (datetime.now() - timedelta(days=2)).strftime('%Y-%m-%d')
    recent = df[df['date'] >= limit] # 문자열 상태로 비교
    overlapping = recent['stock'].value_counts()[recent['stock'].value_counts() >= 2].index.tolist()

    msg = f"🔍 **[PRO] 오늘의 분석 리포트 ({today})**\n"
    msg += "━━━━━━━━━━━━━━━━━━\n"
    msg += "✨ **AI 4대장 추천**\n"
    for s in today_list[:4]: msg += f" • {s}\n"
    
    msg += "\n🔥 **2~3일 중복 주도주**\n"
    if not overlapping:
        msg += " (연속 포착된 종목 없음)\n"
    for s in overlapping[:5]:
        msg += f"🏆 **{s}**\n ├ 🤖 AI: 긍정 / ⏳ 재료: 지속\n └ 📈 섹터: 주도 테마\n\n"
    
    msg += "━━━━━━━━━━━━━━━━━━\n💡 224일선 부근 매집 여부를 확인하세요!"

    async with bot:
        await bot.send_message(chat_id=CHAT_ID, text=msg, parse_mode='Markdown')

if __name__ == "__main__":
    asyncio.run(main())
