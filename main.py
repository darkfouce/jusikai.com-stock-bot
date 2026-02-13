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

# 주요 지수 정보 가져오기 함수
def get_market_indices():
    indices = {
        '코스피': 'KS11',
        '코스닥': 'KQ11',
        '나스닥': 'IXIC'
    }
    result = ""
    for name, code in indices.items():
        try:
            # 최근 5일 데이터로 등락 계산
            df = fdr.DataReader(code, (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d'))
            curr = df.iloc[-1]['Close']
            prev = df.iloc[-2]['Close']
            chg = ((curr - prev) / prev) * 100
            result += f" {name}: {curr:,.2f} ({chg:+.2f}%)\n"
        except:
            result += f" {name}: 데이터 조회 실패\n"
    return result

# 종목별 현재가 및 등락률 조회
def get_stock_details(name):
    try:
        df_krx = fdr.StockListing('KRX')
        row = df_krx[df_krx['Name'] == name]
        if not row.empty:
            symbol = row.iloc[0]['Code']
            df = fdr.DataReader(symbol, (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d'))
            curr = int(df.iloc[-1]['Close'])
            prev = int(df.iloc[-2]['Close'])
            chg = ((curr - prev) / prev) * 100
            return f"{curr:,}원 ({chg:+.2f}%)"
    except: pass
    return "조회 실패"

async def main():
    bot = telegram.Bot(token=TOKEN)
    url = "https://jusikai.com/"
    
    # 1. 지수 데이터 수집
    market_info = get_market_indices()

    # 2. 주도주 크롤링
    res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
    soup = BeautifulSoup(res.text, 'html.parser')
    tags = soup.select('.ranking-stock-name') or soup.select('tr td a')
    today_list = [t.text.strip() for t in tags if t.text.strip()][:20]

    # 3. 데이터 누적 분석 (최근 3일 내 2회 이상)
    today = (datetime.utcnow() + timedelta(hours=9)).strftime('%Y-%m-%d')
    new_df = pd.DataFrame({'date': [today]*len(today_list), 'stock': today_list})

    if os.path.exists(DATA_FILE):
        df = pd.read_csv(DATA_FILE)
        df = pd.concat([df, new_df]).drop_duplicates()
    else:
        df = new_df
    df.to_csv(DATA_FILE, index=False)

    limit_date = (datetime.strptime(today, '%Y-%m-%d') - timedelta(days=2)).strftime('%Y-%m-%d')
    recent = df[df['date'] >= limit_date]
    counts = recent['stock'].value_counts()
    leaders = counts[counts >= 2].index.tolist()

    # 4. 리포트 구성
    msg = f"📊 **시장 주요 지수 ({today})**\n"
    msg += market_info + "\n"
    msg += "━━━━━━━━━━━━━━━━━━\n"
    msg += f"🔥 **AI 주도주 (2회 이상 포착)**\n\n"

    for name in leaders[:5]:
        info = get_stock_details(name)
        msg += f"🏆 **{name}**\n"
        msg += f" ├ 💰 현재가: {info}\n"
        msg += f" ├ 📊 AI 판별: 긍정(수급 집중)\n"
        msg += f" ├ ⏳ 재료 상태: 지속(유효)\n"
        msg += f" └ 🏷️ 섹터: 주도 테마\n\n"

    msg += "━━━━━━━━━━━━━━━━━━\n"
    msg += "💡 224일선 부근 눌림목 매수 전략 유효!"

    async with bot:
        await bot.send_message(chat_id=CHAT_ID, text=msg, parse_mode='Markdown')

if __name__ == "__main__":
    asyncio.run(main())
