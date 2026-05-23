import streamlit as st
import requests
from bs4 import BeautifulSoup
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import json

# =================================================================
# 1. 페이지 기본 설정 및 제목
# =================================================================
st.set_page_config(page_title="Oddee 뉴스봇 대시보드", page_icon="📰", layout="centered")
st.title("📰 Oddee 뉴스봇 관리 대시보드")
st.write("최신 기사를 확인하고 내 메일로 바로 발송할 수 있는 뉴스 가공 봇입니다.")

# =================================================================
# 2. [우회 완료] 프록시 API를 활용한 RSS 피드 크롤링 함수 (1시간 캐시)
# =================================================================
@st.cache_data(ttl=3600)  
def fetch_oddee_news():
    # Streamlit IP 차단을 뚫기 위해 무료 우회 프록시 API 서버를 경유합니다.
    target_url = "https://www.oddee.com/feed/"
    proxy_url = f"https://api.allorigins.win/get?url={requests.utils.quote(target_url)}"
    
    try:
        response = requests.get(proxy_url, timeout=15)
        
        if response.status_code != 200:
            st.error(f"⚠️ 우회 서버 응답 실패 (상태 코드: {response.status_code})")
            return []
            
        # AllOrigins API는 데이터를 JSON 형태 내부의 'contents'에 담아줍니다.
        json_data = response.json()
        xml_content = json_data.get("contents", "")
        
        # XML 데이터를 해석하기 위해 BeautifulSoup과 lxml 파서 사용
        soup = BeautifulSoup(xml_content, 'xml')
        articles = []
        
        # RSS 피드 내부에서 각 기사를 뜻하는 <item> 태그 추출
        items = soup.find_all('item')
        
        for item in items:
            title_tag = item.find('title')
            link_tag = item.find('link')
            
            if title_tag and link_tag:
                title = title_tag.text.strip()
                link = link_tag.text.strip()
                
                # 중복 데이터 검사 후 추가
                if link not in [a['link'] for a in articles]:
                    articles.append({"title": title, "link": link})
            
            if len(articles) >= 5:  # 최신 기사 5개만 수집
                break
                
        return articles

    except Exception as e:
        st.error(f"🚨 피드 우회 수집 중 에러 발생: {e}")
        st.info("💡 팁: requirements.txt 파일에 'lxml'이 정상적으로 추가되었는지 확인해 주세요.")
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
    st.warning("수집된 기사가 없습니다. 라이브러리 빌드 중이거나 우회 서버 연결을 확인 중입니다.")

st.divider()

# =================================================================
# 5. 개발자용 디버깅 툴 (우회 서버 작동 확인용)
# =================================================================
if st.checkbox("⚙️ 개발자용 디버깅 모드 켜기"):
    st.subheader("🛠️ 프록시 우회 상태 점검")
    try:
        t_url = "https://www.oddee.com/feed/"
        p_url = f"https://api.allorigins.win/get?url={requests.utils.quote(t_url)}"
        test_res = requests.get(p_url, timeout=10)
        st.write(f"우회 서버 응답 코드: `{test_res.status_code}` (200이면 프록시 우회 성공!)")
        
        js = test_res.json()
        inner_content = js.get("contents", "")
        test_soup = BeautifulSoup(inner_content, 'xml')
        st.write("우회 통로를 통해 받아온 최신 타이틀 샘플:")
        st.code([t.text.strip() for t in test_soup.find_all('title')[:4]])
    except Exception as e:
        st.error(f"디버깅 연결 실패: {e}")
