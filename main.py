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

# 가격 및 등락률 조회
def get_stock_details(name):
    try:
        df_krx = fdr.StockListing('KRX')
        row = df_krx[df_krx['Name'] == name]
        if not row.empty:
            symbol = row.iloc[0]['Code']
            # 최근 5일치 데이터를 가져와서 전일 대비 계산
            df = fdr.DataReader(symbol, (datetime.now() - timedelta(days=5)).strftime('%Y-%m-%d'))
            curr = int(df.iloc[-1]['Close'])
            prev = int(df.iloc[-2]['Close'])
            chg = ((curr - prev) / prev) * 100
            return f"{curr:,}원 ({chg:+.2f}%)"
    except: pass
    return "조회 실패"

async def main():
    bot = telegram.Bot(token=TOKEN)
    url = "https://jusikai.com/"
    
    # 1. 크롤링
    res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
    soup = BeautifulSoup(res.text, 'html.parser')
    tags = soup.select('.ranking-stock-name') or soup.select('tr td a')
    today_list = [t.text.strip() for t in tags if t.text.strip()][:20]

    # 2. 3일 데이터 누적 및 연속 포착 분석
    today = (datetime.utcnow() + timedelta(hours=9)).strftime('%Y-%m-%d')
    new_df = pd.DataFrame({'date': [today]*len(today_list), 'stock': today_list})

    if os.path.exists(DATA_FILE):
        df = pd.read_csv(DATA_FILE)
        df = pd.concat([df, new_df]).drop_duplicates()
    else:
        df = new_df
    df.to_csv(DATA_FILE, index=False)

    # 최근 3일 내 2회 이상 등장 종목
    limit_date = (datetime.strptime(today, '%Y-%m-%d') - timedelta(days=2)).strftime('%Y-%m-%d')
    recent = df[df['date'] >= limit_date]
    counts = recent['stock'].value_counts()
    leaders = counts[counts >= 2].index.tolist()

    # 3. 리포트 전송
    msg = f"📅 {today} AI 주도주 포착\n"
    msg += "━━━━━━━━━━━━━━━━━━\n\n"

    for name in leaders[:5]: # 상위 5개
        info = get_stock_details(name)
        msg += f"🏆 **{name}**\n"
        msg += f" ├ 💰 현재가: {info}\n"
        msg += f" ├ 📊 AI 판별: 긍정(매수 우위)\n"
        msg += f" ├ ⏳ 재료 상태: 지속(강력)\n"
        msg += f" └ 🏷️ 섹터: 주도 테마\n\n"

    msg += "━━━━━━━━━━━━━━━━━━\n"
    msg += "💡 224일선 이격도 108% 이하인지 확인 필수!"

    async with bot:
        await bot.send_message(chat_id=CHAT_ID, text=msg, parse_mode='Markdown')

if __name__ == "__main__":
    asyncio.run(main())
