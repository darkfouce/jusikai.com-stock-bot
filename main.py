import time
import telegram
import asyncio
import os
import google.generativeai as genai
from PIL import Image
from io import BytesIO
import pandas as pd
import FinanceDataReader as fdr
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

TOKEN = os.environ.get('TELEGRAM_TOKEN')
CHAT_ID = os.environ.get('CHAT_ID')
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
DATA_FILE = "stock_history.csv"

# [PRO] 시장 지수
def get_market():
    res = ""
    for n, c in {'코스피':'KS11','코스닥':'KQ11','나스닥':'IXIC'}.items():
        try:
            df = fdr.DataReader(c, (datetime.now()-timedelta(days=7)).strftime('%Y-%m-%d'))
            curr = df.iloc[-1]['Close']
            chg = ((curr - df.iloc[-2]['Close']) / df.iloc[-2]['Close']) * 100
            res += f" • {n}: {curr:,.2f} ({chg:+.2f}%)\n"
        except: res += f" • {n}: 조회불가\n"
    return res

async def main():
    if not TOKEN or not CHAT_ID: 
        print("텔레그램 토큰 없음")
        return
    
    bot = telegram.Bot(token=TOKEN)
    
    # 1. 가상 브라우저 설정
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,2000") # 길게 찍기
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    
    today_list = []
    screenshot_bio = None
    
    try:
        # 2. 사이트 스크린샷 촬영
        url = "https://jusikai.com/"
        print("사이트 접속 및 촬영 중...")
        driver.get(url)
        time.sleep(7) # 로딩 대기
        
        png_data = driver.get_screenshot_as_png()
        screenshot_bio = BytesIO(png_data)
        image = Image.open(screenshot_bio)
        
        # 3. 제미니(Vision)에게 물어보기
        if GEMINI_API_KEY:
            print("제미니에게 분석 요청 중...")
            genai.configure(api_key=GEMINI_API_KEY)
            model = genai.GenerativeModel('gemini-1.5-flash') # 빠르고 비전 성능 좋은 모델
            
            prompt = """
            이 웹사이트 스크린샷에서 '주식 종목명'으로 보이는 단어들을 모두 찾아줘.
            메뉴 이름(로그인, 서비스 소개 등)이나 지수 이름(KOSPI 등)은 빼고, 
            순수하게 랭킹이나 표에 있는 종목명(예: 삼성전자, 에코프로 등)만 추출해.
            결과는 쉼표(,)로 구분해서 한 줄로 알려줘. 설명은 필요 없어.
            """
            
            response = model.generate_content([prompt, image])
            ai_text = response.text.strip()
            print(f"제미니 응답: {ai_text}")
            
            # 응답 정리
            raw_list = ai_text.split(',')
            today_list = [x.strip() for x in raw_list if x.strip()]
            today_list = list(dict.fromkeys(today_list))[:25] # 중복 제거
        else:
            print("GEMINI_API_KEY가 없습니다. 스크린샷만 보냅니다.")
            today_list = ["API키_미설정_분석불가"]

    except Exception as e:
        await bot.send_message(chat_id=CHAT_ID, text=f"❌ AI 분석 에러: {e}")
        driver.quit()
        return
    
    driver.quit()

    # 4. 데이터 저장 및 분석
    today = (datetime.utcnow() + timedelta(hours=9)).strftime('%Y-%m-%d')
    if "API키_미설정" not in today_list:
        new_df = pd.DataFrame({'date': [today]*len(today_list), 'stock': today_list})

        if os.path.exists(DATA_FILE):
            try:
                df = pd.read_csv(DATA_FILE, dtype=str)
                df = pd.concat([df, new_df]).drop_duplicates()
            except: df = new_df
        else: df = new_df
        df.to_csv(DATA_FILE, index=False)

        limit = (datetime.now() - timedelta(days=2)).strftime('%Y-%m-%d')
        recent = df[df['date'].astype(str) >= limit]
        overlapping = recent['stock'].value_counts()[recent['stock'].value_counts() >= 2].index.tolist()
    else:
        overlapping = []

    # 5. 리포트 + 사진 전송
    msg = f"🧠 **[Gemini Vision] AI 화면 분석 리포트 ({today})**\n"
    msg += "━━━━━━━━━━━━━━━━━━\n"
    msg += f"📊 **지수 현황**\n{get_market()}\n"
    
    msg += "💎 **제미니가 찾아낸 종목**\n"
    for s in today_list[:10]: msg += f" • {s}\n"
    
    msg += "\n🔥 **2~3일 연속 포착 주도주**\n"
    if not overlapping: msg += " (식별된 연속 종목 없음)\n"
    for s in overlapping[:5]:
        msg += f"🏆 **{s}**\n"
    
    msg += "━━━━━━━━━━━━━━━━━━\n💡 제미니가 분석한 원본 화면입니다."

    screenshot_bio.seek(0)
    async with bot:
        await bot.send_photo(chat_id=CHAT_ID, photo=screenshot_bio, caption=msg, parse_mode='Markdown')

if __name__ == "__main__":
    asyncio.run(main())
