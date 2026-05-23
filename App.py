import streamlit as st
import requests
from bs4 import BeautifulSoup
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import feedparser

# =================================================================
# 1. 페이지 기본 설정 및 제목
# =================================================================
st.set_page_config(page_title="Oddee 뉴스봇 대시보드", page_icon="📰", layout="centered")
st.title("📰 Oddee 뉴스봇 관리 대시보드")
st.write("최신 기사를 확인하고 내 메일로 바로 발송할 수 있는 뉴스 가공 봇입니다.")

# =================================================================
# 2. [안정성 극대화] feedparser를 활용한 RSS 피드 수집 함수 (1시간 캐시)
# =================================================================
@st.cache_data(ttl=3600)  
def fetch_oddee_news():
    url = "https://www.oddee.com/feed/"
    
    try:
        # feedparser는 자체적으로 브라우저 위장 기능 및 차단 우회 알고리즘을 내장하고 있습니다.
        feed = feedparser.parse(url)
        
        # 만약 feedparser 응답에 에러가 있거나 데이터가 비어있을 경우 예외 처리
        if not feed.entries:
            st.error("⚠️ RSS 피드 데이터를 읽어오지 못했습니다. 사이트 서버 상태를 확인해 주세요.")
            return []
            
        articles = []
        
        # feed.entries 안에는 최신 기사들이 순서대로 담겨 있습니다.
        for entry in feed.entries:
            title = entry.get("title", "No Title").strip()
            link = entry.get("link", "https://www.oddee.com/").strip()
            
            # 중복 데이터 검사 후 추가
            if link not in [a['link'] for a in articles]:
                articles.append({"title": title, "link": link})
            
            if len(articles) >= 5:  # 최신 기사 5개만 수집
                break
                
        return articles

    except Exception as e:
        st.error(f"🚨 뉴스 피드 해석 중 에러 발생: {e}")
        st.info("💡 팁: requirements.txt 파일에 'feedparser'가 정상적으로 추가되었는지 확인해 주세요.")
        return []

# =================================================================
# 3. 이메일 발송 함수
# =================================================================
def send_newsletter(articles, receiver_email):
    try:
        sender_email = st.secrets["email"]["sender"]
        sender_password = st.secrets["email"]["password"]
    except KeyError:
        st.error("🔒 Streamlit Secrets에 이메일 정보(email.sender, email.password)가 설정되지 않았습니다.")
        return False
    
    msg = MIMEMultipart('alternative')
    msg['Subject'] = "📰 [Oddee] 오늘의 흥미로운 최신 뉴스"
    msg['From'] = sender_email
    msg['To'] = receiver_email
    
    html = "<h3>오늘 배달된 최신 기사입니다.</h3><ul>"
    for art in articles:
        html += f"<li><a href='{art['link']}'>{art['title']}</a></li>"
    html += "</ul>"
    
    msg.attach(MIMEText(html, 'html'))
    
    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, receiver_email, msg.as_string())
        return True
    except Exception as e:
        st.error(f"메일 발송 실패: {e}")
        return False

# =================================================================
# 4. 화면 UI 렌더링 부
# =================================================================

# 기사 데이터 가져오기
articles_list = fetch_oddee_news()

if articles_list:
    st.subheader("🔥 현재 수집된 최신 기사 (Top 5)")
    for idx, article in enumerate(articles_list, 1):
        st.markdown(f"{idx}. [{article['title']}]({article['link']})")
        
    st.divider()
    
    st.subheader("📧 이메일 뉴스레터 발송")
    target_email = st.text_input("뉴스레터를 받을 이메일 주소를 입력하세요:", value="your_mail@example.com")
    
    if st.button("🚀 뉴스레터 지금 메일로 받기"):
        with st.spinner("메일을 발송 중입니다..."):
            success = send_newsletter(articles_list, target_email)
            if success:
                st.success(f"🎉 {target_email} 계정으로 성공적으로 발송되었습니다!")
else:
    st.warning("수집된 기사가 없습니다. 라이브러리가 빌드 중이거나 동기화 중일 수 있으니 잠시 후 새로고침해 주세요.")

st.divider()

# =================================================================
# 5. 개발자용 디버깅 툴
# =================================================================
if st.checkbox("⚙️ 개발자용 디버깅 모드 켜기"):
    st.subheader("🛠️ Feedparser 파싱 상태 점검")
    try:
        debug_feed = feedparser.parse("https://www.oddee.com/feed/")
        st.write(f"피드 내부 상태 코드: `{debug_feed.get('status', 'N/A')}`")
        st.write(f"가져온 기사 총 개수: `{len(debug_feed.entries)}`개")
        if debug_feed.entries:
            st.write("피드 첫 번째 기사 제목 예시:")
            st.code(debug_feed.entries[0].get("title"))
    except Exception as e:
        st.error(f"디버깅 연결 실패: {e}")
