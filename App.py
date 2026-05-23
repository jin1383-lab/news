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
st.set_page_config(page_title="Oddee 멀티 뉴스봇", page_icon="📰", layout="centered")
st.title("📰 Oddee 멀티 뉴스 관리 대시보드")
st.write("Most Viewed, Trending, Popular 기사를 각각 솎아내어 한글 번역과 함께 제공합니다.")

# =================================================================
# 2. 정렬 기준별 RSS 피드 수집 및 번역 함수 (1시간 캐시)
# =================================================================
@st.cache_data(ttl=3600)  
def fetch_oddee_by_sort(sort_type):
    """
    sort_type 종류:
    - 'most_viewed': 조회수 또는 기본 정렬
    - 'trending': 최근 날짜 기준 핫한 기사
    - 'popular': 댓글이나 반응이 많은 기사
    """
    if sort_type == 'most_viewed':
        url = "https://www.oddee.com/feed/"  # 메인 피드가 보통 가장 많이 본 기사 위주 배치
    elif sort_type == 'trending':
        url = "https://www.oddee.com/feed/?orderby=date"  # 최신 트렌드 경향
    elif sort_type == 'popular':
        url = "https://www.oddee.com/feed/?orderby=comment_count"  # 댓글 많은 인기순
    else:
        url = "https://www.oddee.com/feed/"

    try:
        feed = feedparser.parse(url)
        
        # 만약 특정 피드가 막히거나 비어있으면 기본 피드로 Fallback
        if not feed.entries or len(feed.entries) == 0:
            feed = feedparser.parse("https://www.oddee.com/feed/")
            
        articles = []
        
        for entry in feed.entries:
            raw_title = entry.get("title", "No Title").strip()
            link = entry.get("link", "https://www.oddee.com/").strip()
            
            # 실시간 한글 번역
            try:
                translated_title = translate(raw_title, "ko", "en")
                full_title = f"{raw_title} ({translated_title})"
            except Exception:
                full_title = raw_title
            
            if link not in [a['link'] for a in articles]:
                articles.append({"title": full_title, "link": link})
            
            if len(articles) >= 5:  # 각 카테고리당 5개씩 수집
                break
                
        return articles

    except Exception as e:
        st.error(f"🚨 [{sort_type}] 피드 해석 중 에러 발생: {e}")
        return []

# =================================================================
# 3. 통합 이메일 발송 함수
# =================================================================
def send_combined_newsletter(data_dict, receiver_email):
    try:
        sender_email = st.secrets["email"]["sender"]
        sender_password = st.secrets["email"]["password"]
    except KeyError:
        st.error("🔒 Streamlit Secrets에 이메일 정보가 설정되지 않았습니다.")
        return False
    
    msg = MIMEMultipart('alternative')
    msg['Subject'] = "📰 [Oddee 종합 뉴스레터] 오늘의 맞춤형 기사 모음"
    msg['From'] = sender_email
    msg['To'] = receiver_email
    
    # HTML 메일 본문 작성 (3개 영역 모두 포함)
    html = "<h2>오늘의 Oddee 종합 뉴스레터</h2>"
    
    for category, articles in data_dict.items():
        html += f"<h3 style='color: #ff4b4b;'>🔥 {category} Top 5</h3><ul>"
        if articles:
            for art in articles:
                html += f"<li><a href='{art['link']}'>{art['title']}</a></li>"
        else:
            html += "<li>수집된 기사가 없습니다.</li>"
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
# 4. 화면 UI 렌더링 부 (Tabs 활용)
# =================================================================

# 데이터 선행 수집
with st.spinner("각 카테고리별 뉴스를 수집 및 번역 중입니다..."):
    most_viewed_news = fetch_oddee_by_sort('most_viewed')
    trending_news = fetch_oddee_by_sort('trending')
    popular_news = fetch_oddee_by_sort('popular')

# 데이터 묶기 (이메일 발송용)
combined_data = {
    "Most Viewed 뉴스": most_viewed_news,
    "Trending 뉴스": trending_news,
    "Popular 뉴스": popular_news
}

# Streamlit 탭 생성
tab1, tab2, tab3 = st.tabs(["🔥 Most Viewed", "⚡ Trending", "💬 Popular"])

with tab1:
    st.subheader("📊 독자들이 가장 많이 본 기사")
    if most_viewed_news:
        for idx, art in enumerate(most_viewed_news, 1):
            st.markdown(f"{idx}. [{art['title']}]({art['link']})")
    else:
        st.write("기사가 없습니다.")

with tab2:
    st.subheader("📈 지금 뜨고 있는 실시간 트렌드 기사")
    if trending_news:
        for idx, art in enumerate(trending_news, 1):
            st.markdown(f"{idx}. [{art['title']}]({art['link']})")
    else:
        st.write("기사가 없습니다.")

with tab3:
    st.subheader("💬 댓글 반응이 폭발한 인기 기사")
    if popular_news:
        for idx, art in enumerate(popular_news, 1):
            st.markdown(f"{idx}. [{art['title']}]({art['link']})")
    else:
        st.write("기사가 없습니다.")

st.divider()

# =================================================================
# 5. 통합 이메일 뉴스레터 발송 섹션
# =================================================================
st.subheader("📧 전체 카테고리 통합 메일 발송")
st.write("위 3가지 종류의 뉴스(총 15개)가 깔끔하게 정리된 하나의 메일로 발송됩니다.")
target_email = st.text_input("뉴스레터를 받을 이메일 주소:", value="your_mail@example.com")

if st.button("🚀 종합 뉴스레터 한 번에 받기"):
    with st.spinner("통합 메일을 구성하여 발송 중입니다..."):
        success = send_combined_newsletter(combined_data, target_email)
        if success:
            st.success(f"🎉 {target_email} 계정으로 통합 뉴스레터가 전송되었습니다!")

st.divider()

# =================================================================
# 6. 개발자용 디버깅 툴
# =================================================================
if st.checkbox("⚙️ 데이터 동기화 상태 점검"):
    st.write(f"Most Viewed 수집 개수: `{len(most_viewed_news)}`개")
    st.write(f"Trending 수집 개수: `{len(trending_news)}`개")
    st.write(f"Popular 수집 개수: `{len(popular_news)}`개")
