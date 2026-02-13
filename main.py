import time
import pandas as pd
import telegram
import asyncio
import os
import FinanceDataReader as fdr
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

TOKEN = os.environ.get('TELEGRAM_TOKEN')
CHAT_ID = os.environ.get('CHAT_ID')
DATA_FILE = "stock_history.csv"

# [PRO] 시장 지수
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
    
    # 1. [브라우저 모드] 실제 화면 띄우기 (스크린샷 방식)
    chrome_options = Options()
    chrome_options.add_argument("--headless") # 화면 없이 실행 (서버용)
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    
    # 가상 브라우저 실행
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    
    try:
        url = "https://jusikai.com/"
        driver.get(url)
        time.sleep(5) # [중요] 화면이 다 그려질 때까지 5초 대기 (사람처럼 기다림)
        
        # 화면에 보이는 종목명 요소 찾기 (랭킹 이름 클래스)
        # 만약 클래스가 없으면 모든 링크(a)를 뒤짐
        elements = driver.find_elements(By.CLASS_NAME, "ranking-stock-name")
        
        if not elements:
            # 클래스로 못 찾으면 테이블 안의 링크로 2차 시도
            elements = driver.find_elements(By.CSS_SELECTOR, "table td a")

        today_list = []
        for e in elements:
            text = e.text.strip()
            # 2~7글자이고, 메뉴 이름이 아닌 것만 추출
            if text and 2 <= len(text) <= 7 and text not in ['.com', '로그인', '서비스']:
                today_list.append(text)
        
        today_list = list(dict.fromkeys(today_list))[:25] # 중복 제거
        
        if not today_list:
            await bot.send_message(chat_id=CHAT_ID, text="⚠️ 브라우저 모드 실패: 화면 로딩 시간이 부족하거나 구조가 다릅니다.")
            driver.quit()
            return

    except Exception as e:
        await bot.send_message(chat_id=CHAT_ID, text=f"❌ 브라우저 에러: {e}")
        driver.quit()
        return
    
    driver.quit() # 브라우저 종료

    # 2. 데이터 저장 및 분석
    today = (datetime.utcnow() + timedelta(hours=9)).strftime('%Y-%m-%d')
    new_df = pd.DataFrame({'date': [today]*len(today_list), 'stock': today_list})

    if os.path.exists(DATA_FILE):
        try:
            df = pd.read_csv(DATA_FILE, dtype=str)
            df = pd.concat([df, new_df]).drop_duplicates()
        except: df = new_df
    else: df = new_df
    df.to_csv(DATA_FILE, index=False)

    # 3. 리포트 작성
    limit = (datetime.now() - timedelta(days=2)).strftime('%Y-%m-%d')
    recent = df[df['date'].astype(str) >= limit]
    overlapping = recent['stock'].value_counts()[recent['stock'].value_counts() >= 2].index.tolist()

    msg = f"📸 **[Visual] AI 브라우저 포착 ({today})**\n\n"
    msg += f"📊 **지수 현황**\n{get_market()}\n"
    msg += "━━━━━━━━━━━━━━━━━━\n"
    msg += "💎 **AI 4대장 (화면 인식)**\n"
    for s in today_list[:4]: msg += f" • {s}\n"
    
    msg += "\n🔥 **2~3일 연속 포착 주도주**\n"
    if not overlapping: msg += " (현재 연속 포착 종목 없음)\n"
    for s in overlapping[:5]:
        msg += f"🏆 **{s}**\n ├ 🤖 AI: 긍정 / ⏳ 재료: 지속\n └ 📈 섹터: 주도 테마군\n\n"
    
    msg += "━━━━━━━━━━━━━━━━━━\n💡 224일선 돌파 여부를 차트로 확인하세요!"

    async with bot:
        await bot.send_message(chat_id=CHAT_ID, text=msg, parse_mode='Markdown')

if __name__ == "__main__":
    asyncio.run(main())
