import streamlit as st
import requests
from bs4 import BeautifulSoup
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# 페이지 기본 설정
st.set_page_config(page_title="Oddee 뉴스봇 대시보드", page_icon="📰", layout="centered")
st.title("📰 Oddee 뉴스봇 관리 대시보드")
st.write("최신 기사를 확인하고 내 메일로 바로 발송할 수 있는 뉴스 가공 봇입니다.")

# 1. 크롤링 함수 (st.cache_data를 사용해 빈번한 웹 요청 방지 및 속도 향상)
@st.cache_data(ttl=3600)  # 1시간 동안 캐시 유지
def fetch_oddee_news():
    url = "https://www.oddee.com/"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    try:
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        articles = []
        # oddee.com의 타이틀 구조에 맞게 셀렉터 설정 (실제 구조에 맞춰 변경 가능)
        for post in soup.select('.title a')[:5]: 
            articles.append({
                "title": post.text.strip(),
                "link": post['href']
            })
        return articles
    except Exception as e:
        st.error(f"데이터를 가져오는 중 오류가 발생했습니다: {e}")
        return []

# 2. 이메일 발송 함수
def send_newsletter(articles, receiver_email):
    # Streamlit Cloud의 Secrets나 로컬의 .title/secrets.toml에서 계정 정보 로드
    sender_email = st.secrets["email"]["sender"]
    sender_password = st.secrets["email"]["password"]
    
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

# --- UI 구현부 ---

# 기사 불러오기
articles_list = fetch_oddee_news()

if articles_list:
    st.subheader("🔥 현재 수집된 최신 기사 (Top 5)")
    # 수집된 기사를 Streamlit 화면에 깔끔하게 먼저 보여줌
    for idx, article in enumerate(articles_list, 1):
        st.markdown(f"{idx}. [{article['title']}]({article['link']})")
        
    st.divider()
    
    # 메일 수신 및 발송 제어
    st.subheader("📧 이메일 뉴스레터 발송")
    target_email = st.text_input("뉴스레터를 받을 이메일 주소를 입력하세요:", value="your_mail@example.com")
    
    if st.button("🚀 뉴스레터 지금 메일로 받기"):
        with st.spinner("메일을 발송 중입니다..."):
            success = send_newsletter(articles_list, target_email)
            if success:
                st.success(f"🎉 {target_email} 계정으로 성공적으로 발송되었습니다!")
else:
    st.warning("수집된 기사가 없습니다. 사이트 구조를 확인하거나 잠시 후 다시 시도해주세요.")
