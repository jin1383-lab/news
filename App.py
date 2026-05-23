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
# 2. 사이트별 RSS 피드 주소 매핑 딕셔너리
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
        "popular": "https://listverse.com/feed/"  # 단일 피드 지원으로 동일 세팅
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
        "most_viewed": "https://www.uexpress.com/oddities/news-of-the-weird/feed",
        "trending": "https://www.uexpress.com/oddities/news-of-the-weird/feed",
        "popular": "https://www.uexpress.com/oddities/news-of-the-weird/feed"
    }
}

# =================================================================
# 3. 선택된 사이트 & 정렬 기준별 RSS 피드 수집 및 번역 (1시간 캐시)
# =================================================================
@st.cache_data(ttl=3600)  
def fetch_news_by_site(site_name, sort_type):
    # 선택된 사이트의 정렬 주소 가져오기
    url = SITE_CONFIG[site_name].get(sort_type, "https://www.oddee.com/feed/")

    try:
        # feedparser로 차단 없이 RSS 데이터 파싱
        feed = feedparser.parse(url)
        
        # 특정 피드가 비어있을 경우 해당 사이트의 메인 피드로 Fallback
        if not feed.entries or len(feed.entries) == 0:
            fallback_url = SITE_CONFIG[site_name]["most_viewed"]
            feed = feedparser.parse(fallback_url)
            
        articles = []
        
        for entry in feed.entries:
            raw_title = entry.get("title", "No Title").strip()
            link = entry.get("link", "https://www.google.com").strip()
            
            # 실시간 한글 번역 구동
            try:
                translated_title = translate(raw_title, "ko", "en")
                full_title = f"{raw_title} ({translated_title})"
            except Exception:
                full_title = raw_title
            
            # 중복 링크 방지
            if link not in [a['link'] for a in articles]:
                articles.append({"title": full_title, "link": link})
            
            if len(articles) >= 5:  # 사이트 과부하 방지용 5개 제한
                break
                
        return articles

    except Exception as e:
        st.error(f"🚨 [{site_name} - {sort_type}] 피드 해석 중 에러 발생: {e}")
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

# 상단 사이트 선택 셀렉트박스 추가
selected_site = st.selectbox(
    "🌐 탐색할 해외 뉴스 사이트를 선택하세요:",
    list(SITE_CONFIG.keys())
)

st.divider()

# 선택된 사이트의 데이터 동시 수집 및 번역 실행
with st.spinner(f"{selected_site}에서 뉴스를 긁어와 실시간 번역 중입니다..."):
    most_viewed_news = fetch_news_by_site(selected_site, 'most_viewed')
    trending_news = fetch_news_by_site(selected_site, 'trending')
    popular_news = fetch_news_by_site(selected_site, 'popular')

# 이메일 전송용 묶음 데이터
combined_data = {
    "Most Viewed 코너": most_viewed_news,
    "Trending 코너": trending_news,
    "Popular 코너": popular_news
}

# 탭을 나누어 정렬별 결과 노출
tab1, tab2, tab3 = st.tabs(["🔥 Most Viewed", "⚡ Trending", "💬 Popular"])

with tab1:
    st.subheader(f"📊 {selected_site} - 가장 많이 본 뉴스")
    if most_viewed_news:
        for idx, art in enumerate(most_viewed_news, 1):
            st.markdown(f"{idx}. [{art['title']}]({art['link']})")
    else:
        st.warning("수집된 뉴스 기사가 없습니다.")

with tab2:
    st.subheader(f"📈 {selected_site} - 실시간 트렌드 경향")
    if trending_news:
        for idx, art in enumerate(trending_news, 1):
            st.markdown(f"{idx}. [{art['title']}]({art['link']})")
    else:
        st.warning("수집된 뉴스 기사가 없습니다.")

with tab3:
    st.subheader(f"💬 {selected_site} - 독자 반응이 뜨거운 뉴스")
    if popular_news:
        for idx, art in enumerate(popular_news, 1):
            st.markdown(f"{idx}. [{art['title']}]({art['link']})")
    else:
        st.warning("수집된 뉴스 기사가 없습니다.")

st.divider()

# =================================================================
# 6. 이메일 뉴스레터 발송 섹션
# =================================================================
st.subheader("📧 이메일로 이 카테고리 묶어 받기")
st.write(f"현재 선택된 **[{selected_site}]**의 3개 영역 기사들이 하나의 메일로 묶여 발송됩니다.")
target_email = st.text_input("뉴스레터를 받을 이메일 주소 입력:", value="your_mail@example.com")

if st.button("🚀 번역된 종합 뉴스레터 메일로 쏘기"):
    with st.spinner("메일을 구성하여 안전하게 발송 중입니다..."):
        success = send_combined_newsletter(selected_site, combined_data, target_email)
        if success:
            st.success(f"🎉 {target_email} 계정으로 뉴스 배달이 완료되었습니다!")

st.divider()

# =================================================================
# 7. 디버깅 정보
# =================================================================
if st.checkbox("⚙️ 전체 사이트 동기화 상태 보기"):
    for site in SITE_CONFIG.keys():
        st.write(f"· `{site}` 피드 세팅 완료")
