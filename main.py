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
    
    # 1. 가상 브라우저 설정 (화면 크게)
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,2500") # 세로로 더 길게
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    
    today_list = []
    screenshot_bio = None
    
    try:
        url = "https://jusikai.com/"
        print("사이트 접속 및 촬영 중...")
        driver.get(url)
        time.sleep(10) # Thinking 모드는 분석 시간이 필요하므로 로딩도 넉넉히
        
        png_data = driver.get_screenshot_as_png()
        screenshot_bio = BytesIO(png_data)
        image = Image.open(screenshot_bio)
        
        # 3. Gemini Thinking Mode 호출
        if GEMINI_API_KEY:
            print("Gemini Thinking Mode (사고 모드) 가동 중...")
            genai.configure(api_key=GEMINI_API_KEY)
            
            # [최종 수정] 현존하는 유일한 사고 모델 (Gemini 2.0 Flash Thinking)
            target_model = 'gemini-2.0-flash-thinking-exp-01-21'
            
            try:
                model = genai.GenerativeModel(target_model)
                
                # 사고 과정을 유도하는 프롬프트
                prompt = """
                이 이미지의 내용을 단계별로 생각하며 분석해(Think step-by-step).
                1. 이것은 주식 정보 사이트야. 화면에서 주식 종목 이름들이 나열된 곳을 찾아.
                2. 메뉴(로그인, 공지사항)나 지수(KOSPI, KOSDAQ)는 무시해.
                3. 오직 '개별 종목명'만 추출해. (예: 삼성전자, 알테오젠, 에코프로 등)
                4. 추출한 종목명들을 쉼표(,)로 구분해서 한 줄로 출력해. 설명은 필요 없어.
                """
                
                response = model.generate_content([prompt, image])
                ai_text = response.text.strip()
                print(f"사고 모드 분석 결과: {ai_text}")
                
                # 결과 정제
                raw_list = ai_text.split(',')
                today_list = [x.strip() for x in raw_list if x.strip()]
                # 한글 2자 이상인 것만 필터링 (사고 과정 텍스트 제거용)
                today_list = [x for x in today_list if len(x) >= 2 and any(ord('가') <= ord(c) <= ord('힣') for c in x)]
                today_list = list(dict.fromkeys(today_list))[:25]
                
            except Exception as model_error:
                print(f"❌ 모델 호출 실패: {model_error}")
                today_list = ["모델_오류_로그확인"]

        else:
            print("GEMINI_API_KEY가 없습니다.")
            today_list = ["API키_미설정"]

    except Exception as e:
        print(f"❌ 전체 에러: {e}")
        await bot.send_message(chat_id=CHAT_ID, text=f"⚠️ 오류 발생: {e}\n(사진은 전송합니다)")
    
    driver.quit()

    # 4. 데이터 저장
    today = (datetime.utcnow() + timedelta(hours=9)).strftime('%Y-%m-%d')
    if today_list and "오류" not in today_list[0] and "미설정" not in today_list[0]:
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

    # 5. 리포트 전송
    msg = f"🧠 **[Thinking Mode] AI 심층 분석 리포트 ({today})**\n"
    msg += "━━━━━━━━━━━━━━━━━━\n"
    msg += f"📊 **지수 현황**\n{get_market()}\n"
    
    if today_list and "오류" not in today_list[0]:
        msg += "💎 **AI 포착 종목**\n"
        for s in today_list[:10]: msg += f" • {s}\n"
    else:
         msg += "⚠️ 종목 추출 실패 (로그 확인 필요)\n"
    
    msg += "\n🔥 **2~3일 연속 포착 주도주**\n"
    if not overlapping: msg += " (연속 포착 종목 없음)\n"
    for s in overlapping[:5]:
        msg += f"🏆 **{s}**\n"
    
    msg += "━━━━━━━━━━━━━━━━━━\n💡 사고 모드(Thinking Mode)가 분석한 화면입니다."

    if screenshot_bio:
        screenshot_bio.seek(0)
        async with bot:
            await bot.send_photo(chat_id=CHAT_ID, photo=screenshot_bio, caption=msg, parse_mode='Markdown')

if __name__ == "__main__":
    asyncio.run(main())
