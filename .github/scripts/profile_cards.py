"""Generate GitHub profile cards (stats, top languages, trophies, contribution graph) as SVG files.

Runs inside GitHub Actions with the built-in GITHUB_TOKEN, so the profile README does not depend on
third-party image services. Writes to profile/*.svg.

Usage:
  GITHUB_TOKEN=... GH_USER=UmamaQayumKhan python .github/scripts/profile_cards.py
  python .github/scripts/profile_cards.py --sample   # render with sample data (local preview)
"""
import datetime as dt
import json
import os
import sys
import urllib.request
from html import escape

USER = os.environ.get("GH_USER", "UmamaQayumKhan")
OUT = os.path.join(os.path.dirname(__file__), "..", "..", "profile")

BG, BORDER, TITLE, ICON, TEXT, MUTED = "#fffdf7", "#ece6da", "#e05a2f", "#1f7a4d", "#2c3550", "#7a8299"
FONT = "'Segoe UI', Ubuntu, 'Helvetica Neue', Arial, sans-serif"

QUERY = """
query($login: String!) {
  user(login: $login) {
    name
    followers { totalCount }
    pullRequests { totalCount }
    issues { totalCount }
    repositories(first: 100, ownerAffiliations: OWNER, isFork: false, privacy: PUBLIC) {
      totalCount
      nodes {
        stargazerCount
        languages(first: 10, orderBy: {field: SIZE, direction: DESC}) { edges { size node { name color } } }
      }
    }
    contributionsCollection {
      totalCommitContributions
      restrictedContributionsCount
      contributionCalendar { totalContributions weeks { contributionDays { date contributionCount } } }
    }
  }
}
"""


def fetch():
    token = os.environ["GITHUB_TOKEN"]
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY, "variables": {"login": USER}}).encode(),
        headers={"Authorization": f"bearer {token}", "Content-Type": "application/json", "User-Agent": "profile-cards"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        body = json.load(r)
    if "errors" in body:
        raise SystemExit(f"GraphQL error: {body['errors']}")
    return body["data"]["user"]


def sample():
    import random
    random.seed(4)
    today = dt.date.today()
    days = [{"date": (today - dt.timedelta(days=i)).isoformat(), "contributionCount": random.choice([0, 0, 1, 2, 3, 5, 8, 12])} for i in range(370)][::-1]
    weeks = [{"contributionDays": days[i:i + 7]} for i in range(0, len(days), 7)]
    langs = [("Python", "#3572A5", 900000), ("Jupyter Notebook", "#DA5B0B", 400000), ("JavaScript", "#f1e05a", 120000),
             ("HTML", "#e34c26", 90000), ("CSS", "#563d7c", 40000), ("Dockerfile", "#384d54", 5000)]
    return {"name": "Umama Qayum Khan", "followers": {"totalCount": 12}, "pullRequests": {"totalCount": 9}, "issues": {"totalCount": 4},
            "repositories": {"totalCount": 28, "nodes": [{"stargazerCount": 3, "languages": {"edges": [{"size": s, "node": {"name": n, "color": c}} for n, c, s in langs]}}]},
            "contributionsCollection": {"totalCommitContributions": 640, "restrictedContributionsCount": 0,
                                        "contributionCalendar": {"totalContributions": 812, "weeks": weeks}}}


def card(w, h, inner):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" font-family="{FONT}">'
            f'<rect x="0.5" y="0.5" width="{w - 1}" height="{h - 1}" rx="12" fill="{BG}" stroke="{BORDER}"/>{inner}</svg>')


def fmt(n):
    return f"{n / 1000:.1f}k" if n >= 1000 else str(n)


def stats_svg(d):
    cc = d["contributionsCollection"]
    stars = sum(r["stargazerCount"] for r in d["repositories"]["nodes"])
    total = cc["contributionCalendar"]["totalContributions"]
    rows = [("Total stars earned", stars), ("Commits (last year)", cc["totalCommitContributions"] + cc["restrictedContributionsCount"]),
            ("Pull requests", d["pullRequests"]["totalCount"]), ("Issues", d["issues"]["totalCount"]),
            ("Public repositories", d["repositories"]["totalCount"]), ("Followers", d["followers"]["totalCount"])]
    s = f'<text x="25" y="38" font-size="19" font-weight="700" fill="{TITLE}">Umama\'s GitHub Stats</text>'
    for i, (label, val) in enumerate(rows):
        y = 70 + i * 22
        s += (f'<circle cx="32" cy="{y - 5}" r="5" fill="{ICON}"/>'
              f'<text x="46" y="{y}" font-size="14" font-weight="600" fill="{TEXT}">{label}:</text>'
              f'<text x="230" y="{y}" font-size="14" font-weight="700" fill="{TEXT}">{fmt(val)}</text>')
    # contributions ring
    s += (f'<circle cx="400" cy="108" r="52" fill="none" stroke="{TITLE}" stroke-opacity=".18" stroke-width="7"/>'
          f'<circle cx="400" cy="108" r="52" fill="none" stroke="{TITLE}" stroke-width="7" stroke-linecap="round" '
          f'stroke-dasharray="{min(total, 1000) / 1000 * 326.7:.1f} 327" transform="rotate(-90 400 108)"/>'
          f'<text x="400" y="114" text-anchor="middle" font-size="24" font-weight="800" fill="{TEXT}">{fmt(total)}</text>'
          f'<text x="400" y="182" text-anchor="middle" font-size="12" fill="{MUTED}">contributions (last year)</text>')
    return card(495, 200, s)


def langs_svg(d):
    tot = {}
    for r in d["repositories"]["nodes"]:
        for e in r["languages"]["edges"]:
            n = e["node"]["name"]
            tot.setdefault(n, [0, e["node"]["color"] or "#999"])[0] += e["size"]
    top = sorted(tot.items(), key=lambda x: -x[1][0])[:6]
    s = f'<text x="25" y="38" font-size="19" font-weight="700" fill="{TITLE}">Most Used Languages</text>'
    if not top:
        return card(360, 200, s + f'<text x="25" y="90" font-size="14" fill="{MUTED}">No language data yet</text>')
    total = sum(v[0] for _, v in top)
    s += '<clipPath id="bar"><rect x="25" y="56" width="310" height="10" rx="5"/></clipPath><g clip-path="url(#bar)">'
    x = 25.0
    for _, (size, color) in top:
        w = 310 * size / total
        s += f'<rect x="{x:.2f}" y="56" width="{w + 0.5:.2f}" height="10" fill="{color}"/>'
        x += w
    s += "</g>"
    for i, (name, (size, color)) in enumerate(top):
        cx, cy = 25 + (i % 2) * 170, 96 + (i // 2) * 28
        s += (f'<circle cx="{cx + 5}" cy="{cy - 5}" r="5" fill="{color}"/>'
              f'<text x="{cx + 16}" y="{cy}" font-size="13" font-weight="600" fill="{TEXT}">{escape(name if len(name) <= 14 else name[:13] + '…')} '
              f'<tspan fill="{MUTED}" font-weight="400">{100 * size / total:.1f}%</tspan></text>')
    return card(360, 200, s)


TROPHY = "M-14 -22 h28 v10 a14 14 0 0 1 -28 0z M-14 -18 h-7 a7 7 0 0 0 7 9 M14 -18 h7 a7 7 0 0 1 -7 9 M-3 2 h6 v8 h-6z M-11 10 h22 v5 h-22z"
RANKS = [("S", "#e8a317", "#fff4d6"), ("A", "#5b7fbf", "#e6eefb"), ("B", "#b8733a", "#f8eadf"), ("C", "#7a8299", "#eef0f5")]


def trophies_svg(d):
    cc = d["contributionsCollection"]
    stars = sum(r["stargazerCount"] for r in d["repositories"]["nodes"])
    items = [("Commits", cc["totalCommitContributions"] + cc["restrictedContributionsCount"], (1000, 500, 100, 10)),
             ("Contributions", cc["contributionCalendar"]["totalContributions"], (1000, 500, 200, 50)),
             ("Repositories", d["repositories"]["totalCount"], (50, 30, 10, 1)),
             ("Stars", stars, (100, 50, 10, 1)),
             ("Pull Requests", d["pullRequests"]["totalCount"], (100, 50, 10, 1)),
             ("Issues", d["issues"]["totalCount"], (100, 50, 10, 1)),
             ("Followers", d["followers"]["totalCount"], (100, 50, 20, 1))]
    s = ""
    for i, (title, val, th) in enumerate(items):
        rank = next((k for k, t in enumerate(th) if val >= t), None)
        letter, col, bg = RANKS[rank] if rank is not None else ("–", "#b9bfcc", "#f3f4f7")
        x = 8 + i * 118
        s += (f'<g transform="translate({x},8)"><rect width="110" height="118" rx="12" fill="{bg}" stroke="{BORDER}"/>'
              f'<g transform="translate(55,46)"><path d="{TROPHY}" fill="{col}" stroke="{col}" stroke-width="1.5" stroke-linejoin="round"/></g>'
              f'<text x="55" y="34" text-anchor="middle" font-size="10" font-weight="800" fill="#fff">{letter}</text>'
              f'<text x="55" y="86" text-anchor="middle" font-size="13" font-weight="700" fill="{TEXT}">{title}</text>'
              f'<text x="55" y="104" text-anchor="middle" font-size="12" font-weight="600" fill="{MUTED}">{fmt(val)}</text></g>')
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="{8 + len(items) * 118}" height="134" viewBox="0 0 {8 + len(items) * 118} 134" font-family="{FONT}">{s}</svg>'


def activity_svg(d):
    days = [x for w in d["contributionsCollection"]["contributionCalendar"]["weeks"] for x in w["contributionDays"]]
    days = days[-31:]
    W, H, L, R, T, B = 1000, 320, 60, 25, 60, 50
    vals = [x["contributionCount"] for x in days]
    top = max(4, max(vals) if vals else 4)
    top = top + (-top % 4)
    pw, ph = W - L - R, H - T - B
    pts = [(L + i * pw / max(1, len(vals) - 1), T + ph - v / top * ph) for i, v in enumerate(vals)]
    s = f'<text x="{W / 2}" y="34" text-anchor="middle" font-size="19" font-weight="700" fill="{TITLE}">Umama Qayum Khan\'s Contribution Graph</text>'
    for k in range(5):
        y = T + ph - k * ph / 4
        s += (f'<line x1="{L}" y1="{y:.1f}" x2="{W - R}" y2="{y:.1f}" stroke="{BORDER}"/>'
              f'<text x="{L - 10}" y="{y + 4:.1f}" text-anchor="end" font-size="11" fill="{MUTED}">{int(top * k / 4)}</text>')
    if pts:
        line = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
        s += (f'<polygon points="{L},{T + ph} {line} {pts[-1][0]:.1f},{T + ph}" fill="{TITLE}" fill-opacity=".14"/>'
              f'<polyline points="{line}" fill="none" stroke="{TITLE}" stroke-width="2.5" stroke-linejoin="round"/>')
        for (x, y), day in zip(pts, days):
            s += (f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3.5" fill="{ICON}"><title>{day["date"]}: {day["contributionCount"]}</title></circle>'
                  f'<text x="{x:.1f}" y="{T + ph + 18}" text-anchor="middle" font-size="10" fill="{MUTED}">{int(day["date"][8:])}</text>')
    s += (f'<text x="{W / 2}" y="{H - 8}" text-anchor="middle" font-size="12" fill="{TEXT}">Days (last 31)</text>'
          f'<text x="16" y="{T + ph / 2}" text-anchor="middle" font-size="12" fill="{TEXT}" transform="rotate(-90 16 {T + ph / 2})">Contributions</text>')
    return card(W, H, s)


def main():
    d = sample() if "--sample" in sys.argv else fetch()
    os.makedirs(OUT, exist_ok=True)
    for name, fn in [("stats", stats_svg), ("top-langs", langs_svg), ("trophies", trophies_svg), ("activity", activity_svg)]:
        with open(os.path.join(OUT, f"{name}.svg"), "w", encoding="utf-8") as f:
            f.write(fn(d))
        print("wrote", name)


if __name__ == "__main__":
    main()
