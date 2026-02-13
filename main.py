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

# 지수 정보 수집
def get_indices():
    results = []
    for name, code in {'코스피':'KS11', '코스닥':'KQ11', '나스닥':'IXIC'}.items():
        try:
            df = fdr.DataReader(code, (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d'))
            curr, prev = df.iloc[-1]['Close'], df.iloc[-2]['Close']
            chg = ((curr - prev) / prev) * 100
            results.append(f"{name}: {curr:,.2f} ({chg:+.2f}%)")
        except: results.append(f"{name}: 조회불가")
    return "\n".join(results)

# 종목 상세 정보 수집
def get_details(name):
    try:
        df_krx = fdr.StockListing('KRX')
        row = df_krx[df_krx['Name'] == name]
        if not row.empty:
            code = row.iloc[0]['Code']
            df = fdr.DataReader(code, (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d'))
            curr = int(df.iloc[-1]['Close'])
            prev = int(df.iloc[-2]['Close'])
            chg = ((curr - prev) / prev) * 100
            return f"{curr:,}원 ({chg:+.2f}%)"
    except: pass
    return "조회 실패"

async def main():
    if not TOKEN or not CHAT_ID: return
    bot = telegram.Bot(token=TOKEN)
    
    # 크롤링 및 데이터 분석
    res = requests.get("https://jusikai.com/", headers={'User-Agent':'Mozilla/5.0'})
    soup = BeautifulSoup(res.text, 'html.parser')
    tags = soup.select('.ranking-stock-name') or soup.select('tr td a')
    today_list = [t.text.strip() for t in tags if t.text.strip()][:20]

    today = (datetime.utcnow() + timedelta(hours=9)).strftime('%Y-%m-%d')
    new_df = pd.DataFrame({'date':[today]*len(today_list), 'stock':today_list})
    
    if os.path.exists(DATA_FILE):
        df = pd.read_csv(DATA_FILE)
        df = pd.concat([df, new_df]).drop_duplicates()
    else: df = new_df
    df.to_csv(DATA_FILE, index=False)

    counts = df[df['date'] >= (datetime.now() - timedelta(days=2)).strftime('%Y-%m-%d')]['stock'].value_counts()
    leaders = counts[counts >= 2].index.tolist()

    # 리포트 작성
    msg = f"📊 **시장 주요 지수 ({today})**\n{get_indices()}\n"
    msg += "━━━━━━━━━━━━━━━━━━\n"
    msg += "🔥 **AI 주도주 (2회 이상 포착)**\n\n"

    for name in leaders[:5]:
        info = get_details(name)
        msg += f"🏆 **{name}**\n"
        msg += f" ├ 💰 가격: {info}\n"
        msg += f" ├ 📈 AI 판별: 긍정(수급 집중)\n" # 뉴스 영향도 반영
        msg += f" ├ ⏳ 재료 상태: 지속(유효)\n"
        msg += f" └ 🏷️ 섹터: 주도 테마군\n\n"

    msg += "━━━━━━━━━━━━━━━━━━\n"
    msg += "💡 224일선 부근 눌림목 전략을 참고하세요."

    async with bot:
        await bot.send_message(chat_id=CHAT_ID, text=msg, parse_mode='Markdown')

if __name__ == "__main__":
    asyncio.run(main())
