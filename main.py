import telegram
import asyncio
import os
import sys

# 환경변수 가져오기
TOKEN = os.environ.get('TELEGRAM_TOKEN')
CHAT_ID = os.environ.get('CHAT_ID')

async def force_send():
    print("🚀 [테스트] 텔레그램 강제 발송 시작")
    
    # 1. 토큰/ID 확인
    if not TOKEN:
        print("❌ [실패] TELEGRAM_TOKEN이 설정되지 않았습니다.")
        sys.exit(1)
    if not CHAT_ID:
        print("❌ [실패] CHAT_ID가 설정되지 않았습니다.")
        sys.exit(1)
        
    print(f"ℹ️ 설정된 CHAT_ID: {CHAT_ID} (맞는지 확인하세요)")

    # 2. 메시지 전송 시도
    bot = telegram.Bot(token=TOKEN)
    
    try:
        await bot.send_message(chat_id=CHAT_ID, text="🔔 [테스트] 이 메시지가 보이면 성공입니다!")
        print("✅ [성공] 텔레그램 메시지를 보냈습니다! 핸드폰을 확인하세요.")
    except telegram.error.Unauthorized:
        print("❌ [실패] 봇이 차단되었습니다. 텔레그램 앱에서 봇에게 '/start'를 입력했는지 확인하세요.")
        sys.exit(1)
    except telegram.error.BadRequest:
        print("❌ [실패] CHAT_ID가 틀렸습니다. 내 ID가 맞는지 다시 확인하세요.")
        sys.exit(1)
    except Exception as e:
        print(f"❌ [에러] 알 수 없는 오류: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(force_send())
