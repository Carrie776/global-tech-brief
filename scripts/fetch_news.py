import concurrent.futures
import json
import os
import re
import time
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from urllib.parse import quote_plus

import feedparser
import requests
from bs4 import BeautifulSoup
from dateutil import parser as date_parser

try:
    from googlenewsdecoder import new_decoderv1
except Exception:
    new_decoderv1 = None


def decode_gnews_url(url: str) -> str:
    """Resolve Google News RSS redirect URLs to real publisher URLs."""
    if not url or "news.google.com/rss/articles/" not in url or new_decoderv1 is None:
        return url
    try:
        res = new_decoderv1(url, interval=0)
        if isinstance(res, dict) and res.get("status") and res.get("decoded_url"):
            decoded = res["decoded_url"].strip()
            if decoded.startswith("http"):
                return decoded
    except Exception:
        pass
    return url

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/129.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7",
}

TIMEOUT = 15

# 13 家固定媒体配置（主 RSS / 公开入口 + 域名限定补搜 RSS）
OUTLETS = [
    {
        "id": "01",
        "name": "Reuters 路透社",
        "feeds": [
            "https://news.google.com/rss/search?q=site:reuters.com/technology+when:2d&hl=en-US&gl=US&ceid=US:en",
            "https://news.google.com/rss/search?q=site:reuters.com+(semiconductor+OR+AI+OR+Nvidia+OR+TSMC+OR+Apple)+when:2d&hl=en-US&gl=US&ceid=US:en",
        ],
    },
    {
        "id": "02",
        "name": "Bloomberg 彭博",
        "feeds": [
            "https://feeds.bloomberg.com/technology/news.rss",
            "https://news.google.com/rss/search?q=site:bloomberg.com/news/articles+(AI+OR+chip+OR+tech+OR+Nvidia+OR+Apple)+when:2d&hl=en-US&gl=US&ceid=US:en",
        ],
    },
    {
        "id": "03",
        "name": "Nikkei Asia 日经亚洲",
        "feeds": [
            "https://asia.nikkei.com/rss/feed/nar",
            "https://news.google.com/rss/search?q=site:asia.nikkei.com/Business/Tech+when:2d&hl=en-US&gl=US&ceid=US:en",
            "https://news.google.com/rss/search?q=site:asia.nikkei.com+(chip+OR+semiconductor+OR+AI+OR+TSMC+OR+Samsung)+when:2d&hl=en-US&gl=US&ceid=US:en",
        ],
    },
    {
        "id": "04",
        "name": "Yahoo Finance 雅虎财经",
        "feeds": [
            "https://finance.yahoo.com/news/rssindex",
            "https://news.google.com/rss/search?q=site:finance.yahoo.com/news+(Nvidia+OR+AMD+OR+TSMC+OR+AI+OR+Apple+OR+Broadcom)+when:2d&hl=en-US&gl=US&ceid=US:en",
        ],
    },
    {
        "id": "05",
        "name": "Wccftech",
        "feeds": [
            "https://wccftech.com/feed/",
            "https://news.google.com/rss/search?q=site:wccftech.com+when:2d&hl=en-US&gl=US&ceid=US:en",
        ],
    },
    {
        "id": "06",
        "name": "Economic Times 印度经济时报",
        "feeds": [
            "https://economictimes.indiatimes.com/tech/rssfeeds/13357270.cms",
            "https://news.google.com/rss/search?q=site:economictimes.indiatimes.com/tech+when:2d&hl=en-IN&gl=IN&ceid=IN:en",
        ],
    },
    {
        "id": "07",
        "name": "爱集微",
        "feeds": [
            "https://news.google.com/rss/search?q=site:laoyaoba.com+when:2d&hl=zh-CN&gl=CN&ceid=CN:zh-Hans",
            "https://news.google.com/rss/search?q=site:jw.ijiwei.com+when:2d&hl=zh-CN&gl=CN&ceid=CN:zh-Hans",
        ],
    },
    {
        "id": "08",
        "name": "IT之家",
        "feeds": [
            "https://www.ithome.com/rss/",
        ],
    },
    {
        "id": "09",
        "name": "新浪财经",
        "feeds": [
            "https://news.google.com/rss/search?q=site:finance.sina.com.cn+(芯片+OR+半导体+OR+算力+OR+光模块+OR+存储+OR+英伟达+OR+台积电)+when:2d&hl=zh-CN&gl=CN&ceid=CN:zh-Hans",
            "https://news.google.com/rss/search?q=site:finance.sina.com.cn+(小米+OR+中芯国际+OR+寒武纪+OR+中际旭创+OR+北方华创+OR+立讯精密)+when:2d&hl=zh-CN&gl=CN&ceid=CN:zh-Hans",
        ],
    },
    {
        "id": "10",
        "name": "DIGITIMES",
        "feeds": [
            "https://www.digitimes.com/rss/daily.xml",
            "https://news.google.com/rss/search?q=site:digitimes.com.tw+when:2d&hl=zh-TW&gl=TW&ceid=TW:zh-Hant",
            "https://news.google.com/rss/search?q=site:digitimes.com+when:2d&hl=en-US&gl=US&ceid=US:en",
        ],
    },
    {
        "id": "11",
        "name": "TechNews 科技新报",
        "feeds": [
            "https://technews.tw/feed/",
        ],
    },
    {
        "id": "12",
        "name": "经济日报（台湾）",
        "feeds": [
            "https://money.udn.com/rssfeed/news/1001/5591?ch=money",
            "https://news.google.com/rss/search?q=site:money.udn.com+(半導體+OR+台積電+OR+鴻海+OR+聯發科+OR+AI伺服器+OR+記憶體)+when:2d&hl=zh-TW&gl=TW&ceid=TW:zh-Hant",
        ],
    },
    {
        "id": "13",
        "name": "工商时报（台湾）",
        "feeds": [
            "https://www.ctee.com.tw/rss_web/livenews/tech",
            "https://www.ctee.com.tw/rss_web/livenews/industry",
            "https://news.google.com/rss/search?q=site:ctee.com.tw+(半導體+OR+台積電+OR+AI+OR+光通訊+OR+記憶體)+when:2d&hl=zh-TW&gl=TW&ceid=TW:zh-Hant",
        ],
    },
]

# 5大核心赛道与重点公司主动补搜
THEME_QUERIES = [
    "HBM OR DRAM OR NAND memory supercycle Samsung SK Hynix Micron",
    "optical transceiver OR co-packaged optics OR 中际旭创 OR 新易盛 OR 天孚通信",
    "AI data center power OR liquid cooling OR custom ASIC Broadcom MediaTek",
    "SMIC OR CXMT OR NAURA OR Cambricon OR Xiaomi OR Foxconn semiconductor",
]


def clean_html(text: str, max_len: int = 320) -> str:
    if not text:
        return ""
    soup = BeautifulSoup(text, "html.parser")
    cleaned = re.sub(r"\s+", " ", soup.get_text(" ", strip=True)).strip()
    return cleaned[:max_len]


def parse_dt(entry):
    for key in ("published", "updated", "created"):
        val = entry.get(key)
        if val:
            try:
                dt = date_parser.parse(val)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt.astimezone(timezone.utc)
            except Exception:
                pass
    for key in ("published_parsed", "updated_parsed"):
        st = entry.get(key)
        if st:
            try:
                return datetime(*st[:6], tzinfo=timezone.utc)
            except Exception:
                pass
    return None


def fetch_feed(url: str):
    try:
        resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        resp.raise_for_status()
        parsed = feedparser.parse(resp.content)
        items = []
        for e in parsed.entries[:40]:
            link = e.get("link", "").strip()
            title = clean_html(e.get("title", ""), 180)
            if not link or not title:
                continue
            if "tomshardware.com" in link.lower():
                continue
            dt = parse_dt(e)
            author = e.get("author", "") or (
                e.get("source", {}).get("title", "") if isinstance(e.get("source"), dict) else ""
            )
            summary = clean_html(e.get("summary", "") or e.get("description", ""), 320)
            items.append({
                "title": title,
                "url": link,
                "published_utc": dt.isoformat() if dt else "",
                "author": author.strip(),
                "summary": summary,
                "via_google_news": "news.google.com" in url,
            })
        return items, None
    except Exception as exc:
        return [], str(exc)


def fetch_kouzhaoge() -> dict:
    url = "https://www.jintiankansha.me/column/PZ2qKVVGyT"
    result = {"source_url": url, "status": "ok", "items": [], "error": ""}
    try:
        resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        seen = set()
        for a in soup.find_all("a", href=True):
            text = re.sub(r"\s+", " ", a.get_text(" ", strip=True))
            href = a["href"]
            if len(text) < 8 or href in seen:
                continue
            if "/t/" in href or "article" in href or "item" in href:
                seen.add(href)
                full_url = href if href.startswith("http") else f"https://www.jintiankansha.me{href}"
                result["items"].append({"title": text[:160], "url": full_url})
            if len(result["items"]) >= 15:
                break
        if not result["items"]:
            result["status"] = "empty"
    except Exception as exc:
        result["status"] = "error"
        result["error"] = str(exc)
    return result


def main():
    now_utc = datetime.now(timezone.utc)
    la_tz = ZoneInfo("America/Los_Angeles")
    bj_tz = ZoneInfo("Asia/Shanghai")
    now_la = now_utc.astimezone(la_tz)
    now_bj = now_utc.astimezone(bj_tz)

    # 原排期：北京时间周一早上07:30（对应圣何塞周日下午）取72小时，其余取24小时
    override_hours = os.getenv("LOOKBACK_HOURS", "").strip()
    if override_hours.isdigit():
        lookback_hours = int(override_hours)
    else:
        lookback_hours = 72 if now_bj.weekday() == 0 else 24

    cutoff_start_utc = now_utc - timedelta(hours=lookback_hours)
    cutoff_start_la = cutoff_start_utc.astimezone(la_tz)

    output = {
        "meta": {
            "issue_date_bj": now_bj.strftime("%Y%m%d"),
            "issue_date_la": now_la.strftime("%Y-%m-%d"),
            "timezone": "America/Los_Angeles",
            "window_start_la": cutoff_start_la.strftime("%Y-%m-%d %H:%M %Z"),
            "window_end_la": now_la.strftime("%Y-%m-%d %H:%M %Z"),
            "lookback_hours": lookback_hours,
            "generated_utc": now_utc.isoformat(),
        },
        "kouzhaoge": fetch_kouzhaoge(),
        "outlets": [],
        "theme_supplement": [],
    }

    for outlet in OUTLETS:
        seen_urls = set()
        candidates = []
        errors = []
        for feed_url in outlet["feeds"]:
            items, err = fetch_feed(feed_url)
            if err:
                errors.append({"feed": feed_url, "error": err})
            for item in items:
                if item["url"] in seen_urls:
                    continue
                if item["published_utc"]:
                    pub_dt = datetime.fromisoformat(item["published_utc"])
                    if pub_dt < (cutoff_start_utc - timedelta(hours=2)):
                        continue
                seen_urls.add(item["url"])
                candidates.append(item)
            time.sleep(0.3)

        candidates.sort(key=lambda x: x.get("published_utc", ""), reverse=True)
        output["outlets"].append({
            "id": outlet["id"],
            "name": outlet["name"],
            "candidate_count": len(candidates[:18]),
            "candidates": candidates[:18],
            "errors": errors,
        })

    for q in THEME_QUERIES:
        url = f"https://news.google.com/rss/search?q={quote_plus(q)}+when:2d&hl=en-US&gl=US&ceid=US:en"
        items, _ = fetch_feed(url)
        for item in items[:6]:
            output["theme_supplement"].append(item)
        time.sleep(0.3)

    # 统一将 Google News 跳转链解码为原媒体直链，并分配短编号 cid（防止大模型复制长链接出错）
    all_items = []
    for o in output["outlets"]:
        all_items.extend(o["candidates"])
    all_items.extend(output["theme_supplement"])

    gnews_items = [it for it in all_items if "news.google.com/rss/articles/" in it.get("url", "")]
    if gnews_items and new_decoderv1 is not None:
        print(f"[fetch_news] Decoding {len(gnews_items)} Google News URLs to direct publisher URLs...")
        with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
            decoded_urls = list(pool.map(decode_gnews_url, [it["url"] for it in gnews_items]))
        decoded_ok = 0
        for it, new_u in zip(gnews_items, decoded_urls):
            if new_u != it["url"]:
                it["url"] = new_u
                decoded_ok += 1
        print(f"[fetch_news] Decoded {decoded_ok}/{len(gnews_items)} Google News URLs.")

    # 剔除可能解码后落到被排除域名（如 tomshardware.com）的条目，并分配短 ID
    cid_idx = 1
    for o in output["outlets"]:
        filtered = []
        for it in o["candidates"]:
            if "tomshardware.com" in it.get("url", "").lower():
                continue
            it["cid"] = f"C{cid_idx:03d}"
            cid_idx += 1
            filtered.append(it)
        o["candidates"] = filtered
        o["candidate_count"] = len(filtered)

    filtered_theme = []
    for it in output["theme_supplement"]:
        if "tomshardware.com" in it.get("url", "").lower():
            continue
        it["cid"] = f"C{cid_idx:03d}"
        cid_idx += 1
        filtered_theme.append(it)
    output["theme_supplement"] = filtered_theme

    os.makedirs("data", exist_ok=True)
    with open("data/candidates.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    total = sum(o["candidate_count"] for o in output["outlets"])
    print(f"[fetch_news] Done. Window={lookback_hours}h, Total outlet candidates={total}")


if __name__ == "__main__":
    main()
