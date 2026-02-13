import requests
from bs4 import BeautifulSoup
import pandas as pd
import telegram
import asyncio
import os
from datetime import datetime, timedelta

# 1. 환경변수 가져오기
TOKEN = os.environ.get('TELEGRAM_TOKEN')
CHAT_ID = os.environ.get('CHAT_ID')
DATA_FILE = "stock_history.csv"
TARGET_URL = "https://jusikai.com/"

async def run_bot():
    # [1단계] 봇 연결 확인 (실행 시작 알림)
    bot = telegram.Bot(token=TOKEN)
    try:
        print("🤖 봇 실행 시작... 텔레그램 테스트 중")
        # 시작하자마자 메시지를 한번 보내봅니다. (토큰이 맞는지 확인용)
        # 너무 시끄러우면 나중에 주석 처리하세요.
        # await bot.send_message(chat_id=CHAT_ID, text="🤖 주식AI 봇이 작동을 시작했습니다!")
    except Exception as e:
        print(f"❌ 텔레그램 연결 실패! 토큰이나 CHAT_ID를 확인하세요.\n에러: {e}")
        return

    # [2단계] 크롤링 시도
    print(f"🔍 {TARGET_URL} 접속 시도 중...")
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    found_stocks = []
    
    try:
        response = requests.get(TARGET_URL, headers=headers)
        response.raise_for_status() # 접속 에러 체크
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # [중요] 여기에 실제 사이트의 '종목명' 클래스 이름을 넣어야 합니다.
        # 개발자 도구(F12)로 확인 필요. 일단 흔한 이름들로 시도해봅니다.
        # 예: .stock-name, .name, .company, td a 등
        
        # ⚠️ 사용자가 직접 수정해야 할 부분 ⚠️
        # 만약 사이트 구조를 모르면 아래 줄을 수정해야 합니다.
        # 여기서는 예시로 가장 일반적인 테이블 구조를 가정합니다.
        stock_elements = soup.select('.ranking-stock-name') 
        
        # 만약 위 클래스가 없으면, 데이터가 0개로 나옵니다.
        if not stock_elements:
             # 비상용: h3 태그나 strong 태그라도 긁어보기 (테스트용)
             stock_elements = soup.select('tr td a') 
        
        found_stocks = [s.text.strip() for s in stock_elements if s.text.strip()]
        found_stocks = found_stocks[:20] # 상위 20개만
        
        print(f"✅ 크롤링 성공: {len(found_stocks)}개 발견")

    except Exception as e:
        error_msg = f"❌ 사이트 접속 실패: {e}"
        print(error_msg)
        await bot.send_message(chat_id=CHAT_ID, text=error_msg)
        return

    # [3단계] 데이터 분석 및 저장
    if not found_stocks:
        # 종목을 못 찾았으면 경고 메시지 전송
        fail_msg = f"⚠️ 사이트 접속은 됐는데 종목을 못 찾았습니다.\nHTML 클래스 이름(.ranking-stock-name)이 틀린 것 같습니다.\n개발자 도구(F12)로 확인해서 main.py를 수정해주세요."
        await bot.send_message(chat_id=CHAT_ID, text=fail_msg)
        return

    today_date = (datetime.utcnow() + timedelta(hours=9)).strftime('%Y-%m-%d')
    
    # 데이터 저장 로직
    if os.path.exists(DATA_FILE):
        df = pd.read_csv(DATA_FILE)
        df = df[df['date'] != today_date] # 오늘꺼 중복 삭제
    else:
        df = pd.DataFrame(columns=['date', 'stock'])
        
    new_data = pd.DataFrame({'date': [today_date]*len(found_stocks), 'stock': found_stocks})
    df = pd.concat([df, new_data])
    df.to_csv(DATA_FILE, index=False)
    
    # [4단계] 연속 등장 종목 분석
    three_days_ago = (datetime.strptime(today_date, '%Y-%m-%d') - timedelta(days=2)).strftime('%Y-%m-%d')
    recent_df = df[df['date'] >= three_days_ago]
    
    stock_counts = recent_df['stock'].value_counts()
    targets = stock_counts[stock_counts >= 2] # 2회 이상 등장
    
    # [5단계] 결과 전송
    msg = f"📅 {today_date} [주식AI] 분석 결과\n"
    msg += f"수집된 종목: {len(found_stocks)}개\n\n"
    
    if len(targets) > 0:
        msg += "🔥 **집중 관찰 종목 (2회 이상 포착)**\n"
        for name, count in targets.items():
            icon = "👑" if count >= 3 else "✅"
            msg += f"{icon} {name} ({count}회)\n"
    else:
        msg += "👀 연속 포착된 종목이 없습니다.\n(데이터가 더 쌓여야 합니다)"

    await bot.send_message(chat_id=CHAT_ID, text=msg)
    print("🚀 최종 리포트 전송 완료")

if __name__ == "__main__":
    asyncio.run(run_bot())
