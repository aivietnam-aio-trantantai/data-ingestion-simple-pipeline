import os
import time
import logging
from datetime import datetime, timedelta
from pathlib import Path
import yaml
import feedparser
import pandas as pd

def load_config(config_path):
    """Đọc file cấu hình YAML."""
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def setup_logging(log_dir):
    """Thiết lập hệ thống ghi log theo ngày."""
    log_dir = Path(log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)
    today_str = datetime.now().strftime("%Y-%m-%d")
    log_file = log_dir / f"crawl_{today_str}.log"
    
    logging.basicConfig(
        filename=str(log_file),
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s"
    )
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    logging.getLogger().addHandler(console_handler)

def build_query(category, days_back):
    """Xây dựng truy vấn Atom API theo category và submittedDate."""
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days_back)
    date_range = f"[{start_date.strftime('%Y%m%d')}0000 TO {end_date.strftime('%Y%m%d')}2359]"
    return f"cat:{category} AND submittedDate:{date_range}"

import urllib.parse 
def fetch_papers(base_url, category, max_results, days_back, request_delay):
    """Gọi arXiv Atom API và bóc tách dữ liệu bài báo."""
    query = build_query(category, days_back)
    
    encoded_query = urllib.parse.quote(query)
    search_url = f"{base_url}?search_query={encoded_query}&start=0&max_results={max_results}&sortBy=submittedDate&sortOrder=descending"
    
    logging.info(f"Đang truy vấn danh mục {category} với URL: {search_url}")
    time.sleep(request_delay)
    
    feed = feedparser.parse(search_url)
    papers = []
    
    for entry in feed.entries:
        arxiv_id = entry.id.split("/abs/")[-1]
        
        pdf_url = ""
        for link in entry.links:
            if link.get("type") == "application/pdf":
                pdf_url = link.get("href")
                
        authors = ", ".join([author.get("name", "") for author in entry.get("authors", [])])
        tags = ", ".join([tag.get("term", "") for tag in entry.get("tags", [])])
        
        papers.append({
            "arxiv_id": arxiv_id,
            "title": entry.get("title", "").replace("\n", " "),
            "authors": authors,
            "abstract": entry.get("summary", "").replace("\n", " "),
            "categories": tags,
            "published": entry.get("published", ""),
            "updated": entry.get("updated", ""),
            "pdf_url": pdf_url,
            "primary_category": category,
        })
        
    return papers
def deduplicate_by_arxiv_id(all_papers):
    """Loại bỏ các bài báo bị trùng lặp arXiv ID."""
    seen = set()
    unique_papers = []
    for paper in all_papers:
        if paper["arxiv_id"] not in seen:
            seen.add(paper["arxiv_id"])
            unique_papers.append(paper)
    return unique_papers

def save_to_csv(papers, output_dir):
    """Lưu danh sách bài báo vào file CSV, xử lý an toàn nếu file cũ bị trống."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    today_str = datetime.now().strftime("%Y-%m-%d")
    csv_path = output_dir / f"papers_{today_str}.csv"
    
    df_new = pd.DataFrame(papers)
    
    if csv_path.exists() and csv_path.stat().st_size > 0:
        try:
            df_old = pd.read_csv(csv_path)
            df_combined = pd.concat([df_old, df_new]).drop_duplicates(subset=["arxiv_id"])
            df_combined.to_csv(csv_path, index=False, encoding="utf-8-sig")
            logging.info(f"Đã cập nhật và gộp thêm dữ liệu vào file CSV tồn tại: {csv_path}")
            return
        except Exception as e:
            logging.warning(f"File CSV cũ bị lỗi hoặc trống ({e}), tiến hành ghi đè mới.")
            
    df_new.to_csv(csv_path, index=False, encoding="utf-8-sig")
    logging.info(f"Đã tạo mới file CSV tại: {csv_path}")
def main():
    current_dir = Path(__file__).resolve().parent
    config_path = current_dir / "config.yaml"
    
    config = load_config(config_path)
    
    project_root = current_dir.parent
    data_lake_arxiv = project_root / "data_lake_local" / "arxiv"
    
    setup_logging(data_lake_arxiv / "logs")
    
    logging.info("Bắt đầu tiến trình thu thập dữ liệu từ arXiv API...")
    all_papers = []
    
    for category in config["categories"]:
        try:
            batch = fetch_papers(
                base_url=config["api"]["base_url"],
                category=category,
                max_results=config["max_results_per_category"],
                days_back=config["days_back"],
                request_delay=config["api"]["request_delay"]
            )
            all_papers.extend(batch)
            logging.info(f"Thu thập thành công {len(batch)} bài báo từ danh mục {category}")
        except Exception as e:
            logging.error(f"Lỗi khi thu thập danh mục {category}: {e}")
            continue
            
    unique_papers = deduplicate_by_arxiv_id(all_papers)
    logging.info(f"Tổng số bài báo duy nhất sau khi khử trùng: {len(unique_papers)}")
    
    output_csv_dir = data_lake_arxiv / "data"
    save_to_csv(unique_papers, output_csv_dir)
    logging.info("Hoàn tất quy trình thu thập arXiv!")

if __name__ == "__main__":
    main()