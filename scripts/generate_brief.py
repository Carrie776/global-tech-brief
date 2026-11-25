import html
import json
import os
from pathlib import Path
from google import genai
from google.genai import types

OUTLET_ORDER = [
    ("01", "Reuters 路透社"),
    ("02", "Bloomberg 彭博"),
    ("03", "Nikkei Asia 日经亚洲"),
    ("04", "Yahoo Finance 雅虎财经"),
    ("05", "Wccftech"),
    ("06", "Economic Times 印度经济时报"),
    ("07", "爱集微"),
    ("08", "IT之家"),
    ("09", "新浪财经"),
    ("10", "DIGITIMES"),
    ("11", "TechNews 科技新报"),
    ("12", "经济日报（台湾）"),
    ("13", "工商时报（台湾）"),
]

RESPONSE_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "kouzhaoge_note": {"type": "STRING"},
        "focus_items": {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "title": {"type": "STRING"},
                    "bullets": {"type": "ARRAY", "items": {"type": "STRING"}},
                    "source_label": {"type": "STRING"},
                    "url": {"type": "STRING"},
                },
                "required": ["title", "bullets", "source_label", "url"],
            },
        },
        "sections": {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "id": {"type": "STRING"},
                    "name": {"type": "STRING"},
                    "items": {
                        "type": "ARRAY",
                        "items": {
                            "type": "OBJECT",
                            "properties": {
                                "title": {"type": "STRING"},
                                "bullets": {"type": "ARRAY", "items": {"type": "STRING"}},
                                "source_label": {"type": "STRING"},
                                "url": {"type": "STRING"},
                            },
                            "required": ["title", "bullets", "source_label", "url"],
                        },
                    },
                },
                "required": ["id", "name", "items"],
            },
        },
    },
    "required": ["kouzhaoge_note", "focus_items", "sections"],
}


def render_card(item: dict) -> str:
    title = html.escape(item["title"])
    bullets_html = "".join(
        f'<p class="bullet">• {html.escape(b.lstrip("• ").strip())}</p>'
        for b in item.get("bullets", [])[:2]
    )
    src = html.escape(item["source_label"])
    url = html.escape(item["url"], quote=True)
    return (
        '<article class="card">'
        f'<h3 class="card-title">⭐{title}</h3>'
        f'{bullets_html}'
        f'<p class="source"><a href="{url}" target="_blank" rel="noopener noreferrer">{src}</a></p>'
        '</article>'
    )


def build_html(meta: dict, data: dict, is_draft: bool) -> str:
    issue_code = meta["issue_date_bj"]
    window_str = f'{meta["window_start_la"]} 至 {meta["window_end_la"]} ({meta["timezone"]})'
    draft_banner = (
        '<div class="draft-banner">内部核验稿（部分站点未满5条，尚未正式对外发布）</div>'
        if is_draft
        else ""
    )

    nav_links = ['<a href="#focus">重点追踪</a>']
    sections_html = []

    focus_cards = "".join(render_card(it) for it in data.get("focus_items", []))
    sections_html.append(
        f'<section id="focus" class="group">'
        f'<h2 class="group-title">重点追踪</h2>'
        f'{focus_cards or "<p class=empty>本期暂无已核实的重点追踪条目。</p>"}'
        f'</section>'
    )

    sec_map = {s["id"]: s for s in data.get("sections", [])}
    for sid, sname in OUTLET_ORDER:
        sec = sec_map.get(sid, {"id": sid, "name": sname, "items": []})
        items = sec.get("items", [])
        nav_links.append(f'<a href="#sec-{sid}">{html.escape(sname)} ({len(items)})</a>')
        cards = "".join(render_card(it) for it in items)
        sections_html.append(
            f'<section id="sec-{sid}" class="group">'
            f'<h2 class="group-title">{sid} {html.escape(sname)}</h2>'
            f'{cards or "<p class=empty>本期窗口内无可核实新闻。</p>"}'
            f'</section>'
        )

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>【科技】全球科技产业观察 {issue_code}</title>
<style>
  :root {{ --bg:#f6f7f9; --card:#ffffff; --text:#1f2329; --muted:#646a73; --accent:#0b57d0; --border:#e5e7eb; }}
  * {{ box-sizing:border-box; }}
  body {{ margin:0; font-family:-apple-system,BlinkMacSystemFont,"PingFang SC","Microsoft YaHei",sans-serif; background:var(--bg); color:var(--text); line-height:1.6; }}
  .wrap {{ max-width:760px; margin:0 auto; padding:16px 14px 40px; }}
  header {{ background:linear-gradient(135deg,#0f2942,#1b4d7e); color:#fff; border-radius:12px; padding:18px 16px; margin-bottom:14px; }}
  header h1 {{ margin:0 0 6px; font-size:20px; letter-spacing:0.3px; }}
  .meta {{ font-size:12px; opacity:0.9; margin:0; }}
  .draft-banner {{ background:#fff3cd; color:#856404; border:1px solid #ffeeba; border-radius:8px; padding:10px 12px; font-size:13px; margin-bottom:12px; font-weight:600; }}
  .nav {{ display:flex; flex-wrap:wrap; gap:6px; margin-bottom:16px; }}
  .nav a {{ font-size:12px; color:#334155; background:#fff; border:1px solid var(--border); border-radius:999px; padding:4px 10px; text-decoration:none; }}
  .group {{ margin-bottom:22px; }}
  .group-title {{ font-size:16px; color:#0f2942; border-left:4px solid var(--accent); padding-left:10px; margin:0 0 10px; }}
  .card {{ background:var(--card); border:1px solid var(--border); border-radius:10px; padding:12px 14px; margin-bottom:10px; }}
  .card-title {{ margin:0 0 6px; font-size:15px; line-height:1.45; }}
  .bullet {{ margin:3px 0; font-size:13.5px; color:#374151; }}
  .source {{ margin:8px 0 0; font-size:12.5px; }}
  .source a {{ color:var(--accent); text-decoration:none; font-weight:500; }}
  .empty {{ font-size:13px; color:var(--muted); padding:8px 4px; }}
  footer {{ text-align:center; color:var(--muted); font-size:13px; margin-top:28px; padding-top:14px; border-top:1px solid var(--border); }}
</style>
</head>
<body>
<div class="wrap">
  <header>
    <h1>【科技】全球科技产业观察 {issue_code}</h1>
    <p class="meta">覆盖区间：{html.escape(window_str)}</p>
  </header>
  {draft_banner}
  <nav class="nav">{"".join(nav_links)}</nav>
  {"".join(sections_html)}
  <footer>科技团队</footer>
</div>
</body>
</html>
"""


def build_wechat_text(meta: dict, data: dict, live_url: str) -> str:
    lines = [f"【科技】全球科技产业观察 {meta['issue_date_bj']}", ""]
    for item in data.get("focus_items", []):
        lines.append(f"⭐{item['title']}")
        for b in item.get("bullets", [])[:2]:
            lines.append(f"• {b.lstrip('• ').strip()}")
        lines.append(item["url"])
        lines.append("")
    lines.append("科技团队")
    lines.append(live_url)
    return "\n".join(lines).strip() + "\n"


def main():
    api_key = os.environ["GEMINI_API_KEY"]
    model_name = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    site_base = os.getenv("SITE_BASE_URL", "https://example.github.io/global-tech-brief").rstrip("/")

    candidates = json.loads(Path("data/candidates.json").read_text(encoding="utf-8"))
    rules = Path("rules/prompt_rules.md").read_text(encoding="utf-8")

    prompt = (
        f"{rules}\n\n"
        f"以下是本期抓取到的候选新闻 JSON，请严格按规则筛选、核验、去重并输出 JSON：\n"
        f"{json.dumps(candidates, ensure_ascii=False)}"
    )

    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(
        model=model_name,
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=RESPONSE_SCHEMA,
            temperature=0.1,
        ),
    )

    result = json.loads(response.text)
    meta = candidates["meta"]
    issue_date_iso = meta["issue_date_la"]

    sec_map = {s["id"]: s for s in result.get("sections", [])}
    shortfalls = []
    counts = {}
    for sid, sname in OUTLET_ORDER:
        cnt = len(sec_map.get(sid, {}).get("items", []))
        counts[f"{sid} {sname}"] = cnt
        if cnt < 5:
            shortfalls.append(f"{sid} {sname}: 仅 {cnt} 条")

    threshold_met = len(shortfalls) == 0
    is_published = threshold_met


    html_content = build_html(meta, result, is_draft=not is_published)

    if is_published:
        Path("docs/reports").mkdir(parents=True, exist_ok=True)
        report_rel = f"reports/{issue_date_iso}.html"
        Path(f"docs/{report_rel}").write_text(html_content, encoding="utf-8")
        Path("docs/index.html").write_text(html_content, encoding="utf-8")
        live_url = f"{site_base}/{report_rel}"
        html_path = f"docs/{report_rel}"
    else:
        html_path = f"data/{issue_date_iso}-internal.html"
        Path(html_path).write_text(html_content, encoding="utf-8")
        live_url = ""

    wechat_text = build_wechat_text(meta, result, live_url)
    Path("data/wechat_text.txt").write_text(wechat_text, encoding="utf-8")

    status = {
        "issue_date_bj": meta["issue_date_bj"],
        "issue_date_la": issue_date_iso,
        "window": f"{meta['window_start_la']} ~ {meta['window_end_la']}",
        "threshold_met": threshold_met,
        "published_to_homepage": is_published,
        "live_url": live_url,
        "html_path": html_path,
        "focus_count": len(result.get("focus_items", [])),
        "outlet_counts": counts,
        "shortfalls": shortfalls,
        "kouzhaoge_note": result.get("kouzhaoge_note", ""),
    }
    Path("data/latest_status.json").write_text(
        json.dumps(status, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"[generate_brief] Done. threshold_met={threshold_met}, live_url={live_url}")


if __name__ == "__main__":
    main()
