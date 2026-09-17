import os
import requests
from datetime import datetime, timezone
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()
ACCESS_KEY = os.getenv("ACCESS_KEY")

SEARCH_QUERY = "technology"
TODAY_ONLY = False
MAX_RESULTS = 20
IMAGE_QUALITY = "regular"

def today_local():
    return datetime.now().date()

def to_local_date(created_at_str):
    dt = datetime.fromisoformat(created_at_str.replace("Z", "+00:00"))
    return dt.date()

def search_photos(query, max_results, skip_ids):
    photos = []
    target_day = today_local()
    page = 1
    
    headers = {
        "Authorization": f"Client-ID {ACCESS_KEY}"
    }
    
    while len(photos) < max_results:
        url = "https://api.unsplash.com/search/photos"
        params = {
            "query": query,
            "page": page,
            "per_page": 30,
            "order_by": "latest"
        }
        
        response = requests.get(url, headers=headers, params=params)
        if response.status_code != 200:
            print(f"Lỗi khi gọi Unsplash API: {response.status_code} - {response.text}")
            break
            
        data = response.json()
        results = data.get("results", [])
        if not results:
            break
            
        page_all_older_than_today = True
        
        for photo in results:
            created_date = to_local_date(photo["created_at"])
            
            if created_date >= target_day:
                page_all_older_than_today = False
                
            if TODAY_ONLY and created_date != target_day:
                continue
                
            if photo["id"] in skip_ids:
                continue
                
            photos.append(photo)
            if len(photos) >= max_results:
                break
        
        if TODAY_ONLY and page_all_older_than_today:
            print("Đã duyệt hết ảnh trong ngày (dừng sớm tối ưu API).")
            break
            
        page += 1
        
    return photos

if __name__ == "__main__":
    print("Đang thử nghiệm hàm search_photos với Unsplash API...")
    sample_photos = search_photos(query=SEARCH_QUERY, max_results=MAX_RESULTS, skip_ids=[])
    print(f"Tìm thấy {len(sample_photos)} ảnh thỏa mãn điều kiện.")
    for p in sample_photos:
        print(f"- ID: {p['id']} | Created at: {p['created_at']}")
    import json
from datetime import datetime, timezone

def utc_now_iso():
    """Lấy thời gian hiện tại chuẩn ISO UTC."""
    return datetime.now(timezone.utc).isoformat()

def trigger_download_event(download_location_url):
    """Kích hoạt sự kiện download theo quy định của Unsplash API (bắt buộc gọi theo API Guidelines)."""
    headers = {"Authorization": f"Client-ID {ACCESS_KEY}"}
    try:
        requests.get(download_location_url, headers=headers)
    except Exception as e:
        print(f"Lỗi khi trigger download event: {e}")

def download_image(image_url, save_path_without_ext):
    """Tải file ảnh gốc .jpg từ URL về đường dẫn chỉ định."""
    response = requests.get(image_url)
    if response.status_code == 200:
        file_path = Path(f"{save_path_without_ext}.jpg")
        file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, "wb") as f:
            f.write(response.content)
        return str(file_path)
    return None

def load_json_file(file_path):
    """Đọc file JSON an toàn."""
    path = Path(file_path)
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return {}
    return {}

def save_json_file(file_path, data):
    """Lưu dữ liệu vào file JSON."""
    path = Path(file_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def build_full_record(photo, file_path):
    """Xây dựng bản ghi metadata chi tiết đầy đủ cho ảnh."""
    return {
        "id": photo.get("id"),
        "created_at": photo.get("created_at"),
        "width": photo.get("width"),
        "height": photo.get("height"),
        "color": photo.get("color"),
        "alt_description": photo.get("alt_description"),
        "user": photo.get("user", {}).get("name"),
        "file_path": file_path,
        "urls": photo.get("urls")
    }

def download_photos(photos, save_dir, state_file_path, metadata_file_path):
    """Ghi ảnh và thông tin mô tả vào Data Lake; gọi download_location theo quy định API."""
    save_dir = Path(save_dir)
    state = load_json_file(state_file_path)
    metadata_index = load_json_file(metadata_file_path)
    
    for photo in photos:
        photo_id = photo["id"]
        if photo_id in state:
            print(f"Ảnh {photo_id} đã tồn tại trong trạng thái, bỏ qua.")
            continue
            
        print(f"Đang tải ảnh ID: {photo_id}")
        
        trigger_download_event(photo["links"]["download_location"])
        
        image_url = photo["urls"].get(IMAGE_QUALITY, photo["urls"].get("regular"))
        file_path = download_image(image_url, save_dir / photo_id)
        
        if not file_path:
            print(f"Không thể tải ảnh {photo_id}")
            continue
            
        state[photo_id] = {
            "title": photo.get("alt_description"),
            "file": file_path,
            "downloaded_at": utc_now_iso(),
        }
        
        metadata_index[photo_id] = build_full_record(photo, file_path)
        
        save_json_file(state_file_path, state)
        save_json_file(metadata_file_path, metadata_index)
        print(f"Đã lưu thành công ảnh và metadata cho ID: {photo_id}")
if __name__ == "__main__":
    from datetime import datetime

    print("Đang tiến hành tìm kiếm ảnh từ Unsplash...")
    photos = search_photos(query=SEARCH_QUERY, max_results=2, skip_ids=[])
    print(f"Tìm thấy {len(photos)} ảnh thỏa mãn.")

    if photos:
        today_str = datetime.now().strftime("%Y-%m-%d")

        project_root = Path(__file__).resolve().parent.parent
        base_data_lake = project_root / "data_lake_local" / "unsplash"

        save_directory = base_data_lake / today_str
        state_file = base_data_lake / "state" / "downloaded_ids.json"
        metadata_file = base_data_lake / "state" / "metadata.json"

        print("Bắt đầu tiến trình tải ảnh vào Data Lake...")
        download_photos(photos, save_directory, state_file, metadata_file)
        print("Hoàn tất quy trình lấy dữ liệu Unsplash!")
    