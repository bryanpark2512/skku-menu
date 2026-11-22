"""이번 주 학식 메뉴를 정적 HTML 한 장(public/index.html)으로 만든다."""
import argparse
import datetime as dt
import html
import re
from pathlib import Path
from zoneinfo import ZoneInfo

from menu import RESTAURANTS, fetch_week, parse_week

SOURCE = "https://www.skku.edu/skku/campus/support/welfare_11.do"


def line_html(line: str) -> str:
    if re.fullmatch(r"\d{4,5}", line):
        return f'<li class="price">{int(line):,}원</li>'
    m = re.fullmatch(r"(.*\S)\s+(\d{4,5})", line)
    if m:
        return f'<li>{html.escape(m.group(1))}<span class="price">{int(m.group(2)):,}원</span></li>'
    return f"<li>{html.escape(line)}</li>"


def collect_weeks(now: dt.datetime, fetch=fetch_week):
    """토·일에는 다음 주 월요일 기준으로 가져온다.
    두 식당 모두 다음 주 메뉴가 있을 때만 다음 주를 쓰고, 아니면 두 식당 모두 이번 주로 되돌린다."""
    if now.weekday() >= 5:  # 5=토, 6=일
        monday = (now + dt.timedelta(days=7 - now.weekday())).date()
        key = (monday.month, monday.day)
        nxt = {n: parse_week(fetch(ids, monday)) for n, ids in RESTAURANTS.items()}
        if all(key in w and any(c for _, c in w.values()) for w in nxt.values()):
            return nxt, True
    return {n: parse_week(fetch(ids)) for n, ids in RESTAURANTS.items()}, False


def build(weeks: dict, now: dt.datetime, note: str = "") -> str:
    days = []
    titles = {}
    for week in weeks.values():
        for key, (title, _) in week.items():
            if key not in titles:
                titles[key] = title
                days.append(key)

    chips, panels = [], []
    for key in days:
        md = f"{key[0]:02d}-{key[1]:02d}"
        chips.append(f'<button class="chip" data-md="{md}">{html.escape(titles[key])}</button>')
        sections = []
        for rname, week in weeks.items():
            corners = week.get(key, (None, []))[1]
            if corners:
                cards = "".join(
                    f'<div class="card"><h3>{html.escape(n)}</h3><ul>'
                    + "".join(line_html(l) for l in lines)
                    + "</ul></div>"
                    for n, lines in corners
                )
            else:
                cards = '<p class="empty">운영 없음 또는 메뉴 미등록</p>'
            sections.append(f"<section><h2>{html.escape(rname)}</h2>{cards}</section>")
        panels.append(f'<div class="panel" data-md="{md}">{"".join(sections)}</div>')

    updated = now.strftime("%m/%d %H:%M")
    return TEMPLATE.format(chips="".join(chips), panels="".join(panels), updated=updated, source=SOURCE, note=note)


TEMPLATE = """<!doctype html>
<html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>성균관대 학식 · 은행골 / 금잔디</title>
<style>
:root{{--bg:#f6f5f1;--fg:#1d1d1b;--mute:#777;--card:#fff;--line:#e4e2da;--accent:#0b5d3b}}
@media(prefers-color-scheme:dark){{:root{{--bg:#141413;--fg:#eeeee9;--mute:#9a9a92;--card:#1f1f1d;--line:#34332f;--accent:#7fd1a5}}}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--bg);color:var(--fg);font:16px/1.5 -apple-system,"Apple SD Gothic Neo","Noto Sans KR",sans-serif}}
main{{max-width:640px;margin:0 auto;padding:20px 16px 48px}}
h1{{font-size:20px;margin:4px 0 14px}}
.chips{{display:flex;gap:6px;overflow-x:auto;padding-bottom:6px}}
.chip{{flex:none;border:1px solid var(--line);background:var(--card);color:var(--fg);border-radius:999px;padding:6px 12px;font:inherit;font-size:14px}}
.chip.on{{background:var(--accent);border-color:var(--accent);color:#fff}}
.chip.today::after{{content:" ·오늘";font-size:12px}}
.panel{{display:none}}.panel.on{{display:block}}
section{{margin-top:22px}}
h2{{font-size:17px;margin:0 0 8px;color:var(--accent)}}
.card{{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:10px 14px;margin-bottom:8px}}
.card h3{{font-size:14px;margin:0 0 4px;color:var(--mute);font-weight:600}}
ul{{list-style:none;margin:0;padding:0}}
li{{display:flex;justify-content:space-between;gap:12px;padding:2px 0}}
li.price{{justify-content:flex-end}}
.price{{color:var(--mute);font-size:14px;white-space:nowrap}}
.empty{{color:var(--mute);font-size:14px}}
footer{{margin-top:28px;color:var(--mute);font-size:12px}}
footer a{{color:inherit}}
</style></head><body><main>
<h1>성균관대 학식 · 중식{note}</h1>
<div class="chips">{chips}</div>
{panels}
<footer>마지막 갱신 {updated} (KST) · 학교 사이트 기준이라 식당 사정으로 바뀔 수 있어요 · <a href="{source}">원본</a></footer>
</main>
<script>
const kst=new Date(new Date().toLocaleString("en-US",{{timeZone:"Asia/Seoul"}}));
const today=String(kst.getMonth()+1).padStart(2,"0")+"-"+String(kst.getDate()).padStart(2,"0");
const chips=[...document.querySelectorAll(".chip")],panels=[...document.querySelectorAll(".panel")];
function pick(md){{chips.forEach(c=>c.classList.toggle("on",c.dataset.md===md));panels.forEach(p=>p.classList.toggle("on",p.dataset.md===md));}}
chips.forEach(c=>{{if(c.dataset.md===today)c.classList.add("today");c.onclick=()=>pick(c.dataset.md)}});
pick(chips.some(c=>c.dataset.md===today)?today:(chips[0]||{{dataset:{{}}}}).dataset.md);
</script></body></html>
"""


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("-o", "--out", default="public/index.html")
    args = ap.parse_args()
    now = dt.datetime.now(ZoneInfo("Asia/Seoul"))
    weeks, is_next = collect_weeks(now)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(build(weeks, now, " · 다음 주" if is_next else ""), encoding="utf-8")
    print("wrote", out)


if __name__ == "__main__":
    main()
