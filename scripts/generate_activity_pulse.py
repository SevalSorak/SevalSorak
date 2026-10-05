#!/usr/bin/env python3
import json
import os
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

USERNAME = os.getenv("GITHUB_ACTOR_TARGET", "SevalSorak")
TOKEN = os.getenv("PROFILE_ACTIVITY_TOKEN") or os.getenv("GITHUB_TOKEN", "")
OUT = Path("assets/activity-pulse.svg")
TZ = ZoneInfo("Europe/Istanbul")

QUERY = """
query($login: String!) {
  user(login: $login) {
    contributionsCollection {
      contributionCalendar {
        totalContributions
        weeks {
          contributionDays {
            date
            contributionCount
          }
        }
      }
    }
  }
}
"""

def fetch_contributions():
    if not TOKEN:
        raise RuntimeError("A GitHub token is required.")

    payload = json.dumps({
        "query": QUERY,
        "variables": {"login": USERNAME}
    }).encode("utf-8")

    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=payload,
        headers={
            "Authorization": f"Bearer {TOKEN}",
            "Content-Type": "application/json",
            "User-Agent": "sevalsorak-profile-activity-pulse",
        },
        method="POST",
    )

    with urllib.request.urlopen(req, timeout=30) as response:
        data = json.load(response)

    if data.get("errors"):
        raise RuntimeError("GitHub GraphQL error: " + json.dumps(data["errors"]))

    weeks = (
        data.get("data", {})
        .get("user", {})
        .get("contributionsCollection", {})
        .get("contributionCalendar", {})
        .get("weeks", [])
    )

    contributions = {}
    for week in weeks:
        for day in week.get("contributionDays", []):
            contributions[day["date"]] = int(day.get("contributionCount", 0))
    return contributions

def last_30_days(contributions):
    today = datetime.now(TZ).date()
    start = today - timedelta(days=29)
    days = []
    for i in range(30):
        d = start + timedelta(days=i)
        days.append((d, contributions.get(d.isoformat(), 0)))
    return days

def current_streak(days):
    # GitHub-style practical interpretation:
    # if today has no contribution yet, allow the streak to continue from yesterday.
    idx = len(days) - 1
    if idx >= 0 and days[idx][1] == 0:
        idx -= 1
    streak = 0
    while idx >= 0 and days[idx][1] > 0:
        streak += 1
        idx -= 1
    return streak

def esc(text):
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )

def generate_svg(days):
    counts = [count for _, count in days]
    max_count = max(counts) if max(counts, default=0) > 0 else 1

    x0, x1 = 70, 1130
    baseline = 248
    max_amp = 105
    step = (x1 - x0) / (len(days) - 1)

    points = []
    for i, (_, count) in enumerate(days):
        x = x0 + i * step
        y = baseline - (count / max_count) * max_amp
        points.append((x, y))

    point_str = " ".join(f"{x:.1f},{y:.1f}" for x, y in points)

    total = sum(counts)
    active_days = sum(1 for c in counts if c > 0)
    best_count = max(counts, default=0)
    best_idx = counts.index(best_count) if best_count > 0 else 0
    best_date = days[best_idx][0].strftime("%d %b") if best_count > 0 else "—"
    streak = current_streak(days)

    labels = []
    for idx in [0, 7, 14, 21, 29]:
        d = days[idx][0]
        x = x0 + idx * step
        labels.append(
            f'<text x="{x:.1f}" y="286" text-anchor="middle" font-size="11" fill="#64748b">{esc(d.strftime("%d %b"))}</text>'
        )

    dots = []
    for i, (day, count) in enumerate(days):
        if count <= 0:
            continue
        x, y = points[i]
        dots.append(
            f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3.2" fill="#e879f9">'
            f'<title>{esc(day.isoformat())}: {count} contributions</title></circle>'
        )

    updated = datetime.now(TZ).strftime("%d %b %Y · %H:%M TRT")

    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 330" width="1200" height="330" role="img" aria-label="GitHub contribution activity pulse for the last 30 days">
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
  <text x="48" y="76" font-size="15" fill="#94a3b8">GitHub contribution calendar · auto-updated daily</text>

  <g transform="translate(650,38)" font-family="ui-monospace,Consolas,monospace">
    <text x="0" y="0" font-size="10" fill="#64748b" letter-spacing="2">CONTRIBUTIONS</text>
    <text x="0" y="27" font-size="25" font-weight="700" fill="#67e8f9">{total}</text>
    <text x="145" y="0" font-size="10" fill="#64748b" letter-spacing="2">ACTIVE DAYS</text>
    <text x="145" y="27" font-size="25" font-weight="700" fill="#c4b5fd">{active_days}</text>
    <text x="275" y="0" font-size="10" fill="#64748b" letter-spacing="2">BEST DAY</text>
    <text x="275" y="27" font-size="25" font-weight="700" fill="#f9a8d4">{best_count}</text>
    <text x="390" y="0" font-size="10" fill="#64748b" letter-spacing="2">STREAK</text>
    <text x="390" y="27" font-size="25" font-weight="700" fill="#7dd3fc">{streak}d</text>
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

  <text x="48" y="315" font-size="10" fill="#475569" letter-spacing="1.5">BEST DAY · {esc(best_date)} · {best_count} CONTRIBUTIONS</text>
  <text x="1152" y="315" text-anchor="end" font-size="10" fill="#475569">UPDATED {esc(updated)}</text>
</g>
</svg>'''

def main():
    contributions = fetch_contributions()
    days = last_30_days(contributions)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(generate_svg(days), encoding="utf-8")
    print(f"Wrote {OUT} from GitHub contribution calendar.")

if __name__ == "__main__":
    main()
