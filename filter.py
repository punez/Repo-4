import requests
import base64
import json
import urllib.parse
import random
from datetime import datetime

# ==================== تنظیمات ====================
SUB_SOURCES_URL = "https://raw.githubusercontent.com/punez/Repo-4/refs/heads/main/inputs.txt"  # ← در هر ریپو این خط را تغییر بده
OUTPUT_FILE = "final_sub.txt"          # نام فایل خروجی (همون قبلی)
MAX_OUTPUT = 15000                     # سقف نرم — اگر بیشتر شد هم نگه می‌دارد

# =================================================

def log(msg):
    ts = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    print(f"[{ts}] {msg}")

def fetch_sources():
    try:
        r = requests.get(SUB_SOURCES_URL, timeout=15)
        r.raise_for_status()
        urls = [line.strip() for line in r.text.splitlines() if line.strip() and not line.startswith("#")]
        log(f"Found {len(urls)} subscription URLs")
        return urls
    except Exception as e:
        log(f"Error fetching sources.txt: {e}")
        return []

def fetch_and_decode(url):
    try:
        r = requests.get(url.strip(), timeout=20)
        r.raise_for_status()
        content = r.text.strip()

        # اگر base64 باشد decode کن
        try:
            decoded = base64.b64decode(content + "===").decode("utf-8", errors="ignore")
            if "\n" in decoded or "://" in decoded:
                return decoded.splitlines()
        except:
            pass
        return content.splitlines()
    except Exception as e:
        log(f"Failed to fetch {url}: {e}")
        return []

def get_fingerprint(line):
    """کلید dedup بدون در نظر گرفتن SNI (اگر فقط SNI متفاوت باشد → duplicate حساب می‌شود)"""
    line = line.strip()
    if not line:
        return None

    try:
        if line.startswith("vmess://"):
            b64 = line[8:].split("#")[0]
            data = json.loads(base64.b64decode(b64 + "===").decode("utf-8", errors="ignore"))
            return "|".join(str(x).lower() for x in [
                data.get("add", ""), 
                data.get("port", ""),
                data.get("id", ""),
                data.get("fp", ""),
                data.get("path", ""),
                data.get("net", ""),
                data.get("security", ""),
                data.get("type", "")
                # sni / host عمداً اینجا نیست → اگر فقط sni متفاوت باشد duplicate حساب می‌شود
            ])

        elif line.startswith(("vless://", "trojan://")):
            url = urllib.parse.urlparse(line.split("#")[0])
            params = urllib.parse.parse_qs(url.query)
            return "|".join(str(x).lower() for x in [
                url.hostname or "",
                url.port or "443",
                url.username or "",
                params.get("fp", [""])[0],
                params.get("path", [""])[0] or params.get("serviceName", [""])[0],
                params.get("type", [""])[0],
                params.get("security", [""])[0]
                # sni / peer عمداً حذف شده → اگر فقط sni متفاوت باشد duplicate حساب می‌شود
            ])

        else:  # ss, hy2, tuic و پروتکل‌های ساده‌تر
            # این‌ها معمولاً SNI ندارند → کل لینک بدون remark
            return line.split("#")[0].lower()

    except Exception as e:
        # در صورت خطا در parse → fallback به لینک بدون remark
        return line.split("#")[0].lower()

# ==================== اجرای اصلی ====================

log("=== Starting Process Sub (Repo 1-4) ===")

all_lines = []
for sub_url in fetch_sources():
    lines = fetch_and_decode(sub_url)
    all_lines.extend(lines)

log(f"Total raw lines collected: {len(all_lines)}")

# dedup: اگر فقط SNI متفاوت باشد → یکی نگه داشته می‌شود
seen = {}
for line in all_lines:
    key = get_fingerprint(line)
    if key and key not in seen:
        seen[key] = line

unique_nodes = list(seen.values())

# shuffle برای تنوع بیشتر در خروجی
random.shuffle(unique_nodes)

# محدود به سقف (اگر لازم شد)
final_list = unique_nodes[:MAX_OUTPUT]

with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    for node in final_list:
        f.write(node + "\n")

log(f"Done! Final output: {len(final_list)} unique nodes → {OUTPUT_FILE}")
log("Ready for Repo5 to combine and perform TCP test")
