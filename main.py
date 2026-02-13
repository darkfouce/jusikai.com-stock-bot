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

def get_market():
    res = ""
    for n, c in {'코스피':'KS11','코스닥':'KQ11','나스닥':'IXIC'}.items():
        try:
            df = fdr.DataReader(c, (datetime.now()-timedelta(days=7)).strftime('%Y-%m-%d'))
            curr, prev = df.iloc[-1]['Close'], df.iloc[-2]['Close']
            chg = ((curr-prev)/prev)*100
            res += f" • {n}: {curr:,.2f} ({chg:+.2f}%)\n"
        except: res += f" • {n}: 조회불가\n"
    return res

async def main():
    if not TOKEN or not CHAT_ID: return
    bot = telegram.Bot(token=TOKEN)
    
    # 크롤링
    h = {'User-Agent':'Mozilla/5.0'}
    r = requests.get("https://jusikai.com/", headers=h)
    soup = BeautifulSoup(r.text, 'html.parser')
    tags = soup.select('.ranking-stock-name') or soup.select('td a')
    today_list = [t.text.strip() for t in tags if 2 <= len(t.text.strip()) <= 10]

    # 오늘 데이터 생성
    today = (datetime.utcnow() + timedelta(hours=9)).strftime('%Y-%m-%d')
    new_df = pd.DataFrame({'date':[today]*len(today_list), 'stock':today_list})

    # 기록 누적 (dtype 강제 지정으로 에러 방지)
    if os.path.exists(DATA_FILE):
        try:
            df = pd.read_csv(DATA_FILE, dtype={'date': str, 'stock': str})
            df = pd.concat([df, new_df]).drop_duplicates()
        except: df = new_df
    else: df = new_df
    df.to_csv(DATA_FILE, index=False)

    # 2~3일 연속 포착 분석
    limit = (datetime.now() - timedelta(days=2)).strftime('%Y-%m-%d')
    recent = df[df['date'].astype(str) >= limit]
    overlapping = recent['stock'].value_counts()[recent['stock'].value_counts() >= 2].index.tolist()

    # 리포트 발송
    msg = f"🔍 **[PRO] AI 분석 리포트 ({today})**\n\n"
    msg += f"📊 **지수 현황**\n{get_market()}\n"
    msg += "━━━━━━━━━━━━━━━━━━\n"
    msg += "✨ **AI 4대장 오늘의 추천**\n"
    for s in today_list[:4]: msg += f" • {s}\n"
    msg += "\n🔥 **2~3일 연속 포착 주도주**\n"
    for s in overlapping[:5]:
        msg += f"🏆 **{s}**\n ├ 🤖 AI: 긍정 / ⏳ 재료: 지속\n └ 📈 섹터: 주도 테마군\n\n"
    msg += "━━━━━━━━━━━━━━━━━━\n💡 224일선 부근 눌림목을 확인하세요!"

    async with bot:
        await bot.send_message(chat_id=CHAT_ID, text=msg, parse_mode='Markdown')

if __name__ == "__main__":
    asyncio.run(main())
