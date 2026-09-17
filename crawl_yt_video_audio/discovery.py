from datetime import datetime, timedelta, timezone
from googleapiclient.discovery import build

def is_likely_english(snippet):
    """Kiểm tra sơ bộ xem tiêu đề video có chứa ký tự tiếng Anh hay không."""
    title = snippet.get("title", "")
    try:
        title.encode(encoding="utf-8").decode("ascii")
        return True
    except UnicodeDecodeError:
        return False

def get_recent_videos(api_key, skip_ids, config):
    """Tìm video mới bằng YouTube Data API v3 dựa trên config."""
    youtube = build("youtube", "v3", developerKey=api_key)
    
    published_after = (datetime.now(timezone.utc) - timedelta(days=config.get("days_back", 1))).isoformat()
    video_urls = []
    
    response = youtube.search().list(
        part = 'snippet',
        q=config.get("query"),
        type="video",
        publishedAfter=published_after,
        order="date",
        maxResults=50
    ).execute()
    
    candidate_ids = [
        item["id"]["videoId"]
        for item in response.get("items", [])
        if item["id"]["videoId"] not in skip_ids
    ]
    
    if not candidate_ids:
        return video_urls

    details = youtube.videos().list(
        part="snippet,contentDetails",
        id=",".join(candidate_ids)
    ).execute()
    
    for item in details.get("items", []):
        video_id = item["id"]
        snippet = item["snippet"]
        
        if config.get("require_english", True) and not is_likely_english(snippet):
            continue
            
        video_urls.append(f"https://www.youtube.com/watch?v={video_id}")
        if len(video_urls) >= config.get("max_results", 10):
            break
            
    return video_urls

if __name__ == "__main__":
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    api_key = os.getenv("YOUTUBE_API_KEY")
    
    test_config = {
        "query": "AI Research Papers",
        "days_back": 1,
        "require_english": True,
        "max_results": 3
    }
    
    print("Đang thử nghiệm tìm kiếm video từ YouTube API...")
    urls = get_recent_videos(api_key=api_key, skip_ids=[], config=test_config)
    print("Danh sách video tìm được:", urls)