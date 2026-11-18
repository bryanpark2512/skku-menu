"""성균관대 인사캠 학식(은행골식당, 금잔디식당) 오늘 메뉴를 가져와 알려준다."""
import argparse
import datetime as dt
import os
import re
import sys
from zoneinfo import ZoneInfo

import requests
from bs4 import BeautifulSoup

BASE = "https://www.skku.edu/skku/campus/support/welfare_11.do"
RESTAURANTS = {
    "은행골식당": {"conspaceCd": "10201031", "srResId": "2"},
    "금잔디식당": {"conspaceCd": "10201033", "srResId": "6"},
}
HEADERS = {"User-Agent": "Mozilla/5.0 (skku-menu-bot)"}


def fetch_week(ids: dict) -> str:
    # srShowTime=W: 이번 주 전체, srCategory=L: 중식
    params = {"mode": "info", **ids, "srShowTime": "W", "srCategory": "L"}
    r = requests.get(BASE, params=params, headers=HEADERS, timeout=20)
    r.raise_for_status()
    return r.text


def parse_week(html: str) -> dict:
    """{(월, 일): (라벨, [(코너명, [메뉴 줄...]), ...])} 를 돌려준다."""
    soup = BeautifulSoup(html, "html.parser")
    week = {}
    for wrap in soup.select(".weekly_list .weeListWrap"):
        title = wrap.select_one(".weeListTit").get_text(" ", strip=True)
        m = re.search(r"\((\d{1,2})\.(\d{1,2})\)", title)
        if not m:
            continue
        corners = []
        for c in wrap.select(".weeListCont"):
            name = re.sub(r"\s*코너$", "", c.select_one("h6").get_text(" ", strip=True))
            lines = []
            for pre in c.select("ul li pre"):
                lines += [ln.strip() for ln in pre.get_text().splitlines() if ln.strip()]
            if lines:
                corners.append((name, lines))
        week[(int(m.group(1)), int(m.group(2)))] = (title, corners)
    return week


def format_message(day: tuple, weeks: dict):
    blocks, label = [], None
    for rname, week in weeks.items():
        title, corners = week.get(day, (None, []))
        label = label or title
        if not corners:
            continue
        rows = [f"{n}: {' · '.join(lines)}" for n, lines in corners]
        blocks.append(f"[{rname}]\n" + "\n".join(rows))
    if not blocks:
        return None
    return f"오늘 학식 · {label}\n\n" + "\n\n".join(blocks)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", help="MM-DD (기본: 서울 기준 오늘)")
    args = ap.parse_args()
    if args.date:
        mm, dd = map(int, args.date.split("-"))
        day = (mm, dd)
    else:
        now = dt.datetime.now(ZoneInfo("Asia/Seoul"))
        day = (now.month, now.day)
    weeks = {name: parse_week(fetch_week(ids)) for name, ids in RESTAURANTS.items()}
    msg = format_message(day, weeks)
    print(msg or "오늘은 두 식당 모두 메뉴가 없습니다.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
