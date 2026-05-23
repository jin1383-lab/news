@st.cache_data(ttl=3600)  # 1시간 캐시
def fetch_oddee_news():
    url = "https://www.oddee.com/"
    # 봇 차단을 우려해 실제 브라우저처럼 보이도록 User-Agent 강 강화
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        # 한글 깨짐 방지 및 인코딩 정상화
        response.encoding = response.apparent_encoding 
        
        soup = BeautifulSoup(response.text, 'html.parser')
        articles = []
        
        # --- [수정] Oddee.com의 실제 주요 기사 타이틀 셀렉터 패턴들 ---
        # 패턴 1: 일반적인 워드프레스 및 뉴스 레이아웃 타이틀 (h2나 h3 내부의 링크)
        elements = soup.select('h2.title a') or soup.select('h3.title a') or soup.select('.post-title a') or soup.select('article h2 a')
        
        # 만약 위 패턴으로도 안 잡힐 경우, 메인화면의 모든 h2/h3 내부 링크 중 주소가 있는 것을 탐색
        if not elements:
            elements = [title.find('a') for title in soup.find_all(['h2', 'h3']) if title.find('a')]

        for post in elements:
            if not post or not post.has_attr('href'):
                continue
                
            title = post.text.strip()
            link = post['href']
            
            # 상대 경로로 링크가 잡힐 경우 절대 경로로 보정
            if link.startswith('/'):
                link = f"https://www.oddee.com{link}"
                
            # 빈 제목이거나 이미 중복된 링크는 제외하고 수집
            if title and link not in [a['link'] for a in articles]:
                articles.append({"title": title, "link": link})
                
            if len(articles) >= 5:  # 최신 기사 5개만 채우면 루프 종료
                break
                
        return articles

    except Exception as e:
        st.error(f"크롤링 중 에러 발생: {e}")
        return []
