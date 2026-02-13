import sys
import os
import asyncio

# 1. 라이브러리 설치 확인
try:
    import requests
    from bs4 import BeautifulSoup
    import telegram
except ImportError as e:
    print(f"❌ [치명적 에러] 라이브러리가 설치되지 않았습니다: {e}")
    print("requirements.txt 파일에 오타가 있는지 확인해주세요.")
    sys.exit(1)

# 2. 환경변수(Secrets) 확인
TOKEN = os.environ.get('TELEGRAM_TOKEN')
CHAT_ID = os.environ.get('CHAT_ID')

async def main():
    print("🚀 봇 진단 시작...")
    
    # [체크 1] 텔레그램 설정 확인
    if not TOKEN or not CHAT_ID:
        print("❌ [에러] 텔레그램 토큰(TOKEN) 또는 아이디(CHAT_ID)가 없습니다.")
        print("GitHub Settings -> Secrets 메뉴에서 설정했는지 확인하세요.")
        return

    bot = telegram.Bot(token=TOKEN)

    # [체크 2] 텔레그램 연결 테스트
    try:
        # 일단 봇이 살아있는지 메시지부터 보냅니다.
        await bot.send_message(chat_id=CHAT_ID, text="🤖 [봇 생존신고] 시스템 점검을 시작합니다.")
        print("✅ 텔레그램 연결 성공")
    except Exception as e:
        print(f"❌ [에러] 텔레그램 전송 실패: {e}")
        print("토큰이 틀렸거나, 봇에게 말을 건 적이 없거나, CHAT_ID가 틀렸습니다.")
        return

    # [체크 3] 사이트 크롤링 테스트
    url = "https://jusikai.com/"
    print(f"🔍 {url} 접속 시도 중...")
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }

    try:
        res = requests.get(url, headers=headers, timeout=10)
        
        if res.status_code != 200:
            error_msg = f"❌ 사이트 접속 실패 (상태코드: {res.status_code})"
            print(error_msg)
            await bot.send_message(chat_id=CHAT_ID, text=error_msg)
            return
            
        soup = BeautifulSoup(res.text, 'html.parser')
        
        # 태그 찾기 시도 (여러 가지 경우의 수 대입)
        # 1순위: 랭킹 이름, 2순위: 일반적인 리스트, 3순위: 링크
        tags = soup.select('.ranking-stock-name') 
        if not tags:
            tags = soup.select('.stock-name')
        if not tags:
            tags = soup.select('li a') # 최후의 수단
            
        stocks = [t.text.strip() for t in tags if t.text.strip()]
        stocks = stocks[:10] # 10개만 가져오기

        if not stocks:
            fail_msg = "⚠️ 사이트 접속은 성공했으나, 종목명을 하나도 못 찾았습니다.\n(HTML 클래스 이름이 변경된 것 같습니다)"
            print(fail_msg)
            await bot.send_message(chat_id=CHAT_ID, text=fail_msg)
        else:
            success_msg = f"✅ 크롤링 성공!\n발견된 종목: {', '.join(stocks)}"
            print(success_msg)
            await bot.send_message(chat_id=CHAT_ID, text=success_msg)

    except Exception as e:
        err_msg = f"❌ 크롤링 도중 에러 발생: {e}"
        print(err_msg)
        await bot.send_message(chat_id=CHAT_ID, text=err_msg)

if __name__ == "__main__":
    asyncio.run(main())
