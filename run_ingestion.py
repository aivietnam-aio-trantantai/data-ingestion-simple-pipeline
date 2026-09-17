import os
import sys
import subprocess
import argparse
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent

JOB_SCRIPTS = {
    "arxiv": "crawl_arxiv/main.py",
    "yt": "crawl_yt_video_audio/downloader.py", 
    "unsplash": "crawl_unsplash_image/main.py",
}

def run_python(rel_path):
    """Chạy một file script Python con bằng chính sys.executable để đảm bảo đúng môi trường."""
    script = REPO_ROOT / rel_path
    print(f"===> Đang thực thi tiến trình: {rel_path}")
    
    proc = subprocess.run(
        [sys.executable, str(script)],
        cwd=str(REPO_ROOT),
    )
    return proc.returncode

def parse_job_argument(argv):
    """Phân tích tham số dòng lệnh nhận vào qua --job."""
    parser = argparse.ArgumentParser(description="Orchestrator cho Data Ingestion Pipeline")
    parser.add_argument(
        "--job", 
        required=True, 
        choices=["all", "arxiv", "yt", "unsplash"],
        help="Chọn job cần chạy: all hoặc từng nguồn riêng lẻ"
    )
    args = parser.parse_args(argv)
    if args.job == "all":
        return ["all"]
    return [args.job]

def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]
        
    jobs = parse_job_argument(argv)
    if "all" in jobs:
        jobs = ["arxiv", "yt", "unsplash"]
        
    exit_code = 0
    for job in jobs:
        if job not in JOB_SCRIPTS:
            print(f"Lỗi: Job '{job}' không tồn tại trong cấu hình!")
            continue
            
        rc = run_python(JOB_SCRIPTS[job])
        if rc != 0 and exit_code == 0:
            exit_code = rc
            print(f"Cảnh báo: Job '{job}' kết thúc với mã lỗi {rc}")
            
    return exit_code

if __name__ == "__main__":
    sys.exit(main())