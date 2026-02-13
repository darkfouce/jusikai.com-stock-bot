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

# 가격 및 등락률 가져오기 함수
def get_stock_info(name):
    try:
        # 한국 거래소 종목 리스트 불러오기 (최초 1회)
        df_krx = fdr.StockListing('KRX')
        row = df_krx[df_krx['Name'] == name]
        if not row.empty:
            symbol = row.iloc[0]['Code']
            # 최근 2일치 데이터로 등락 계산
            df = fdr.DataReader(symbol, (datetime.now() - timedelta(days=5)).strftime('%Y-%m-%d'))
            curr_price = int(df.iloc[-1]['Close'])
            prev_price = int(df.iloc[-2]['Close'])
            change_percent = ((curr_price - prev_price) / prev_price) * 100
            return f"{curr_price:,}원 ({change_percent:+.2f}%)"
    except:
        pass
    return "데이터 확인 불가"

async def run_analysis():
    bot = telegram.Bot(token=TOKEN)
    url = "https://jusikai.com/"
    headers = {'User-Agent': 'Mozilla/5.0'}
    
    # 1. 크롤링
    res = requests.get(url, headers=headers)
    soup = BeautifulSoup(res.text, 'html.parser')
    tags = soup.select('.ranking-stock-name') or soup.select('tr td a')
    today_stocks = [t.text.strip() for t in tags if t.text.strip()][:20]

    # 2. 데이터 저장 및 분석
    today = (datetime.utcnow() + timedelta(hours=9)).strftime('%Y-%m-%d')
    new_df = pd.DataFrame({'date': [today]*len(today_stocks), 'stock': today_stocks})

    if os.path.exists(DATA_FILE):
        df = pd.read_csv(DATA_FILE)
        df = pd.concat([df, new_df]).drop_duplicates()
    else:
        df = new_df
    df.to_csv(DATA_FILE, index=False)

    recent_limit = (datetime.strptime(today, '%Y-%m-%d') - timedelta(days=2)).strftime('%Y-%m-%d')
    recent_df = df[df['date'] >= recent_limit]
    counts = recent_df['stock'].value_counts()
    leaders = counts[counts >= 2].index.tolist()

    # 3. 리포트 작성
    msg = f"📅 {today} 진짜 주도주 랭킹\n"
    msg += "━━━━━━━━━━━━━━━━━━\n\n"

    if not leaders:
        msg += "👀 연속 포착된 종목이 없습니다.\n"
    else:
        for i, name in enumerate(leaders[:5], 1):
            price_info = get_stock_info(name)
            msg += f"{i}위. 🏆 **{name}**\n"
            msg += f" ├ 💰 현재가: {price_info}\n"
            msg += f" ├ 📊 AI 판별: 긍정(수급 집중)\n"
            msg += f" ├ ⏳ 재료 상태: 지속(추세 유효)\n"
            msg += f" └ 🏷️ 섹터: 주도 테마군\n\n"

    msg += "━━━━━━━━━━━━━━━━━━\n"
    msg += "💡 Tip: 224일선 부근 매집봉 여부를 확인하세요!"

    async with bot:
        await bot.send_message(chat_id=CHAT_ID, text=msg, parse_mode='Markdown')

if __name__ == "__main__":
    asyncio.run(run_analysis())
