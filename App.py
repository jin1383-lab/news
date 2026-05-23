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
st.set_page_config(page_title="글로벌 기묘한 뉴스 봇", page_icon="👽", layout="centered")
st.title("👽 글로벌 기묘한 뉴스 종합 대시보드")
st.write("전 세계의 가십, 미스터리, 신기한 뉴스를 한곳에 모아 번역해 드립니다.")

# =================================================================
# 2. [최신 반영] 사이트별 RSS 피드 주소 매핑 딕셔너리
# =================================================================
SITE_CONFIG = {
    "Oddee (기묘한 이야기)": {
        "most_viewed": "https://www.oddee.com/feed/",
        "trending": "https://www.oddee.com/feed/?orderby=date",
        "popular": "https://www.oddee.com/feed/?orderby=comment_count"
    },
    "Listverse (탑 10 미스터리)": {
        "most_viewed": "https://listverse.com/feed/",
        "trending": "https://listverse.com/feed/?paged=1",
        "popular": "https://listverse.com/feed/"
    },
    "Mental Floss (지식/상식 가십)": {
        "most_viewed": "https://www.mentalfloss.com/api/rss/all",
        "trending": "https://www.mentalfloss.com/api/rss/all",
        "popular": "https://www.mentalfloss.com/api/rss/all"
    },
    "UPI Odd News (실시간 황당 뉴스)": {
        "most_viewed": "https://rss.upi.com/news/odd_news.rss",
        "trending": "https://rss.upi.com/news/odd_news.rss",
        "popular": "https://rss.upi.com/news/odd_news.rss"
    },
    "News of the Weird (세상에 이런일이)": {
        "most_viewed": "https://www.uexpress.com/feed/oddities/news-of-the-weird",
        "trending": "https://www.uexpress.com/feed/oddities/news-of-the-weird",
        "popular": "https://www.uexpress.com/feed/oddities/news-of-the-weird"
    }
}

# =================================================================
# 3. [철벽 우회] requests 데이터 주입 방식 크롤링 함수 (1시간 캐시)
# =================================================================
@st.cache_data(ttl=3600)  
def fetch_news_by_site(site_name, sort_type):
    url = SITE_CONFIG[site_name].get(sort_type, "https://www.oddee.com/feed/")
    
    # 윈도우 11 크롬 브라우저와 100% 똑같은 유저 에이전트 및 통신 승인용 헤더 세팅
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7"
    }
    
    try:
        # Step 1: feedparser를 바로 쓰지 않고, 강력한 requests 라이브러리로 방화벽을 먼저 깨부숩니다.
        response = requests.get(url, headers=headers, timeout=12)
        
        # Step 2: 받아온 가공 전의 깨끗한 문자열 데이터를 feedparser에 강제로 밀어 넣어 해석시킵니다.
        feed = feedparser.parse(response.content)
            
        if not feed.entries:
            return []
            
        articles = []
        
        for entry in feed.entries:
            raw_title = entry.get("title", "").strip()
            link = entry.get("link", "").strip()
            
            # 주소 유실 대비 보정 (id 태그나 guid 태그 확인)
            if not link and entry.get("id"):
                link = entry.get("id").strip()
            if not link and entry.get("guid"):
                link = entry.get("guid").strip()
                
            if not raw_title or not link:
                continue
                
            # 실시간 구글 한글 번역
            try:
                translated_title = translate(raw_title, "ko", "en")
                full_title = f"{raw_title} ({translated_title})"
            except Exception:
                full_title = raw_title
            
            # 중복 데이터 검사
            if link not in [a['link'] for a in articles]:
                articles.append({"title": full_title, "link": link})
            
            if len(articles) >= 5:  # 상위 5개 수집 완료 시 리턴
                break
                
        return articles

    except Exception as e:
        # 배포 로그 점검용 에러 기록
        st.sidebar.error(f"⚠️ {site_name} 연결 세부 실패 사유: {e}")
        return []

# =================================================================
# 4. 통합 이메일 발송 함수
# =================================================================
def send_combined_newsletter(site_name, data_dict, receiver_email):
    try:
        sender_email = st.secrets["email"]["sender"]
        sender_password = st.secrets["email"]["password"]
    except KeyError:
        st.error("🔒 Streamlit Secrets에 이메일 정보가 설정되지 않았습니다.")
        return False
    
    msg = MIMEMultipart('alternative')
    msg['Subject'] = f"📰 [{site_name} 뉴스레터] 오늘의 신기한 세계 소식"
    msg['From'] = sender_email
    msg['To'] = receiver_email
    
    html = f"<h2>오늘의 {site_name} 종합 뉴스레터</h2>"
    html += "<p>해외 사이트의 핫한 기사들을 한글 번역과 함께 전해드립니다.</p><br>"
    
    for category, articles in data_dict.items():
        html += f"<h3 style='color: #4b86ff;'>✨ {category} Top 5</h3><ul>"
        if articles:
            for art in articles:
                html += f"<li><a href='{art['link']}'>{art['title']}</a></li>"
        else:
            html += "<li>현재 수집된 기사가 없습니다.</li>"
        html += "</ul><br>"
    
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
# 5. 화면 UI 렌더링 부
# =================================================================

selected_site = st.selectbox(
    "🌐 탐색할 해외 뉴스 사이트를 선택하세요:",
    list(SITE_CONFIG.keys())
)

st.divider()

# 선택된 사이트의 데이터 동시 수집 및 번역 실행
with st.spinner(f"{selected_site}에서 뉴스를 안전하게 가져와 번역 중입니다..."):
    most_viewed_news = fetch_news_by_site(selected_site, 'most_viewed')
    trending_news = fetch_news_by_site(selected_site, 'trending')
    popular_news = fetch_news_by_site(selected_site, 'popular')

# 이메일 전송용 묶음 데이터
combined_data = {
    "Most Viewed 코너": most_viewed_news,
    "Trending 코너": trending_news,
    "Popular 코너": popular_news
}

# 탭 구조화
tab1, tab2, tab3 = st.tabs(["🔥 Most Viewed", "⚡ Trending", "💬 Popular"])

with tab1:
    st.subheader(f"📊 {selected_site} - 상위 노출 뉴스")
    if most_viewed_news:
        for idx, art in enumerate(most_viewed_news, 1):
            st.markdown(f"{idx}. [{art['title']}]({art['link']})")
    else:
        st.warning("⚠️ 사이트 보안망 우회 실패 또는 주소 점검 중입니다. 잠시 후 새로고침(R)을 눌러주세요.")

with tab2:
    st.subheader(f"📈 {selected_site} - 실시간 경향 뉴스")
    if trending_news:
        for idx, art in enumerate(trending_news, 1):
            st.markdown(f"{idx}. [{art['title']}]({art['link']})")
    else:
        st.warning("⚠️ 사이트 보안망 우회 실패 또는 주소 점검 중입니다. 잠시 후 새로고침(R)을 눌러주세요.")

with tab3:
    st.subheader(f"💬 {selected_site} - 반응이 뜨거운 뉴스")
    if popular_news:
        for idx, art in enumerate(popular_news, 1):
            st.markdown(f"{idx}. [{art['title']}]({art['link']})")
    else:
        st.warning("⚠️ 사이트 보안망 우회 실패 또는 주소 점검 중입니다. 잠시 후 새로고침(R)을 눌러주세요.")

st.divider()

# =================================================================
# 6. 이메일 뉴스레터 발송 섹션
# =================================================================
st.subheader("📧 이메일로 이 카테고리 묶어 받기")
st.write(f"현재 선택된 **[{selected_site}]**의 기사들이 하나의 메일로 묶여 발송됩니다.")
target_email = st.text_input("뉴스레터를 받을 이메일 주소 입력:", value="your_mail@example.com")

if st.button("🚀 번역된 종합 뉴스레터 메일로 쏘기"):
    if not most_viewed_news and not trending_news and not popular_news:
        st.error("보내기 실패: 수집된 기사가 존재하지 않습니다.")
    else:
        with st.spinner("메일을 구성하여 안전하게 발송 중입니다..."):
            success = send_combined_newsletter(selected_site, combined_data, target_email)
            if success:
                st.success(f"🎉 {target_email} 계정으로 뉴스 배달이 완료되었습니다!")

st.divider()

# =================================================================
# 7. 디버깅 정보
# =================================================================
if st.checkbox("⚙️ 전체 사이트 동기화 상태 보기"):
    st.write(f"현재 선택된 사이트: `{selected_site}`")
    st.write(f"Most Viewed 개수: `{len(most_viewed_news)}`개")
    st.write(f"Trending 개수: `{len(trending_news)}`개")
    st.write(f"Popular 개수: `{len(popular_news)}`개")
