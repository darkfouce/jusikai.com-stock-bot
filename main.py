import sys
import os
import traceback

print("🚀 [시작] 프로그램이 실행되었습니다.")

# 1. 라이브러리 테스트
try:
    import telegram
    import asyncio
    import requests
    from bs4 import BeautifulSoup
    print("✅ [성공] 라이브러리(도구)가 정상적으로 설치되었습니다.")
except ImportError as e:
    print(f"❌ [에러] 라이브러리 설치 실패! requirements.txt를 확인하세요.\n에러내용: {e}")
    sys.exit(1)

# 2. 비밀번호(Secrets) 테스트
TOKEN = os.environ.get('TELEGRAM_TOKEN')
CHAT_ID = os.environ.get('CHAT_ID')

if not TOKEN:
    print("❌ [에러] TELEGRAM_TOKEN이 없습니다! Settings -> Secrets 설정을 확인하세요.")
    sys.exit(1)
if not CHAT_ID:
    print("❌ [에러] CHAT_ID가 없습니다! Settings -> Secrets 설정을 확인하세요.")
    sys.exit(1)

print(f"✅ [성공] 비밀번호를 가져왔습니다. (ID 길이: {len(str(CHAT_ID))})")

# 3. 텔레그램 발송 테스트
async def send_debug_msg():
    print("📨 [연결] 텔레그램 발송 시도 중...")
    bot = telegram.Bot(token=TOKEN)
    
    try:
        # 가장 기본 메시지 보내기
        await bot.send_message(chat_id=CHAT_ID, text="🔔 [테스트] 이 메시지가 보이면 성공입니다!")
        print("🎉 [완료] 텔레그램 메시지 전송 성공! 핸드폰을 확인하세요.")
    except Exception as e:
        print("❌ [치명적 에러] 텔레그램 전송 실패!")
        print(f"에러 상세 내용: {e}")
        print("-" * 30)
        print("💡 [해결 힌트]")
        if "Unauthorized" in str(e):
            print("-> 토큰(TOKEN)이 틀렸습니다. 봇파더에게 다시 받으세요.")
        elif "Chat not found" in str(e) or "BadRequest" in str(e):
            print("-> CHAT_ID가 틀렸거나, 봇에게 먼저 말을 걸지 않았습니다.")
            print("-> 텔레그램 앱에서 봇에게 '/start'라고 말을 거세요.")
        else:
            print("-> 알 수 없는 오류입니다. 에러 내용을 복사해서 질문하세요.")
        print("-" * 30)
        sys.exit(1)

if __name__ == "__main__":
    try:
        asyncio.run(send_debug_msg())
    except Exception as total_error:
        print("☠️ [시스템 다운] 알 수 없는 이유로 프로그램이 꺼졌습니다.")
        traceback.print_exc()
        sys.exit(1)
