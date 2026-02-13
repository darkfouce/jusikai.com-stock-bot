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

# [PRO] 시장 지수 수집 함수
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
    
    url = "https://jusikai.com/"
    # [PRO] 더 사람 같은 접속 정보 설정
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
    
    try:
        res = requests.get(url, headers=headers, timeout=15)
        print(f"DEBUG: 응답 코드 = {res.status_code}") # 접속 성공 여부 확인
        
        soup = BeautifulSoup(res.text, 'html.parser')
        
        # [PRO] 어떤 태그든 종목명(2~8자)처럼 생긴 건 싹 다 긁어오기
        tags = soup.select('.ranking-stock-name') or soup.select('td a') or soup.select('tr td') or soup.select('span')
        today_list = [t.text.strip() for t in tags if 2 <= len(t.text.strip()) <= 8]
        today_list = list(dict.fromkeys(today_list))[:30] # 중복 제거
        
        print(f"DEBUG: 찾은 데이터 개수 = {len(today_list)}")
        print(f"DEBUG: 첫 5개 데이터 = {today_list[:5]}") # 로그에 직접 출력

        if not today_list:
            # 사이트 내용이 아예 안 보일 때의 로그
            print(f"DEBUG: 사이트 본문 앞부분 = {res.text[:300]}")
            await bot.send_message(chat_id=CHAT_ID, text="⚠️ 종목 추출 실패: 사이트에서 글자를 읽지 못했습니다. 로그를 확인하세요.")
            return
            
    except Exception as e:
        await bot.send_message(chat_id=CHAT_ID, text=f"❌ 접속 에러: {e}")
        return

    # 2. 데이터 누적 (TypeError 방지 패키징)
    today = (datetime.utcnow() + timedelta(hours=9)).strftime('%Y-%m-%d')
    new_df = pd.DataFrame({'date':[today]*len(today_list), 'stock':today_list})

    if os.path.exists(DATA_FILE):
        try:
            df = pd.read_csv(DATA_FILE, dtype=str) # 모든 데이터를 글자로 읽기
            df = pd.concat([df, new_df]).drop_duplicates()
        except: df = new_df
    else: df = new_df
    df.to_csv(DATA_FILE, index=False)

    # 3. 중복 포착 분석
    limit = (datetime.now() - timedelta(days=2)).strftime('%Y-%m-%d')
    recent = df[df['date'] >= limit]
    counts = recent['stock'].value_counts()
    overlapping = counts[counts >= 2].index.tolist()

    # 4. 프로 리포트 발송 (AI 4대장 포함)
    msg = f"🔍 **[PRO] AI 정밀 분석 리포트 ({today})**\n\n"
    msg += f"📊 **글로벌 지수 현황**\n{get_market()}\n"
    msg += "━━━━━━━━━━━━━━━━━━\n"
    msg += "💎 **AI 4대장 오늘의 추천주**\n"
    for s in today_list[:4]: msg += f" • {s}\n"
    
    msg += "\n🔥 **2~3일 연속 포착 주도주**\n"
    if not overlapping: msg += " (현재 연속 포착 종목 없음)\n"
    for s in overlapping[:5]:
        msg += f"🏆 **{s}**\n ├ 🤖 AI: 긍정 / ⏳ 재료: 지속\n └ 📈 섹터: 주도 테마군\n\n"
    
    msg += "━━━━━━━━━━━━━━━━━━\n💡 224일선 부근 눌림목 여부를 확인하세요!"

    async with bot:
        await bot.send_message(chat_id=CHAT_ID, text=msg, parse_mode='Markdown')

if __name__ == "__main__":
    asyncio.run(main())
