import requests
from bs4 import BeautifulSoup
import pandas as pd
import telegram
import asyncio
import os
from datetime import datetime, timedelta

# 1. 설정값 가져오기 (비밀번호 숨김)
TOKEN = os.environ.get('TELEGRAM_TOKEN')
CHAT_ID = os.environ.get('CHAT_ID')
DATA_FILE = "stock_history.csv"

# 2. 크롤링 함수
def get_stocks():
    url = "https://jusikai.com/" # 실제 사이트 주소
    headers = {'User-Agent': 'Mozilla/5.0'}

    try:
        res = requests.get(url, headers=headers)
        soup = BeautifulSoup(res.text, 'html.parser')

        # [주의] 여기가 제일 중요! 실제 사이트에서 종목명 태그(Class)를 찾아야 함
        # 예시로 '.ranking-stock-name'을 썼지만, 안 되면 개발자 도구로 확인 필요
        tags = soup.select('.ranking-stock-name') 

        stocks = [t.text.strip() for t in tags if t.text.strip()]
        return stocks[:20] # 상위 20개만
    except:
        return []

# 3. 데이터 저장 및 분석 함수
def analyze(today_stocks):
    # 오늘 날짜
    today = (datetime.utcnow() + timedelta(hours=9)).strftime('%Y-%m-%d')

    # 1) 기존 기록 불러오기
    if os.path.exists(DATA_FILE):
        df = pd.read_csv(DATA_FILE)
    else:
        df = pd.DataFrame(columns=['date', 'stock'])

    # 2) 오늘 데이터 추가 (중복 방지)
    df = df[df['date'] != today]
    new_df = pd.DataFrame({'date': [today]*len(today_stocks), 'stock': today_stocks})
    df = pd.concat([df, new_df])

    # 3) 파일 저장
    df.to_csv(DATA_FILE, index=False)

    # 4) 최근 3일간 2회 이상 등장한 종목 찾기
    start_date = (datetime.strptime(today, '%Y-%m-%d') - timedelta(days=3)).strftime('%Y-%m-%d')
    recent = df[df['date'] >= start_date]

    counts = recent['stock'].value_counts()
    targets = counts[counts >= 2] # 2회 이상 포착

    return targets, today

# 4. 텔레그램 전송 함수
async def send_msg(targets, date):
    bot = telegram.Bot(token=TOKEN)
    msg = f"📅 {date} [주식AI] 주도주 알림\n\n"

    if len(targets) > 0:
        msg += "🔥 **최근 3일 내 연속 포착된 종목**\n(세력이 돈을 계속 넣는 중)\n\n"
        for name, count in targets.items():
            icon = "👑" if count >= 3 else "✅"
            msg += f"{icon} {name} ({count}회 등장)\n"
    else:
        msg += "👀 오늘은 연속 포착된 종목이 없습니다."

    await bot.send_message(chat_id=CHAT_ID, text=msg)

if __name__ == "__main__":
    stocks = get_stocks()
    if stocks:
        targets, date = analyze(stocks)
        asyncio.run(send_msg(targets, date))
    else:
        print("데이터 수집 실패 (사이트 구조 확인 필요)")
