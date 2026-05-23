import streamlit as st
import requests
from bs4 import BeautifulSoup
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# =================================================================
# 1. 페이지 기본 설정 및 제목
# =================================================================
st.set_page_config(page_title="Oddee 뉴스봇 대시보드", page_icon="📰", layout="centered")
st.title("📰 Oddee 뉴스봇 관리 대시보드")
st.write("최신 기사를 확인하고 내 메일로 바로 발송할 수 있는 뉴스 가공 봇입니다.")

# =================================================================
# 2. 업그레이드된 만능 크롤링 함수 (1시간 캐시 적용)
# =================================================================
@st.cache_data(ttl=3600)  
def fetch_oddee_news():
    url = "https://www.oddee.com/"
    # 크롬 브라우저와 동일한 헤더 설정 (봇 차단 우회)
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.encoding = response.apparent_encoding 
        
        soup = BeautifulSoup(response.text, 'html.parser')
        articles = []
        
        # 페이지 내의 모든 링크(a 태그)를 전수조사하는 만능 전략
        all_links = soup.find_all('a')
        
        for link_tag in all_links:
            if not link_tag.has_attr('href'):
                continue
                
            href = link_tag['href']
            title = link_tag.text.strip()
            
            # 불필요한 페이지 링크 제외 키워드
            skip_keywords = ['category', 'tag', 'about', 'contact', 'privacy', 'wp-admin', 'facebook', 'twitter', 'pinterest']
            
            # 조건 검사: 본인 도메인이면서 제목 글자 수가 15자 이상인 '진짜 기사' 후보 필터링
            if (href.startswith('https://www.oddee.com/') or href.startswith('/')) and len(title) > 15:
                if not any(kw in href.lower() for kw in skip_keywords):
                    
                    # 상대 경로일 경우 절대 경로로 보정
                    if href.startswith('/'):
                        href = f"https://www.oddee.com{href}"
                        
                    # 중복 주소 제외하고 수집
                    if href not in [a['link'] for a in articles]:
                        articles.append({"title": title, "link": href})
            
            if len(articles) >= 5:  # 최신 기사 5개만 수집 시 종료
                break
                
        return articles

    except Exception as e:
        st.error(f"크롤링 중 에러 발생: {e}")
        return []

# =================================================================
# 3. 이메일 발송 함수
# =================================================================
def send_newsletter(articles, receiver_email):
    # Streamlit Cloud의 Secrets 설정 창이나 로컬의 secrets.toml에서 정보를 가져옵니다.
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
    st.warning("수집된 기사가 없습니다. 사이트 구조를 확인하거나 아래 디버깅 모드를 켜보세요.")

st.divider()

# =================================================================
# 5. 개발자용 디버깅 툴 (연결 실패 원인 추적용)
# =================================================================
if st.checkbox("⚙️ 개발자용 디버깅 모드 켜기"):
    st.subheader("🛠️ 웹사이트 응답 상태 점검")
    try:
        test_res = requests.get("https://www.oddee.com/", headers={"User-Agent": "Mozilla/5.0"}, timeout=5)
        st.write(f"접속 상태 코드: `{test_res.status_code}` (200이면 정상)")
        
        test_soup = BeautifulSoup(test_res.text, 'html.parser')
        st.write("발견된 모든 링크(a 태그)의 텍스트 상위 10개 예시:")
        st.code([a.text.strip() for a in test_soup.find_all('a') if a.text.strip()][:10])
    except Exception as e:
        st.error(f"디버깅 연결 실패: {e}")
