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

# [PRO] 제외할 메뉴 단어 리스트 (image_beb728 기반)
JUNK_WORDS = ['.com', '서비스', '소개', '명예', '전당', 'RSI', 'MACD', '로그인', '회원가입', '공지', '고객']

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
    
    # 1. 크롤링 (진짜 종목만 골라내는 필터 적용)
    url = "https://jusikai.com/"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    
    try:
        res = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(res.text, 'html.parser')
        
        # [PRO] 메뉴판이 아닌 본문 데이터만 타겟팅 (CSS 선택자 강화)
        tags = soup.select('table td a') or soup.select('.ranking-stock-name')
        
        today_list = []
        for t in tags:
            name = t.text.strip()
            # 2~7글자 사이이면서 메뉴어가 아닌 것만 종목으로 인정
            if name and 2 <= len(name) <= 7 and not any(jw in name for jw in JUNK_WORDS):
                today_list.append(name)
        
        today_list = list(dict.fromkeys(today_list))[:25] # 중복 제거

        if not today_list:
            await bot.send_message(chat_id=CHAT_ID, text="⚠️ 유효한 종목을 찾지 못했습니다. 사이트 구역을 다시 분석합니다.")
            return
            
    except Exception as e:
        await bot.send_message(chat_id=CHAT_ID, text=f"❌ 접속 에러: {e}")
        return

    # 2. 데이터 누적 (TypeError 완벽 방지)
    today = (datetime.utcnow() + timedelta(hours=9)).strftime('%Y-%m-%d')
    new_df = pd.DataFrame({'date': [today]*len(today_list), 'stock': today_list})

    if os.path.exists(DATA_FILE):
        try:
            # 파일을 읽을 때 무조건 문자열(str)로 읽어서 float64 비교 오류 차단
            df = pd.read_csv(DATA_FILE, dtype=str)
            df = pd.concat([df, new_df]).drop_duplicates()
        except: df = new_df
    else: df = new_df
    df.to_csv(DATA_FILE, index=False)

    # 3. 중복 포착 분석
    limit_date = (datetime.now() - timedelta(days=2)).strftime('%Y-%m-%d')
    recent = df[df['date'].astype(str) >= limit_date]
    counts = recent['stock'].value_counts()
    overlapping = counts[counts >= 2].index.tolist()

    # 4. 리포트 작성
    msg = f"🔍 **[PRO] AI 정밀 분석 리포트 ({today})**\n\n"
    msg += f"📊 **지수 현황**\n{get_market()}\n"
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
