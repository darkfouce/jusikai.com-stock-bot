import os
import sys

print("🚀 [1단계] 스크립트 시작")

# 1. 라이브러리 임포트 테스트
try:
    import requests
    from bs4 import BeautifulSoup
    import pandas as pd
    import telegram
    import asyncio
    print("✅ 라이브러리 불러오기 성공")
except ImportError as e:
    print(f"❌ [에러] 라이브러리가 설치되지 않았습니다: {e}")
    print("requirements.txt 파일을 확인해주세요.")
    sys.exit(1)

# 2. 환경변수(Secrets) 확인
TOKEN = os.environ.get('TELEGRAM_TOKEN')
CHAT_ID = os.environ.get('CHAT_ID')

if not TOKEN or not CHAT_ID:
    print("❌ [에러] 텔레그램 설정(Secrets)이 없습니다!")
    print("GitHub Settings -> Secrets and variables -> Actions에 TELEGRAM_TOKEN과 CHAT_ID가 있는지 확인하세요.")
    sys.exit(1) # 여기서 강제 종료
else:
    print("✅ 환경변수(Secrets) 확인 완료")

# 3. 크롤링 테스트
TARGET_URL = "https://jusikai.com/"
print(f"🔍 [2단계] {TARGET_URL} 접속 시도...")

try:
    headers = {'User-Agent': 'Mozilla/5.0'}
    response = requests.get(TARGET_URL, headers=headers, timeout=10)
    
    if response.status_code != 200:
        print(f"❌ [에러] 사이트 접속 실패. 상태 코드: {response.status_code}")
        sys.exit(1)
        
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # 여기서 태그를 찾아봅니다.
    print("🧩 HTML 태그 찾는 중...")
    
    # [수정 포인트] 사이트 구조에 맞는 태그인지 확인
    tags = soup.select('.ranking-stock-name') 
    
    if not tags:
        print("⚠️ [경고] '.ranking-stock-name' 태그를 하나도 못 찾았습니다.")
        print("사이트가 자바스크립트로 로딩되거나, 클래스 이름이 바뀌었을 수 있습니다.")
        print("--- HTML 일부분 출력 (디버깅용) ---")
        print(soup.prettify()[:500]) # HTML 앞부분 500자만 출력해서 확인
        print("--------------------------------")
        # 태그를 못 찾아도 일단 텔레그램 테스트를 위해 넘어갑니다.
        stocks = ["테스트종목1", "테스트종목2"] 
    else:
        stocks = [t.text.strip() for t in tags]
        print(f"✅ 크롤링 성공: {len(stocks)}개 발견 -> {stocks[:3]}...")

except Exception as e:
    print(f"❌ [에러] 크롤링 중 문제 발생: {e}")
    sys.exit(1)

# 4. 텔레그램 전송 테스트
print("📨 [3단계] 텔레그램 전송 시도...")

async def send_test_msg():
    bot = telegram.Bot(token=TOKEN)
    try:
        await bot.send_message(chat_id=CHAT_ID, text="🤖 [테스트] 봇이 정상 작동 중입니다! (에러 해결됨)")
        print("✅ 텔레그램 전송 성공!")
    except Exception as e:
        print(f"❌ [에러] 텔레그램 전송 실패: {e}")
        print("토큰이 틀렸거나, CHAT_ID가 잘못되었거나, 봇에게 말을 건 적이 없는 경우입니다.")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(send_test_msg())
    print("🎉 모든 테스트 통과!")
