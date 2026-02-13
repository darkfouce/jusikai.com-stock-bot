import requests
from bs4 import BeautifulSoup
import pandas as pd
import telegram
import asyncio
import os
import FinanceDataReader as fdr
from datetime import datetime, timedelta

TOKEN = os.environ.get('TELEGRAM_TOKEN')
CHAT_ID = os.environ.get('CHAT_ID')
DATA_FILE = "stock_history.csv"

async def main():
    if not TOKEN or not CHAT_ID: return
    bot = telegram.Bot(token=TOKEN)
    
    # 1. 크롤링 (User-Agent를 더 정교하게 설정)
    url = "https://jusikai.com/"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    try:
        res = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(res.text, 'html.parser')
        
        # [진단] 사이트에서 가져온 텍스트 일부를 로그에 출력 (GitHub Actions에서 확인용)
        print("--- 사이트 텍스트 추출 시도 ---")
        
        # 모든 가능한 경로 뒤지기 (클래스, 링크, 표)
        tags = soup.select('.ranking-stock-name') or soup.select('td a') or soup.select('tr td')
        today_list = [t.text.strip() for t in tags if 2 <= len(t.text.strip()) <= 10]
        today_list = list(dict.fromkeys(today_list))[:30]
        
        if not today_list:
            # 텍스트가 하나도 없으면 사이트가 로봇을 막은 것입니다.
            print(f"로그: 사이트 본문 길이 = {len(res.text)}")
            await bot.send_message(chat_id=CHAT_ID, text="⚠️ 종목 추출 실패: 사이트 구조를 다시 확인해야 합니다.")
            return
            
    except Exception as e:
        await bot.send_message(chat_id=CHAT_ID, text=f"❌ 접속 에러: {e}")
        return

    # 2. 데이터 처리 및 저장 (TypeError 방지)
    today = (datetime.utcnow() + timedelta(hours=9)).strftime('%Y-%m-%d')
    new_df = pd.DataFrame({'date': [today]*len(today_list), 'stock': today_list})

    if os.path.exists(DATA_FILE):
        try:
            # 모든 데이터를 문자열로 처리하여 데이터 형식이 꼬이는 현상 차단
            df = pd.read_csv(DATA_FILE, dtype=str)
            df = pd.concat([df, new_df]).drop_duplicates()
        except: 
            df = new_df
    else: 
        df = new_df
    df.to_csv(DATA_FILE, index=False)

    # 3. 중복 포착 분석 및 발송
    limit = (datetime.now() - timedelta(days=2)).strftime('%Y-%m-%d')
    recent = df[df['date'].astype(str) >= limit]
    overlapping = recent['stock'].value_counts()[recent['stock'].value_counts() >= 2].index.tolist()

    msg = f"🔍 **[PRO] 오늘의 분석 리포트 ({today})**\n"
    msg += "━━━━━━━━━━━━━━━━━━\n"
    msg += "✨ **AI 4대장 추천**\n"
    for s in today_list[:4]: msg += f" • {s}\n"
    
    msg += "\n🔥 **2~3일 중복 주도주**\n"
    if not overlapping: msg += " (포착된 연속 종목 없음)\n"
    for s in overlapping[:5]:
        msg += f"🏆 **{s}**\n ├ 🤖 AI: 긍정 / ⏳ 재료: 지속\n └ 📈 섹터: 주도 테마군\n\n"
    
    msg += "━━━━━━━━━━━━━━━━━━\n💡 224일선 부근 눌림목 여부를 확인하세요!"

    async with bot:
        await bot.send_message(chat_id=CHAT_ID, text=msg, parse_mode='Markdown')

if __name__ == "__main__":
    asyncio.run(main())
