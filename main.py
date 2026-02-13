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
    
    # 1. 가상 브라우저 설정
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,2500") # 세로로 길게
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    
    today_list = []
    screenshot_bio = None
    
    try:
        url = "https://jusikai.com/"
        print("사이트 접속 및 촬영 중...")
        driver.get(url)
        time.sleep(8) # 로딩 대기
        
        png_data = driver.get_screenshot_as_png()
        screenshot_bio = BytesIO(png_data)
        image = Image.open(screenshot_bio)
        
        # 3. Gemini API 호출
        if GEMINI_API_KEY:
            print(f"Gemini 3 Pro Preview 호출 중...")
            genai.configure(api_key=GEMINI_API_KEY)
            
            # [사용자 요청 반영] 모델명을 gemini-3-pro-preview 로 설정
            target_model = 'gemini-3-pro-preview'
            
            try:
                model = genai.GenerativeModel(target_model)
                
                # Pro 모델의 성능을 끌어내기 위한 프롬프트
                prompt = """
                이 웹사이트 스크린샷을 분석해주세요.
                1. 화면에 보이는 '주식 종목명'(예: 삼성전자, 에코프로 등)을 모두 찾으세요.
                2. 메뉴 이름, 뉴스 제목, 지수 이름(KOSPI 등)은 제외하세요.
                3. 오직 종목명만 추출하여 쉼표(,)로 구분된 한 줄의 텍스트로 출력하세요.
                """
                
                response = model.generate_content([prompt, image])
                ai_text = response.text.strip()
                print(f"Gemini 응답: {ai_text}")
                
                raw_list = ai_text.split(',')
                today_list = [x.strip() for x in raw_list if x.strip()]
                # 한글 2자 이상만 필터링 (오류 텍스트 제거)
                today_list = [x for x in today_list if len(x) >= 2 and any(ord('가') <= ord(c) <= ord('힣') for c in x)]
                today_list = list(dict.fromkeys(today_list))[:25]
                
            except Exception as model_error:
                print(f"❌ 모델 호출 에러: {model_error}")
                print("⚠️ 404 에러가 뜬다면 모델명이 아직 공개되지 않은 것입니다. 아래 사용 가능한 목록을 참고하세요:")
                try:
                    for m in genai.list_models():
                        if 'generateContent' in m.supported_generation_methods:
                            print(f" - {m.name}")
                except: pass
                today_list = ["모델명_확인필요"]

        else:
            print("GEMINI_API_KEY가 없습니다.")
            today_list = ["API키_미설정"]

    except Exception as e:
        print(f"❌ 전체 에러: {e}")
        await bot.send_message(chat_id=CHAT_ID, text=f"⚠️ 오류 발생: {e}\n(사진은 전송합니다)")
    
    driver.quit()

    # 4. 데이터 저장
    today = (datetime.utcnow() + timedelta(hours=9)).strftime('%Y-%m-%d')
    if today_list and "확인필요" not in today_list[0] and "미설정" not in today_list[0]:
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
    msg = f"🧠 **[Gemini 3 Pro] AI 분석 리포트 ({today})**\n"
    msg += "━━━━━━━━━━━━━━━━━━\n"
    msg += f"📊 **지수 현황**\n{get_market()}\n"
    
    if today_list and "확인필요" not in today_list[0]:
        msg += "💎 **AI 포착 종목**\n"
        for s in today_list[:10]: msg += f" • {s}\n"
    else:
         msg += "⚠️ 종목 추출 실패 (로그 확인 필요)\n"
    
    msg += "\n🔥 **2~3일 연속 포착 주도주**\n"
    if not overlapping: msg += " (연속 포착 종목 없음)\n"
    for s in overlapping[:5]:
        msg += f"🏆 **{s}**\n"
    
    msg += "━━━━━━━━━━━━━━━━━━\n💡 원본 스크린샷을 확인하세요."

    if screenshot_bio:
        screenshot_bio.seek(0)
        async with bot:
            await bot.send_photo(chat_id=CHAT_ID, photo=screenshot_bio, caption=msg, parse_mode='Markdown')

if __name__ == "__main__":
    asyncio.run(main())
