#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
통합 예약 현황 모니터링 스크립트
- 수락휴, 무의도, 용인자연휴양림 사이트 지원
- 사용법:
    python reservation-monitor.py <site>
  where <site> is one of: "수락휴", "무의도", "용인자연휴양림"
  기본값은 "수락휴"
"""

import os
import sys
import io

if sys.platform == "win32":
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
    except Exception:
        pass

import re
import json
import base64
import cv2
import requests
import numpy as np
import time
import subprocess

# GitHub repo configuration (generated at runtime)
GIT_REPO_URL = "https://github.com/matrix1970/forest.git"
GIT_LOCAL_PATH = os.path.join(os.path.abspath(os.path.dirname(__file__)), "git_repo")
GIT_TOKEN = os.getenv("GIT_TOKEN")  # Load token from environment variable for security

import shutil

def _git_executable():
    """Return the full path to the git executable.
    Tries to locate git via shutil.which; if not found, falls back to common install locations.
    Raises FileNotFoundError with a clear message if git cannot be located.
    """
    git_path = shutil.which('git')
    if git_path:
        return git_path
    # Common default locations on Windows
    possible_paths = [
        r"C:\Program Files\Git\cmd\git.exe",
        r"C:\Program Files\Git\bin\git.exe",
        r"C:\Program Files (x86)\Git\cmd\git.exe",
        r"C:\Program Files (x86)\Git\bin\git.exe",
        r"C:\Users\%USERNAME%\AppData\Local\Programs\Git\cmd\git.exe",
    ]
    for p in possible_paths:
        if os.path.isfile(p):
            return p
    raise FileNotFoundError("Git executable not found. Install Git for Windows and ensure it is on the PATH.")

def ensure_git_repo():
    git_cmd = _git_executable()
    if not os.path.isdir(GIT_LOCAL_PATH):
        os.makedirs(GIT_LOCAL_PATH, exist_ok=True)
        # Clone repository using token for authentication
        clone_url = GIT_REPO_URL.replace("https://", f"https://{GIT_TOKEN}@")
        subprocess.run([git_cmd, "clone", clone_url, GIT_LOCAL_PATH], check=True)
    else:
        # Ensure remote URL has token (in case token changed)
        subprocess.run([
            git_cmd, "-C", GIT_LOCAL_PATH, "remote", "set-url", "origin",
            GIT_REPO_URL.replace("https://", f"https://{GIT_TOKEN}@")
        ], check=True)

    if not os.path.isdir(GIT_LOCAL_PATH):
        os.makedirs(GIT_LOCAL_PATH, exist_ok=True)
        # Clone repository using token for authentication
        clone_url = GIT_REPO_URL.replace("https://", f"https://{GIT_TOKEN}@")
        subprocess.run(["git", "clone", clone_url, GIT_LOCAL_PATH], check=True)
    else:
        # Ensure remote URL has token (in case token changed)
        subprocess.run(["git", "-C", GIT_LOCAL_PATH, "remote", "set-url", "origin", GIT_REPO_URL.replace("https://", f"https://{GIT_TOKEN}@")], check=True)

def generate_html_report(txt_path, html_path):
    try:
        with open(txt_path, "r", encoding="utf-8") as f:
            content = f.read()
        # 현재 시각을 HH:MM:SS 형식으로 삽입
        from datetime import datetime
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        html = f"""<!DOCTYPE html>
<html lang=\"ko\">
<head>
<meta charset=\"UTF-8\">
<title>Room History Report</title>
<meta http-equiv=\"refresh\" content=\"30\"> <!-- refresh every 30 sec -->
<style>
body {{ font-family: Arial, sans-serif; background:#f9f9f9; padding:20px; }}
pre {{ background:#fff; border:1px solid #ddd; padding:10px; overflow:auto; max-height:90vh; }}
</style>
</head>
<body>
<h2>Room History Report</h2>
<p><em>Generated at: {now_str}</em></p>
<pre>{content}</pre>
</body>
</html>"""
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html)
    except Exception as e:
        print(f"⚠️ HTML 생성 오류: {e}")
    try:
        with open(txt_path, "r", encoding="utf-8") as f:
            content = f.read()
        html = f"""<!DOCTYPE html>
<html lang=\"ko\">
<head>
<meta charset=\"UTF-8\">
<title>Room History Report</title>
<meta http-equiv=\"refresh\" content=\"30\"> <!-- refresh every 30 sec -->
<style>
body {{ font-family: Arial, sans-serif; background:#f9f9f9; padding:20px; }}
pre {{ background:#fff; border:1px solid #ddd; padding:10px; overflow:auto; max-height:90vh; }}
</style>
</head>
<body>
<h2>Room History Report</h2>
<pre>{content}</pre>
</body>
</html>"""
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html)
    except Exception as e:
        print(f"⚠️ HTML 생성 오류: {e}")

def git_commit_and_push(site, txt_path, html_path):
    try:
        # copy files into repo under site folder
        site_dir = os.path.join(GIT_LOCAL_PATH, site)
        os.makedirs(site_dir, exist_ok=True)
        dest_txt = os.path.join(site_dir, os.path.basename(txt_path))
        dest_html = os.path.join(site_dir, os.path.basename(html_path))
        shutil.copy2(txt_path, dest_txt)
        shutil.copy2(html_path, dest_html)
        git_cmd = _git_executable()
        subprocess.run([git_cmd, "-C", GIT_LOCAL_PATH, "add", "."], check=True)
        commit_msg = f"Update {site} report {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        subprocess.run([git_cmd, "-C", GIT_LOCAL_PATH, "commit", "-m", commit_msg], check=True)
        subprocess.run([git_cmd, "-C", GIT_LOCAL_PATH, "push", "origin", "main"], check=True)
    except subprocess.CalledProcessError as e:
        print(f"⚠️ Git 작업 오류: {e}")
    except Exception as e:
        print(f"⚠️ Git 일반 오류: {e}")

from datetime import datetime, date
from collections import defaultdict
from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By

# Alias map for filesystem-friendly names
# Flag for test mode – when True, Telegram functions just print instead of sending real requests
TEST_MODE = False

SITE_ALIAS = {"수락휴": "sulakhu", "무의도": "muuid", "용인자연휴양림": "yongin"}

# ---------------------------------------------------------------------------
# 사이트 별 설정
# ---------------------------------------------------------------------------
# 12월 1일 ~ 31일의 정확한 셀 중심 x좌표 (31일 기준, 폭 약 30.5px)
COMMON_DECEMBER_X_CENTERS = [
    627, 658, 688, 718, 749, 779, 809, 840, 870, 900, 930, 961,
    991, 1021, 1052, 1082, 1112, 1143, 1173, 1203, 1234, 1264, 1294,
    1325, 1355, 1385, 1415, 1446, 1476, 1506, 1536
]

SITE_CONFIG = {
    "수락휴": {
        "URL": "https://www.foresttrip.go.kr/com/login.do?hmpgId=ID02030129&targetUrl=/indvz/main.do?hmpgId=ID02030129",
        "TARGET_URL": "https://www.foresttrip.go.kr/rep/or/sssn/monthRsrvtStatus.do?hmpgId=ID02030129&menuId=001004",
        "SAVE_DIR": r"x:/iptime/forest2",
        "MARKED_SUBDIR": "marked",
        "HISTORY_LOG": "status_changes.log",
        "ROOM_HISTORY_LOG": "room_history_report.txt",
        "memberId": "maya910",
        "gnrlMmberPssrd": "u@rt8826fo",
        "MIN_IMAGE_HEIGHT": 2500,
        "DAYS_IN_MONTH": 31,
        "CELL_FIRST_X": 627,
        "CELL_LAST_X": 1536,
        "CELL_X_CENTERS": COMMON_DECEMBER_X_CENTERS,
        "URGENT_TARGET_DAYS": ["5", "12", "25", "26"],
        "ROOM_Y_RANGES": [
            ("[개별동] 1호 비온 뒤 맑음 (4인실)", 975, 1030),
            ("[개별동] 2호 태양은 가득히 (4인실)", 1030, 1085),
            ("[개별동] 3호 초록빛 오후 (4인실)", 1085, 1140),
            ("[개별동] 4호 소풍같은 하루 (6인실)", 1140, 1195),
            ("[개별동] 5호 오늘의 여유 (4인실)", 1195, 1250),
            ("[개별동] 6호 여우비 (4인실)", 1250, 1305),
            ("[개별동] 7호 네잎클로버 (4인실)", 1305, 1360),
            ("[개별동] 8호 햇살 한 조각 (4인실)", 1360, 1415),
            ("[개별동] 9호 수락의 휴일 (2인실)", 1415, 1470),
            ("[개별동] 10호 지구별 여행자 (6인실)", 1470, 1525),
            ("[개별동] 11호 은하수를 건너 (4인실)", 1525, 1580),
            ("[개별동] 12호 밤하늘을 날아서 (4인실)", 1580, 1635),
            ("[개별동] 13호 수락산의 푸른밤 (2인실)", 1635, 1690),
            ("[트리하우스] 14호 별 헤는 밤 (4인실)", 1690, 1745),
            ("[트리하우스] 15호 B612(어린왕자) (4인실)", 1745, 1800),
            ("[트리하우스] 16호[코스+숙박] 별밤 (4인실)", 1800, 1855),
            ("[본동] 17호 수락 638 (2인실)", 1855, 1910),
            ("[본동] 18호 산들바람 (2인실)", 1910, 1965),
            ("[본동] 19호 풍경소리 (2인실)", 1965, 2020),
            ("[본동] 20호 구름산책 (2인실)", 2020, 2075),
            ("[본동] 21호 푸른 하늘 (장애인실:2인)", 2075, 2130),
            ("[본동] 22호 종이비행기 (2인실)", 2130, 2185),
            ("[본동] 23호 노을 질 무렵 (2인실)", 2185, 2240),
            ("[본동] 24호 나비의 꿈 (2인실)", 2240, 2295),
            ("[본동] 25호 새벽공기 (2인실)", 2295, 2350)
        ],
        "LAST_ROOM_CHECK": {"y_range": (2295, 2350), "label": "새벽공기"}
    },
    "무의도": {
        "URL": "https://www.foresttrip.go.kr/com/login.do?hmpgId=0303&targetUrl=/indvz/main.do?hmpgId=0303",
        "TARGET_URL": "https://www.foresttrip.go.kr/rep/or/sssn/monthRsrvtStatus.do?hmpgId=0303&menuId=001004",
        "SAVE_DIR": r"x:/iptime/forest3",
        "MARKED_SUBDIR": "marked",
        "HISTORY_LOG": "status_changes.log",
        "ROOM_HISTORY_LOG": "room_history_report.txt",
        "memberId": "maya910",
        "gnrlMmberPssrd": "u@rt8826fo",
        "MIN_IMAGE_HEIGHT": 2050,
        "DAYS_IN_MONTH": 31,
        "CELL_FIRST_X": 627,
        "CELL_LAST_X": 1536,
        "CELL_X_CENTERS": COMMON_DECEMBER_X_CENTERS,
        "URGENT_TARGET_DAYS": ["5", "12", "25", "26"],
        "ROOM_Y_RANGES": [
            ("[숲속의집]무의도", 975, 1030),
            ("[숲속의집]실미도", 1030, 1085),
            ("[숲속의집]선미도", 1085, 1140),
            ("[숲속의집]팔미도", 1140, 1195),
            ("[숲속의집]소야도", 1195, 1250),
            ("[숲속의집]승봉도", 1250, 1305),
            ("[숲속의집]자월도", 1305, 1360),
            ("[숲속의집]대이작도", 1360, 1415),
            ("[숲속의집]소이작도", 1415, 1470),
            ("[숲속의집]백아도", 1470, 1525),
            ("[숲속의집]굴업도", 1525, 1580),
            ("[연립동]101호", 1580, 1635),
            ("[연립동]102호", 1635, 1690),
            ("[연립동]103호", 1690, 1745),
            ("[연립동]104호", 1745, 1800),
            ("[연립동]105호", 1800, 1855),
            ("[연립동]106호", 1855, 1910),
            ("[연립동]107호", 1910, 1965),
            ("[연립동]108호", 1965, 2020)
        ],
        "LAST_ROOM_CHECK": {"y_range": (1965, 2020), "label": "108호"}
    },
    "용인자연휴양림": {
        "URL": "https://www.foresttrip.go.kr/com/login.do?hmpgId=ID02030031&targetUrl=/indvz/main.do?hmpgId=ID02030031",
        "TARGET_URL": "https://www.foresttrip.go.kr/rep/or/sssn/monthRsrvtStatus.do?hmpgId=ID02030031&menuId=001004",
        "SAVE_DIR": r"x:/iptime/forest",
        "MARKED_SUBDIR": "marked",
        "HISTORY_LOG": "status_changes.log",
        "ROOM_HISTORY_LOG": "room_history_report.txt",
        "memberId": "maya910",
        "gnrlMmberPssrd": "u@rt8826fo",
        "MIN_IMAGE_HEIGHT": 2600,
        "DAYS_IN_MONTH": 31,
        "CELL_FIRST_X": 627,
        "CELL_LAST_X": 1536,
        "CELL_X_CENTERS": COMMON_DECEMBER_X_CENTERS,
        "URGENT_TARGET_DAYS": ["5", "12", "25", "26"],
        "ROOM_Y_RANGES": [
            ("[숲속의집]가마골1", 975, 1030),
            ("[숲속의집]가마골2", 1030, 1085),
            ("[숲속의집]가마골3", 1085, 1140),
            ("[숲속의집]가마골4", 1140, 1195),
            ("[숲속의집]느티골5-1", 1195, 1250),
            ("[숲속의집]느티골5-2", 1250, 1305),
            ("[숲속의집]느티골5-3", 1305, 1360),
            ("[숲속의집]느티골5-4", 1360, 1415),
            ("[숲속의집]느티골5-5", 1415, 1470),
            ("[숲속의집]밤티골2", 1470, 1525),
            ("[숲속의집]밤티골3", 1525, 1580),
            ("[숲속의집]밤티골4", 1580, 1635),
            ("[숲속의집]밤티골5", 1635, 1690)
        ],
        "LAST_ROOM_CHECK": {"y_range": (2515, 2570), "label": "카라반04"}
    }
}

# ---------------------------------------------------------------------------
# 공통 설정 (텔레그램 등)
# ---------------------------------------------------------------------------
TELEGRAM_TOKEN = "8845492635:AAEpVGm7fTHGZu3s0hneQ1KSuX2t5a8CYcI"
TELEGRAM_CHAT_ID = "7147398189"
INTERVAL_SECONDS = 60

# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------

def setup_directories(cfg):
    for folder in [cfg["SAVE_DIR"], os.path.join(cfg["SAVE_DIR"], cfg["MARKED_SUBDIR"])]:
        if not os.path.exists(folder):
            os.makedirs(folder)
            print(f"📁 [{folder}] 폴더가 생성되었습니다.")

def append_to_history_log(timestamp, diff_info, cfg):
    """1) 시간순 전체 로그 + 2) 방별 누적 히스토리 동시 기록"""
    try:
        history_log_path = os.path.join(cfg["SAVE_DIR"], cfg["HISTORY_LOG"])
        room_history_path = os.path.join(cfg["SAVE_DIR"], cfg["ROOM_HISTORY_LOG"])
        
        # 방(객실)별로 변경 사항 그룹화
        room_changes = defaultdict(list)
        for item in diff_info:
            room_changes[item['room']].append(item)

        # 1. 시간순 전체 로그 저장
        with open(history_log_path, "a", encoding="utf-8") as f:
            f.write(f"\n========================================\n")
            f.write(f"⏰ 변동 시각: {timestamp}\n")
            f.write(f"========================================\n")
            for room, changes in room_changes.items():
                f.write(f"🏠 {room}\n")
                for c in changes:
                    urgent_tag = " [🚨긴급알림]" if c.get('is_urgent') else ""
                    f.write(f"   └ 📅 {c['day']} : {c['status_before']} ➔ {c['status_after']}{urgent_tag}\n")

        # 2. 방별 누적 히스토리 파일 추가
        with open(room_history_path, "a", encoding="utf-8") as f:
            for room, changes in room_changes.items():
                for c in changes:
                    urgent_tag = " [🚨긴급]" if c.get('is_urgent') else ""
                    f.write(f"[{timestamp}] 🏠 {room} | 📅 {c['day']} : {c['status_before']} ➔ {c['status_after']}{urgent_tag}\n")

        print(f"📝 히스토리 로그 기록 완료: {history_log_path}")
    except Exception as e:
        print(f"⚠️ 로그 파일 저장 실패: {e}")

def send_telegram_message(text):
    if TEST_MODE:
        print(f"[TEST MODE] Telegram message: {text}")
        return True
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": text}
    try:
        r = requests.post(url, data=payload)
        return r.status_code == 200
    except Exception as e:
        print(f"❌ 텔레그램 전송 예외: {e}")
        return False

def send_telegram_photo(photo_path, caption=None):
    if TEST_MODE:
        print(f"[TEST MODE] Telegram photo: {photo_path}, caption: {caption}")
        return True
    if not os.path.exists(photo_path):
        return send_telegram_message(caption or "")
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto"
    try:
        with open(photo_path, "rb") as f:
            files = {"photo": ("marked.png", f, "image/png")}
            data = {"chat_id": TELEGRAM_CHAT_ID}
            if caption:
                data["caption"] = caption
            r = requests.post(url, data=data, files=files)
            return r.status_code == 200
    except Exception as e:
        print(f"❌ 텔레그램 사진 전송 예외: {e}")
        return False

def cv2_imread_unicode(filepath: str):
    try:
        with open(filepath, "rb") as f:
            data = np.frombuffer(f.read(), np.uint8)
            return cv2.imdecode(data, cv2.IMREAD_COLOR)
    except Exception as e:
        print(f"❌ 이미지 로드 실패: {e}")
        return None

def cv2_imwrite_unicode(filepath: str, img) -> bool:
    try:
        ext = os.path.splitext(filepath)[1]
        ok, encoded = cv2.imencode(ext, img)
        if ok:
            with open(filepath, "wb") as f:
                encoded.tofile(f)
            return True
        return False
    except Exception as e:
        print(f"❌ 이미지 저장 실패: {e}")
        return False

# ---------------------------------------------------------------------------
# Core image analysis
# ---------------------------------------------------------------------------

def get_room_and_day(abs_cx, abs_cy, cfg):
    if "CELL_X_CENTERS" in cfg:
        centers = cfg["CELL_X_CENTERS"]
        diffs = [abs(abs_cx - c) for c in centers]
        day_index = diffs.index(min(diffs)) + 1
    else:
        day_index = int(round((abs_cx - cfg["CELL_FIRST_X"]) / cfg["DATE_STEP_X"])) + 1
    if 1 <= day_index <= cfg["DAYS_IN_MONTH"]:
        try:
            wd = date(2026, 12, day_index).weekday()
            weekday_str = ["월", "화", "수", "목", "금", "토", "일"][wd]
            day_str = f"{day_index}일 ({weekday_str})"
        except Exception:
            day_str = f"{day_index}일"
    else:
        day_str = f"X={abs_cx}"
    room_name = "알 수 없는 객실"
    for name, y_min, y_max in cfg["ROOM_Y_RANGES"]:
        if y_min <= abs_cy < y_max:
            room_name = name
            break
    return room_name, day_str

def get_cell_status(img, cy, sx):
    crop = img[max(0, cy-10):cy+11, max(0, sx-10):sx+11].astype(int)
    if crop.size == 0:
        return "공백(비활성)"
    b, g, r = crop[:, :, 0], crop[:, :, 1], crop[:, :, 2]
    green_px = np.sum((g > r + 30) & (g > b + 15) & (g > 120))
    blue_px = np.sum((b > r + 40) & (b > g + 15) & (b > 120) & (r < 120))
    gray_px = np.sum((np.abs(b - g) < 25) & (np.abs(g - r) < 25) & (r >= 100) & (r <= 210))
    if green_px >= 50:
        return "예약가능(🟢예)"
    if blue_px >= 50:
        return "대기(🔵대)"
    if gray_px >= 100:
        return "예약완료(⚪완)"
    return "공백(비활성)"

# ---------------------------------------------------------------------------
# Selenium screenshot capture
# ---------------------------------------------------------------------------

def capture_target_screenshot(cfg, filepath: str) -> bool:
    opts = Options()
    opts.add_argument("--headless=new")
    opts.add_argument("--window-size=1920,2800")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--log-level=3")
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=opts)
    wait = WebDriverWait(driver, 20)
    try:
        driver.get(cfg["URL"])
        driver.implicitly_wait(10)
        wait.until(EC.presence_of_element_located((By.ID, "mmberId"))).send_keys("matrix1970")
        driver.find_element(By.ID, "gnrlMmberPssrd").send_keys("u@rt825100")
        driver.find_element(By.CLASS_NAME, "loginBtn").click()
        time.sleep(3)

        target_url = cfg["TARGET_URL"]
        driver.get(target_url)
        Select(wait.until(EC.presence_of_element_located((By.ID, "srchForest")))).select_by_visible_text("숙소")
        Select(wait.until(EC.presence_of_element_located((By.ID, "monthSelectBox")))).select_by_visible_text("2026년 12월")
        driver.find_element(By.ID, "searchBtn").click()
        
        total = len(cfg["ROOM_Y_RANGES"])
        def table_loaded(d):
            rows = d.find_elements(By.CSS_SELECTOR, "#dayListTable tbody tr")
            if len(rows) >= total:
                return True
            sp = d.find_elements(By.CSS_SELECTOR, ".loading, #loading, .loading-wrap, .loading_layer, [class*='load_'], [id*='loading'], .dimmed")
            return not any(s.is_displayed() for s in sp)
        WebDriverWait(driver, 45).until(table_loaded)
        time.sleep(2)
        try:
            res = driver.execute_cdp_cmd("Page.captureScreenshot", {"captureBeyondViewport": True})
            with open(filepath, "wb") as f:
                f.write(base64.b64decode(res["data"]))
        except Exception:
            driver.find_element(By.TAG_NAME, "body").screenshot(filepath)
        return True
    except Exception as e:
        print(f"[ERROR] 캡처 예외: {e}")
        try:
            with open(filepath + ".html", "w", encoding="utf-8") as f:
                f.write(driver.page_source)
        except Exception:
            pass
        return False
    finally:
        driver.quit()

def is_screenshot_valid(filepath: str, cfg) -> bool:
    try:
        img = cv2_imread_unicode(filepath)
        if img is None:
            return False
        h, _ = img.shape[:2]
        if h < cfg["MIN_IMAGE_HEIGHT"]:
            print(f"⚠️ 이미지 높이 부족 ({h}< {cfg['MIN_IMAGE_HEIGHT']})")
            return False
        y0, y1 = cfg["LAST_ROOM_CHECK"]["y_range"]
        last_crop = img[y0:y1, cfg["CELL_FIRST_X"]:cfg["CELL_LAST_X"]]
        if np.std(last_crop) < 5.0:
            print("⚠️ 마지막 객실 영역이 비어있음 (std <5)")
            return False
        return True
    except Exception as e:
        print(f"❌ 이미지 검증 오류: {e}")
        return False

# ---------------------------------------------------------------------------
# Difference detection & alerting
# ---------------------------------------------------------------------------

def mark_exact_differences(before_path, after_path, cfg, timestamp):
    try:
        img1 = cv2_imread_unicode(before_path)
        img2 = cv2_imread_unicode(after_path)
        if img1 is None or img2 is None:
            return False, [], None
        if img1.shape[0] < cfg["MIN_IMAGE_HEIGHT"] or img2.shape[0] < cfg["MIN_IMAGE_HEIGHT"]:
            return False, [], None
        img1_mark = img1.copy()
        img2_mark = img2.copy()
        changed = False
        info = []
        for name, y_min, y_max in cfg["ROOM_Y_RANGES"]:
            cy = (y_min + y_max) // 2
            for day_idx in range(cfg["DAYS_IN_MONTH"]):
                if "CELL_X_CENTERS" in cfg and day_idx < len(cfg["CELL_X_CENTERS"]):
                    sx = cfg["CELL_X_CENTERS"][day_idx]
                else:
                    sx = int(round(cfg["CELL_FIRST_X"] + day_idx * cfg["DATE_STEP_X"]))
                before = get_cell_status(img1, cy, sx)
                after = get_cell_status(img2, cy, sx)
                if before != after:
                    changed = True
                    room, day = get_room_and_day(sx, cy, cfg)
                    day_num = str(day_idx + 1)
                    is_urgent = day_num in cfg.get("URGENT_TARGET_DAYS", [])
                    cv2.circle(img1_mark, (sx, cy), 15, (0, 0, 255), 2)
                    cv2.circle(img2_mark, (sx, cy), 15, (0, 0, 255), 2)
                    info.append({
                        "room": room,
                        "day": day,
                        "day_num": day_num,
                        "is_urgent": is_urgent,
                        "status_before": before,
                        "status_after": after,
                        "x": sx,
                        "y": cy,
                    })
        after_path_mark = None
        if changed:
            marked_dir = os.path.join(cfg["SAVE_DIR"], cfg["MARKED_SUBDIR"])
            before_path_mark = os.path.join(marked_dir, f"{timestamp}_전_marked.png")
            after_path_mark = os.path.join(marked_dir, f"{timestamp}_후_marked.png")
            cv2_imwrite_unicode(before_path_mark, img1_mark)
            cv2_imwrite_unicode(after_path_mark, img2_mark)
        return changed, info, after_path_mark
    except Exception as e:
        print(f"❌ 차이 분석 오류: {e}")
        return False, [], None

# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------

def test_notification():
    """Simulate a status change notification to verify filtering logic.
    This runs only in TEST_MODE and does not require Selenium or network.
    """
    site = "수락휴"
    cfg = SITE_CONFIG[site]
    
    test_cases = [
        # 1. 5일 (긴급일자) 예약대기 발생 -> 텔레그램 전송 대상
        {
            "room": "[본동] 17호 수락 638",
            "day": "5일 (토)",
            "day_num": "5",
            "is_urgent": True,
            "status_before": "예약완료(⚪완)",
            "status_after": "대기(🔵대)"
        },
        # 2. 12일 (긴급일자) 예약완료 발생 -> 텔레그램 전송 제외 (로그만 기록)
        {
            "room": "[본동] 18호 산들바람",
            "day": "12일 (토)",
            "day_num": "12",
            "is_urgent": True,
            "status_before": "예약가능(🟢예)",
            "status_after": "예약완료(⚪완)"
        },
        # 3. 15일 (일반일자) 예약가능 발생 -> 긴급일자 아니므로 텔레그램 전송 제외 (로그만 기록)
        {
            "room": "[본동] 19호 풍경소리",
            "day": "15일 (화)",
            "day_num": "15",
            "is_urgent": False,
            "status_before": "예약완료(⚪완)",
            "status_after": "예약가능(🟢예)"
        }
    ]

    print(f"\n--- [테스트 1] 전체 변경 건 로그 기록 테스트 ---")
    append_to_history_log(datetime.now().strftime('%Y-%m-%d %H:%M:%S'), test_cases, cfg)

    print(f"\n--- [테스트 2] 텔레그램 필터링 테스트 (긴급일자: {', '.join(cfg['URGENT_TARGET_DAYS'])}일) ---")
    urgent_alerts = [
        item for item in test_cases
        if item.get('is_urgent') and not item['status_after'].startswith('예약완료')
    ]

    for item in test_cases:
        desc = f"{item['room']} {item['day']} ({item['status_before']} → {item['status_after']})"
        if item.get('is_urgent') and not item['status_after'].startswith('예약완료'):
            print(f"✅ [전송 대상] {desc} -> 텔레그램 전송 진행")
        elif item['status_after'].startswith('예약완료'):
            print(f"🚫 [전송 제외] {desc} -> '예약완료' 변동은 텔레그램 미전송 (로그만 기록)")
        else:
            print(f"🚫 [전송 제외] {desc} -> 긴급일자 외 변동은 텔레그램 미전송 (로그만 기록)")

    if urgent_alerts:
        alert_lines = [
            f"🚨 [{site} 12월 긴급 예약 변동 알림]",
            f"⏰ 시각: {datetime.now().strftime('%H:%M:%S')}\n"
        ]
        for u in urgent_alerts:
            alert_lines.append(f"👉 {u['room']} {u['day']} : {u['status_before']} → {u['status_after']}")
        alert_msg = "\n".join(alert_lines).strip()
        send_telegram_photo('dummy_marked.png', caption=alert_msg)
    return

def main():
    site = sys.argv[1] if len(sys.argv) > 1 else "수락휴"
    if site not in SITE_CONFIG:
        print(f"지원되지 않는 사이트: {site}. 가능한 값: {list(SITE_CONFIG.keys())}")
        sys.exit(1)
    cfg = SITE_CONFIG[site]
    cfg["DATE_STEP_X"] = (cfg["CELL_LAST_X"] - cfg["CELL_FIRST_X"]) / float(cfg["DAYS_IN_MONTH"] - 1)

    setup_directories(cfg)
    start_msg = f"🚀 {site} 12월 예약 현황 모니터링 시작 (긴급: {', '.join(cfg['URGENT_TARGET_DAYS'])}일 / 주기: {INTERVAL_SECONDS}s)"
    send_telegram_message(start_msg)
    print(start_msg)
    prev_path = None
    while True:
        now = datetime.now()
        ts = now.strftime("%Y%m%d_%H%M%S")
        alias = SITE_ALIAS.get(site, site)
        filename = f"{alias}_{ts}.png"
        cur_path = os.path.join(cfg["SAVE_DIR"], filename)
        print(f"\n[{now}] 스크린샷 촬영 중 …")
        if not capture_target_screenshot(cfg, cur_path) or not is_screenshot_valid(cur_path, cfg):
            print("⚠️ 캡처 실패 또는 이미지 유효성 검사 실패 – 다음 라운드로 넘어갑니다.")
            if os.path.exists(cur_path):
                os.remove(cur_path)
            time.sleep(INTERVAL_SECONDS)
            continue
        if prev_path:
            changed, diff_info, after_mark_path = mark_exact_differences(prev_path, cur_path, cfg, ts)
            if changed:
                # 1) 항상 로그 파일에 변경 이력 기록 (상세 및 방별 누적)
                time_str = now.strftime('%Y-%m-%d %H:%M:%S')
                append_to_history_log(time_str, diff_info, cfg)
                # GitHub에 HTML 보고서 커밋 및 푸시
                ensure_git_repo()
                txt_path = os.path.join(cfg["SAVE_DIR"], cfg["ROOM_HISTORY_LOG"])
                html_path = os.path.join(cfg["SAVE_DIR"], "room_history_report.html")
                generate_html_report(txt_path, html_path)
                git_commit_and_push(site, txt_path, html_path)

                # 콘솔 출력
                print("\n" + "="*50)
                print(f"🎯 [{site} 12월 예약 변동 감지 - 총 {len(diff_info)}건]")
                for item in diff_info:
                    tag = " 🚨[긴급!]" if item.get('is_urgent') else ""
                    print(f"🏠 {item['room']} | 📅 {item['day']} : {item['status_before']} ➔ {item['status_after']}{tag}")
                print("="*50 + "\n")

                # 2) 텔레그램 전송 필터링:
                # - 긴급 타깃 일자(URGENT_TARGET_DAYS: 5, 12, 25, 26)에 해당하고,
                # - '예약완료'로의 변경이 아닌 건만 텔레그램으로 전송
                urgent_alerts = [
                    item for item in diff_info
                    if item.get('is_urgent') and not item['status_after'].startswith('예약완료')
                ]

                if urgent_alerts:
                    alert_lines = [
                        f"🚨 [{site} 12월 긴급 예약 변동 알림]",
                        f"⏰ 시각: {now.strftime('%H:%M:%S')}\n"
                    ]
                    for u in urgent_alerts:
                        alert_lines.append(f"👉 {u['room']} {u['day']} : {u['status_before']} → {u['status_after']}")

                    alert_msg = "\n".join(alert_lines).strip()
                    photo_to_send = after_mark_path if (after_mark_path and os.path.exists(after_mark_path)) else cur_path
                    send_telegram_photo(photo_to_send, caption=alert_msg)
                else:
                    print(f"[INFO] 긴급 알림일({', '.join(cfg['URGENT_TARGET_DAYS'])}일) 외 변동 또는 예약완료 – 텔레그램 전송 생략 (로그 파일만 기록됨)")

        prev_path = cur_path
        time.sleep(INTERVAL_SECONDS)

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "test_notification":
        test_notification()
    else:
        main()