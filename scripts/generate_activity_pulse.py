#!/usr/bin/env python3
import json
import math
import os
import urllib.request
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

USERNAME = os.getenv("GITHUB_ACTOR_TARGET", "SevalSorak")
TOKEN = os.getenv("GITHUB_TOKEN", "")
OUT = Path("assets/activity-pulse.svg")
TZ = ZoneInfo("Europe/Istanbul")

def fetch_events():
    events = []
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "sevalsorak-profile-activity-pulse",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if TOKEN:
        headers["Authorization"] = f"Bearer {TOKEN}"

    for page in range(1, 4):
        url = f"https://api.github.com/users/{USERNAME}/events/public?per_page=100&page={page}"
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=30) as response:
            batch = json.load(response)
        if not batch:
            break
        events.extend(batch)
        if len(batch) < 100:
            break
    return events

def event_date(event):
    dt = datetime.fromisoformat(event["created_at"].replace("Z", "+00:00"))
    return dt.astimezone(TZ).date()

def build_activity(events):
    today = datetime.now(TZ).date()
    start = today - timedelta(days=29)
    daily = {start + timedelta(days=i): {"commits": 0, "prs": 0, "issues": 0} for i in range(30)}

    for event in events:
        day = event_date(event)
        if day not in daily:
            continue
        typ = event.get("type")
        payload = event.get("payload") or {}

        if typ == "PushEvent":
            # GitHub public events expose the pushed commit list in payload.commits.
            daily[day]["commits"] += len(payload.get("commits") or [])
        elif typ == "PullRequestEvent":
            action = payload.get("action")
            if action in {"opened", "closed", "reopened", "synchronize"}:
                daily[day]["prs"] += 1
        elif typ == "IssuesEvent":
            action = payload.get("action")
            if action in {"opened", "closed", "reopened"}:
                daily[day]["issues"] += 1

    return daily

def esc(text):
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )

def generate_svg(daily):
    days = list(daily.keys())
    weighted = [
        daily[d]["commits"] + daily[d]["prs"] * 2 + daily[d]["issues"] * 1.5
        for d in days
    ]
    max_value = max(weighted) if max(weighted, default=0) > 0 else 1

    x0, x1 = 70, 1130
    baseline = 248
    max_amp = 105
    step = (x1 - x0) / (len(days) - 1)

    points = []
    for i, value in enumerate(weighted):
        x = x0 + i * step
        y = baseline - (value / max_value) * max_amp
        points.append((x, y))

    # Smooth by drawing a polyline with rounded joins. The data remains exact per day.
    point_str = " ".join(f"{x:.1f},{y:.1f}" for x, y in points)

    total_commits = sum(v["commits"] for v in daily.values())
    total_prs = sum(v["prs"] for v in daily.values())
    total_issues = sum(v["issues"] for v in daily.values())
    active_days = sum(1 for v in weighted if v > 0)
    peak_index = max(range(len(weighted)), key=lambda i: weighted[i]) if weighted else 0
    peak_day = days[peak_index].strftime("%d %b") if weighted and weighted[peak_index] > 0 else "—"

    labels = []
    for idx in [0, 7, 14, 21, 29]:
        d = days[idx]
        x = x0 + idx * step
        labels.append(
            f'<text x="{x:.1f}" y="286" text-anchor="middle" font-size="11" fill="#64748b">{esc(d.strftime("%d %b"))}</text>'
        )

    dots = []
    for i, (x, y) in enumerate(points):
        if weighted[i] <= 0:
            continue
        tooltip = (
            f"{days[i].isoformat()}: "
            f"{daily[days[i]]['commits']} commits, "
            f"{daily[days[i]]['prs']} PR events, "
            f"{daily[days[i]]['issues']} issue events"
        )
        dots.append(
            f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3.2" fill="#e879f9">'
            f'<title>{esc(tooltip)}</title></circle>'
        )

    updated = datetime.now(TZ).strftime("%d %b %Y · %H:%M TRT")

    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 330" width="1200" height="330" role="img" aria-label="GitHub activity pulse for the last 30 days">
<defs>
  <linearGradient id="ap-trace" x1="0" y1="0" x2="1" y2="0">
    <stop offset="0" stop-color="#22d3ee"/>
    <stop offset=".42" stop-color="#8b5cf6"/>
    <stop offset=".72" stop-color="#f472b6"/>
    <stop offset="1" stop-color="#38bdf8"/>
  </linearGradient>
  <linearGradient id="ap-fill" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="#8b5cf6" stop-opacity=".26"/>
    <stop offset="1" stop-color="#050712" stop-opacity="0"/>
  </linearGradient>
  <filter id="ap-glow" x="-10%" y="-100%" width="120%" height="300%">
    <feGaussianBlur stdDeviation="4"/>
  </filter>
</defs>

<rect width="1200" height="330" rx="24" fill="#050712"/>
<rect x="1" y="1" width="1198" height="328" rx="23" fill="none" stroke="#172033"/>

<g font-family="Inter,Segoe UI,Arial,sans-serif">
  <text x="48" y="48" font-size="13" font-weight="700" fill="#67e8f9" letter-spacing="4">ACTIVITY PULSE · LAST 30 DAYS</text>
  <text x="48" y="76" font-size="15" fill="#94a3b8">Public GitHub commit, pull request and issue activity · auto-updated daily</text>

  <g transform="translate(690,38)" font-family="ui-monospace,Consolas,monospace">
    <text x="0" y="0" font-size="10" fill="#64748b" letter-spacing="2">COMMITS</text>
    <text x="0" y="27" font-size="25" font-weight="700" fill="#67e8f9">{total_commits}</text>
    <text x="115" y="0" font-size="10" fill="#64748b" letter-spacing="2">PR EVENTS</text>
    <text x="115" y="27" font-size="25" font-weight="700" fill="#c4b5fd">{total_prs}</text>
    <text x="245" y="0" font-size="10" fill="#64748b" letter-spacing="2">ISSUES</text>
    <text x="245" y="27" font-size="25" font-weight="700" fill="#f9a8d4">{total_issues}</text>
    <text x="350" y="0" font-size="10" fill="#64748b" letter-spacing="2">ACTIVE DAYS</text>
    <text x="350" y="27" font-size="25" font-weight="700" fill="#7dd3fc">{active_days}</text>
  </g>

  <g stroke="#172033" stroke-width=".7">
    <line x1="70" y1="143" x2="1130" y2="143"/>
    <line x1="70" y1="195" x2="1130" y2="195"/>
    <line x1="70" y1="248" x2="1130" y2="248"/>
  </g>

  <polygon points="{x0},{baseline} {point_str} {x1},{baseline}" fill="url(#ap-fill)"/>
  <polyline points="{point_str}" fill="none" stroke="url(#ap-trace)" stroke-width="8" stroke-linecap="round" stroke-linejoin="round" opacity=".18" filter="url(#ap-glow)"/>
  <polyline points="{point_str}" fill="none" stroke="url(#ap-trace)" stroke-width="2.8" stroke-linecap="round" stroke-linejoin="round"/>

  {''.join(dots)}
  {''.join(labels)}

  <text x="48" y="315" font-size="10" fill="#475569" letter-spacing="1.5">PEAK DAY · {esc(peak_day)}</text>
  <text x="1152" y="315" text-anchor="end" font-size="10" fill="#475569">UPDATED {esc(updated)}</text>
</g>
</svg>'''

def main():
    events = fetch_events()
    daily = build_activity(events)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(generate_svg(daily), encoding="utf-8")
    print(f"Wrote {OUT} from {len(events)} public events.")

if __name__ == "__main__":
    main()
