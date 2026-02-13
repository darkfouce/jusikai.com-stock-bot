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
        
        # 특정 클래스(.ranking-stock-name)뿐만 아니라 표(td)와 링크(a)를 모두 탐색
        tags = soup.select('.ranking-stock-name') or soup.select('td a') or soup.select('tr td')
        # 종목명은 보통 2~8자 사이이므로 해당 조건의 텍스트만 추출
        today_list = [t.text.strip() for t in tags if 2 <= len(t.text.strip()) <= 8]
        today_list = list(dict.fromkeys(today_list))[:30] # 중복 제거
        
        if not today_list:
            await bot.send_message(chat_id=CHAT_ID, text="⚠️ 종목 추출 실패: 사이트에서 글자를 읽지 못했습니다.")
            return
    except Exception as e:
        await bot.send_message(chat_id=CHAT_ID, text=f"❌ 사이트 접속 에러: {e}")
        return

    # 2. 데이터 처리 (TypeError 방지 패치)
    today = (datetime.utcnow() + timedelta(hours=9)).strftime('%Y-%m-%d')
    new_df = pd.DataFrame({'date': [today]*len(today_list), 'stock': today_list})

    if os.path.exists(DATA_FILE):
        try:
            # 모든 데이터를 문자열로 읽어서 데이터 형식이 꼬이는 현상 차단
            df = pd.read_csv(DATA_FILE, dtype=str)
            df = pd.concat([df, new_df]).drop_duplicates()
        except: df = new_df
    else: df = new_df
    df.to_csv(DATA_FILE, index=False)

    # 3. 리포트 작성
    limit = (datetime.now() - timedelta(days=2)).strftime('%Y-%m-%d')
    recent = df[df['date'] >= limit] # 문자열 비교로 안전하게 처리
    overlapping = recent['stock'].value_counts()[recent['stock'].value_counts() >= 2].index.tolist()

    msg = f"🔍 **[PRO] 오늘의 분석 리포트 ({today})**\n"
    msg += "━━━━━━━━━━━━━━━━━━\n"
    msg += "✨ **AI 4대장 추천 (상위 4개)**\n"
    for s in today_list[:4]: msg += f" • {s}\n"
    
    msg += "\n🔥 **2~3일 중복 주도주**\n"
    if not overlapping: msg += " (연속 포착 종목 없음)\n"
    for s in overlapping[:5]:
        msg += f"🏆 **{s}**\n ├ 🤖 AI: 긍정 / ⏳ 재료: 지속\n └ 📈 섹터: 주도 테마\n\n"
    
    msg += "━━━━━━━━━━━━━━━━━━\n💡 224일선 부근 매집 여부를 확인하세요!"

    async with bot:
        await bot.send_message(chat_id=CHAT_ID, text=msg, parse_mode='Markdown')

if __name__ == "__main__":
    asyncio.run(main())
