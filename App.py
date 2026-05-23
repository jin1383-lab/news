import streamlit as st
import requests
from bs4 import BeautifulSoup
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import feedparser
from mtranslate import translate

# =================================================================
# 1. 페이지 기본 설정 및 제목
# =================================================================
st.set_page_config(page_title="Oddee 뉴스봇 대시보드", page_icon="📰", layout="centered")
st.title("📰 Oddee 뉴스봇 관리 대시보드")
st.write("최신 영어 기사를 수집하고 한글 번역까지 곁들여 메일로 발송하는 봇입니다.")

# =================================================================
# 2. RSS 피드 수집 및 번역 함수 (1시간 캐시)
# =================================================================
@st.cache_data(ttl=3600)  
def fetch_oddee_news():
    url = "https://www.oddee.com/feed/"
    
    try:
        # feedparser를 이용해 차단 없이 RSS 피드 수집
        feed = feedparser.parse(url)
        
        if not feed.entries:
            st.error("⚠️ RSS 피드 데이터를 읽어오지 못했습니다. 사이트 서버 상태를 확인해 주세요.")
            return []
            
        articles = []
        
        # 기사 수집 및 실시간 한글 번역 진행
        for entry in feed.entries:
            raw_title = entry.get("title", "No Title").strip()
            link = entry.get("link", "https://www.oddee.com/").strip()
            
            # 구글 번역기를 이용해 영어(en)를 한글(ko)로 실시간 번역
            try:
                translated_title = translate(raw_title, "ko", "en")
                # 요구하신 대로 원래 영어 제목 뒤 괄호 안에 번역본을 결합합니다.
                full_title = f"{raw_title} ({translated_title})"
            except Exception:
                # 번역 도중 에러가 나면 영어 제목만 유지
                full_title = raw_title
            
            # 중복 데이터 검사 후 추가
            if link not in [a['link'] for a in articles]:
                articles.append({"title": full_title, "link": link})
            
            if len(articles) >= 5:  # 최신 기사 5개만 수집
                break
                
        return articles

    except Exception as e:
        st.error(f"🚨 뉴스 피드 해석 및 번역 중 에러 발생: {e}")
        st.info("💡 팁: requirements.txt 파일에 라이브러리들이 정상적으로 추가되었는지 확인해 주세요.")
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
    msg['Subject'] = "📰 [Oddee] 오늘의 흥미로운 번역 뉴스레터"
    msg['From'] = sender_email
    msg['To'] = receiver_email
    
    html = "<h3>오늘 배달된 최신 번역 기사입니다.</h3><ul>"
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

# 기사 데이터 가져오기 (영어 + 한글 번역 결합 완료 상태)
articles_list = fetch_oddee_news()

if articles_list:
    st.subheader("🔥 현재 수집 및 번역 완료된 최신 기사 (Top 5)")
    for idx, article in enumerate(articles_list, 1):
        st.markdown(f"{idx}. [{article['title']}]({article['link']})")
        
    st.divider()
    
    st.subheader("📧 이메일 뉴스레터 발송")
    target_email = st.text_input("뉴스레터를 받을 이메일 주소를 입력하세요:", value="your_mail@example.com")
    
    if st.button("🚀 번역 뉴스레터 지금 메일로 받기"):
        with st.spinner("번역된 메일을 발송 중입니다..."):
            success = send_newsletter(articles_list, target_email)
            if success:
                st.success(f"🎉 {target_email} 계정으로 성공적으로 발송되었습니다!")
else:
    st.warning("수집된 기사가 없습니다. 라이브러리가 빌드 중이거나 동기화 중일 수 있으니 잠시 후 새로고침해 주세요.")

st.divider()

# =================================================================
# 5. 개발자용 디버깅 툴
# =================================================================
if st.checkbox("⚙️ 개발자용 번역 상태 점검"):
    st.subheader("🛠️ 번역 모듈 테스트")
    try:
        test_text = "10 Bizarre Facts You Didn't Know About the World"
        translated_test = translate(test_text, "ko", "en")
        st.write(f"원본 영어: `{test_text}`")
        st.write(f"번역 결과: `{translated_test}`")
    except Exception as e:
        st.error(f"번역 테스트 실패: {e}")
