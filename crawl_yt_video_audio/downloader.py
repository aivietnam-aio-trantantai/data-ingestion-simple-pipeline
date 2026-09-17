from datetime import datetime, timezone
import os
import json
from pathlib import Path
from yt_dlp import YoutubeDL

def download_assets(urls, base_dir, state_file="downloaded_ids.json"):
    """Tải video, audio, phụ đề và thông tin mô tả; ghi state sau mỗi item."""
    base_dir = Path(base_dir)
    
    for sub in ["video", "audio", "info", "subs"]:
        (base_dir / sub).mkdir(parents=True, exist_ok=True)
        
    state_path = base_dir.parent / "state" / state_file
    state_path.parent.mkdir(parents=True, exist_ok=True)
    
    state = {}
    if state_path.exists():
        with open(state_path, "r", encoding="utf-8") as f:
            try:
                state = json.load(f)
            except json.JSONDecodeError:
                state = {}

    for url in urls:
        video_id = url.split("v=")[-1]
        
        if video_id in state:
            print(f"Video {video_id} đã được tải trước đó, bỏ qua.")
            continue
            
        print(f"Đang xử lý tải xuống cho video: {url}")
        record = {"url": url, "downloaded_at": datetime.now(timezone.utc).isoformat()}
        
        ydl_info_opts = {
            'skip_download': True,
            'writesubtitles': True,
            'writeautomaticsub': True,
            'subtitleslangs': ['en'],
            'outtmpl': str(base_dir / "info" / f"{video_id}")
        }
        
        try:
            with YoutubeDL(ydl_info_opts) as ydl:
                info_dict = ydl.extract_info(url, download=False)
                title = info_dict.get("title", "")
                duration = info_dict.get("duration", 0)
                is_shorts = duration < 60 
                
                info_file = base_dir / "info" / f"{video_id}.info.json"
                with open(info_file, "w", encoding="utf-8") as inf:
                    json.dump(info_dict, inf, ensure_ascii=False, indent=4)
                record["info"] = str(info_file)
        except Exception as e:
            print(f"Lỗi khi lấy thông tin video {video_id}: {e}")
            continue
            
        ydl_video_opts = {
            'format': 'bestvideo[ext=mp4]',
            'outtmpl': str(base_dir / "video" / f"{video_id}.%(ext)s")
        }
        try:
            with YoutubeDL(ydl_video_opts) as ydl:
                ydl.download([url])
            record["video"] = str(base_dir / "video" / f"{video_id}.mp4")
        except Exception as e:
            print(f"Lỗi tải video stream: {e}")

        ydl_audio_opts = {
            'format': 'bestaudio[ext=m4a]',
            'outtmpl': str(base_dir / "audio" / f"{video_id}.%(ext)s")
        }
        try:
            with YoutubeDL(ydl_audio_opts) as ydl:
                ydl.download([url])
            record["audio"] = str(base_dir / "audio" / f"{video_id}.m4a")
        except Exception as e:
            print(f"Lỗi tải audio stream: {e}")

        if record.get("video") or record.get("audio"):
            state[video_id] = record
            with open(state_path, "w", encoding="utf-8") as sf:
                json.dump(state, sf, ensure_ascii=False, indent=4)
            print(f"Đã lưu trạng thái thành công cho video ID: {video_id}")
print("Tiến trình tải xuống bằng yt-dlp đã hoàn tất!")
if __name__ == "__main__":
    import os
    from dotenv import load_dotenv
    from datetime import datetime
    
    load_dotenv()
    
    test_urls = ["https://www.youtube.com/watch?v=M4uql4YT_pQ"]
    
    today_str = datetime.now().strftime("%Y-%m-%d")
    
    base_output_dir = os.path.join(os.path.dirname(__file__), "..", "data_lake_local", "youtube", today_str)
    
    print("Bắt đầu tiến trình tải xuống assets từ YouTube bằng yt-dlp...")
    download_assets(urls=test_urls, base_dir=base_output_dir)
    print("Hoàn tất quá trình tải xuống!")