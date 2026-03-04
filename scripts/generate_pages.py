"""
Generate SEO content pages for btctothemoon.uk
Runs after update_score.py in GitHub Actions

Generates:
1. Daily analysis page (/daily/YYYY-MM-DD.html)
2. Milestone pages when score crosses key thresholds
3. Updates sitemap.xml
4. Appends to history.json
"""

import json
import os
from datetime import datetime, timezone

SITE_URL = "https://btctothemoon.uk"
REF_URL = "https://accounts.binance.com/en/register?ref=GXWQ97QK"

# ============================================
# Load data
# ============================================

def load_json(path):
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return None

def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# ============================================
# Historical comparison engine
# ============================================

def find_historical_parallels(score, ref_data):
    """Find the closest historical moments to current score"""
    parallels = []
    for entry in ref_data:
        if entry.get("recovery","").startswith("Ongoing") or entry.get("recovery","").startswith("Current"):
            continue
        if abs(entry["score"] - score) <= 10:
            parallels.append(entry)
    # Sort by score proximity
    parallels.sort(key=lambda x: abs(x["score"] - score))
    return parallels[:3]

def find_last_time_at_level(score, ref_data):
    """Find when score was last at this level"""
    threshold = score + 5
    for entry in reversed(ref_data[:-1]):
        if entry["score"] <= threshold:
            return entry
    return None

def get_phase_name(score):
    if score <= 15: return "Extreme Cold"
    if score <= 30: return "Cold"
    if score <= 45: return "Neutral"
    if score <= 60: return "Warm"
    if score <= 75: return "Accelerating"
    if score <= 90: return "Hot"
    return "Extreme Hot"

def get_phase_description(score):
    """Generate a paragraph about what this score zone historically means"""
    if score <= 15:
        return "Scores below 15 represent extreme market distress. In Bitcoin's history, this has only occurred during major crashes — the 2018 bear bottom, the COVID crash of March 2020, and the FTX collapse in November 2022. Every previous instance was followed by significant recovery within 6-12 months, though the timing of exact bottoms is impossible to predict."
    if score <= 30:
        return "Scores between 15-30 indicate a cold market where fear dominates. Historically, these periods have been accumulation zones where long-term holders added to positions. The average time spent below 30 in past cycles was 4-10 weeks before recovery began. However, bear markets can extend these periods significantly."
    if score <= 45:
        return "Scores between 30-45 suggest the market is transitioning. This zone often appears during the early stages of recovery or during mid-cycle corrections. It's a region of uncertainty — the market could be building a base for the next move up, or it could still be finding its bottom."
    if score <= 60:
        return "Scores between 45-60 represent neutral territory. The market is neither overheated nor deeply discounted. This is often where Bitcoin spends time during healthy consolidation phases. Risk is moderate and sentiment is balanced."
    if score <= 75:
        return "Scores between 60-75 indicate warming conditions. Momentum is building. In past cycles, this zone preceded the most explosive price moves — but it also preceded corrections when the move was too fast. This is the time to ensure you have a clear plan."
    if score <= 90:
        return "Scores between 75-90 are historically elevated. The market is running hot. In every past cycle, sustained scores above 75 eventually led to significant corrections of 30-50% or more. The timing is unpredictable, but the risk is clearly elevated."
    return "Scores above 90 have historically marked cycle peaks. These conditions have only lasted 2-8 weeks before major corrections. Every instance in Bitcoin's history was followed by a decline of 50% or more within the following 12 months."

# ============================================
# HTML Templates
# ============================================

def page_head(title, description, canonical_path):
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<meta name="description" content="{description}">
<link rel="canonical" href="{SITE_URL}{canonical_path}">
<meta property="og:title" content="{title}">
<meta property="og:description" content="{description}">
<meta property="og:type" content="article">
<meta property="og:url" content="{SITE_URL}{canonical_path}">
<meta property="og:image" content="{SITE_URL}/og-image.png">
<meta name="twitter:card" content="summary_large_image">
<link rel="icon" href="../favicon.ico" type="image/x-icon">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
<style>
:root{{--bg:#FAFAFA;--card:#FFF;--text:#1D1D1F;--text2:#6E6E73;--text3:#AEAEB2;--border:rgba(0,0,0,.06);--orange:#F7931A;--orange-light:#FFF8F0;--green:#34C759;--red:#FF3B30;--blue:#007AFF}}
*{{box-sizing:border-box;margin:0;padding:0}}
body{{min-height:100vh;background:var(--bg);color:var(--text);font-family:'Inter',-apple-system,sans-serif;line-height:1.8}}
nav{{position:sticky;top:0;z-index:100;background:rgba(250,250,250,.85);backdrop-filter:blur(20px);border-bottom:1px solid var(--border)}}
.nav-inner{{max-width:720px;margin:0 auto;display:flex;align-items:center;justify-content:space-between;height:52px;padding:0 24px}}
.logo{{display:flex;align-items:center;gap:10px;text-decoration:none}}
.logo-icon{{width:28px;height:28px;border-radius:8px;background:linear-gradient(135deg,#F7931A,#F5B041);display:flex;align-items:center;justify-content:center;color:#fff;font-weight:700;font-size:14px;font-family:'JetBrains Mono',monospace}}
.logo-text{{font-weight:700;font-size:15px;color:var(--text)}}
.back-link{{font-size:13px;color:var(--orange);text-decoration:none;font-weight:500}}
.back-link:hover{{text-decoration:underline}}
article{{max-width:720px;margin:0 auto;padding:48px 24px 80px}}
h1{{font-size:clamp(24px,4vw,36px);font-weight:800;line-height:1.2;letter-spacing:-.5px;margin-bottom:8px}}
.meta{{color:var(--text3);font-size:13px;margin-bottom:32px;font-family:'JetBrains Mono',monospace}}
h2{{font-size:20px;font-weight:700;margin:36px 0 12px;letter-spacing:-.3px}}
p{{margin-bottom:16px;color:var(--text2);font-size:15px}}
.score-badge{{display:inline-flex;align-items:center;gap:8px;padding:6px 16px;border-radius:20px;font-size:15px;font-weight:700;margin:12px 0 24px}}
.data-grid{{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin:20px 0 32px}}
.data-card{{padding:16px;background:#fff;border:1px solid var(--border);border-radius:12px}}
.data-card .label{{font-size:11px;color:var(--text3);text-transform:uppercase;letter-spacing:.5px;font-weight:600}}
.data-card .value{{font-size:18px;font-weight:700;margin-top:4px;font-family:'JetBrains Mono',monospace}}
.history-card{{padding:16px 20px;background:#fff;border:1px solid var(--border);border-radius:12px;margin:12px 0}}
.history-card .date{{font-size:12px;color:var(--orange);font-weight:600;font-family:'JetBrains Mono',monospace}}
.history-card .desc{{font-size:14px;color:var(--text2);margin:6px 0}}
.history-card .outcome{{font-size:13px;color:var(--green);font-weight:600}}
.cta-inline{{display:block;text-align:center;padding:24px;background:linear-gradient(135deg,#FFF9F0,#FFF4E6);border:1px solid rgba(247,147,26,.15);border-radius:16px;margin:32px 0;text-decoration:none}}
.cta-inline .cta-text{{font-size:14px;color:var(--text2);margin-bottom:10px}}
.cta-inline .cta-btn{{display:inline-block;padding:10px 24px;background:var(--orange);color:#fff;border-radius:10px;font-size:14px;font-weight:600;text-decoration:none}}
.disclaimer{{font-size:11px;color:var(--text3);text-align:center;padding:20px;border-top:1px solid var(--border);margin-top:40px;line-height:1.6}}
.nav-bottom{{display:flex;justify-content:space-between;padding:20px 0;border-top:1px solid var(--border);margin-top:32px;font-size:13px}}
.nav-bottom a{{color:var(--orange);text-decoration:none;font-weight:500}}
@media(max-width:520px){{article{{padding:32px 16px 60px}}.data-grid{{grid-template-columns:1fr}}}}
</style>
</head>"""

def page_nav():
    return """
<body>
<nav>
<div class="nav-inner">
  <a class="logo" href="/"><div class="logo-icon">₿</div><span class="logo-text">BTC to the Moon</span></a>
  <a class="back-link" href="/">← Back to Indicator</a>
</div>
</nav>"""

def page_footer():
    return f"""
<div class="disclaimer">
  Scores are based on public on-chain data and historical statistical patterns — not predictions.<br>
  Crypto carries extreme risk. DYOR. Not financial advice.<br>
  © 2026 btctothemoon.uk
</div>
</article>
</body>
</html>"""

def cta_block(score):
    if score <= 30:
        msg = "Historically, scores below 30 have been accumulation zones. If you're considering entering the market, starting small with dollar-cost averaging may be worth exploring."
    elif score <= 60:
        msg = "The market is in a transitional phase. If you want to start building a position, consider small regular purchases rather than one large buy."
    else:
        msg = "The market is running warm. If you already hold BTC, consider reviewing your exit strategy. If you're new, caution is warranted at these levels."
    return f"""
<a class="cta-inline" href="{REF_URL}" target="_blank" rel="noopener noreferrer">
  <div class="cta-text">{msg}</div>
  <span class="cta-btn">Open Binance Account — 10% Fee Rebate</span>
</a>"""

# ============================================
# Generate Daily Page
# ============================================

def generate_daily_page(data, ref_data, today_str):
    score = data["score"]
    raw = data.get("raw", {})
    price = raw.get("btc_price")
    ma200 = raw.get("ma_200")
    fg = raw.get("fear_greed")
    dev = raw.get("deviation_pct")
    dom = raw.get("btc_dominance")
    fund = raw.get("funding_rate")

    phase = get_phase_name(score)
    phase_desc = get_phase_description(score)
    parallels = find_historical_parallels(score, ref_data)

    color = "#007AFF" if score <= 30 else "#34C759" if score <= 45 else "#FF9500" if score <= 60 else "#FF6B35" if score <= 75 else "#FF3B30"

    title = f"BTC Cycle Score: {score}/100 — {phase} | {today_str}"
    desc = f"Bitcoin cycle indicator scored {score}/100 on {today_str}. Fear & Greed at {fg or 'N/A'}, price {'${:,.0f}'.format(price) if price else 'N/A'}, {abs(dev or 0):.0f}% {'below' if (dev or 0) < 0 else 'above'} 200-day MA."

    # Build data cards
    price_str = f"${price:,.0f}" if price else "N/A"
    ma_str = f"${ma200:,.0f}" if ma200 else "N/A"
    dev_str = f"{dev:+.1f}%" if dev else "N/A"
    fg_str = f"{fg}/100" if fg else "N/A"
    dom_str = f"{dom:.1f}%" if dom else "N/A"
    fund_str = f"{fund*100:.4f}%" if fund else "N/A"

    # Build parallels HTML
    parallels_html = ""
    if parallels:
        parallels_html = "<h2>Historical Parallels</h2>\n<p>Here's what happened the last time conditions looked similar:</p>\n"
        for p in parallels:
            parallels_html += f"""<div class="history-card">
  <div class="date">{p['date']} — Score: {p['score']}/100 | ${p['price']:,}</div>
  <div class="desc">{p['note']}</div>
  <div class="outcome">{p['recovery']}</div>
</div>\n"""
        parallels_html += "<p><strong>Important:</strong> History doesn't repeat exactly, but it often rhymes. Past recoveries don't guarantee future ones. Use this as context, not as a trading signal.</p>\n"

    # Yesterday link
    from datetime import timedelta
    today_date = datetime.strptime(today_str, "%Y-%m-%d")
    yesterday = (today_date - timedelta(days=1)).strftime("%Y-%m-%d")
    tomorrow = (today_date + timedelta(days=1)).strftime("%Y-%m-%d")

    html = page_head(title, desc, f"/daily/{today_str}.html")
    html += page_nav()
    html += f"""
<article>
<h1>BTC Cycle Report — {today_str}</h1>
<div class="meta">Updated daily · Based on 4 on-chain indicators</div>

<div class="score-badge" style="background:{color}15;border:1px solid {color}30;color:{color}">
  Score: {score}/100 — {phase}
</div>

<div class="data-grid">
  <div class="data-card"><div class="label">BTC Price</div><div class="value">{price_str}</div></div>
  <div class="data-card"><div class="label">vs 200-Day MA</div><div class="value">{dev_str}</div></div>
  <div class="data-card"><div class="label">Fear & Greed</div><div class="value">{fg_str}</div></div>
  <div class="data-card"><div class="label">BTC Dominance</div><div class="value">{dom_str}</div></div>
</div>

<h2>What Does a Score of {score} Mean?</h2>
<p>{phase_desc}</p>

{parallels_html}

{cta_block(score)}

<h2>How This Score Is Calculated</h2>
<p>The BTC Cycle Indicator combines four metrics, each weighted by its historical predictive value:</p>
<p><strong>Fear & Greed Index (25%):</strong> Measures overall market sentiment from social media, volatility, volume, and surveys. Currently at {fg_str}.</p>
<p><strong>Price vs 200-Day Moving Average (35%):</strong> The 200-day MA is a widely-watched long-term trend indicator. BTC is currently {dev_str} from it. Large deviations below often signal undervaluation; large deviations above signal overextension.</p>
<p><strong>Funding Rate (15%):</strong> The perpetual futures funding rate shows whether leveraged traders are net long or short. Currently {fund_str}.</p>
<p><strong>BTC Dominance (25%):</strong> Bitcoin's share of total crypto market cap. Currently {dom_str}. High dominance typically appears in early/bear markets; low dominance signals alt-season euphoria.</p>

<p style="text-align:center;margin-top:24px"><a href="/" style="color:var(--orange);font-weight:600;text-decoration:none">← View Live Indicator on btctothemoon.uk</a></p>

<div class="nav-bottom">
  <a href="/daily/{yesterday}.html">← Previous Day</a>
  <a href="/daily/{tomorrow}.html">Next Day →</a>
</div>

{page_footer()}"""

    return html

# ============================================
# Generate Milestone Page
# ============================================

MILESTONES = [
    {"threshold": 20, "dir": "below", "slug": "drops-below-20", "title": "BTC Score Drops Below 20 — Extreme Fear Territory"},
    {"threshold": 30, "dir": "below", "slug": "drops-below-30", "title": "BTC Score Drops Below 30 — Entering Bottom Zone"},
    {"threshold": 50, "dir": "above", "slug": "crosses-above-50", "title": "BTC Score Crosses 50 — Entering Neutral Territory"},
    {"threshold": 70, "dir": "above", "slug": "crosses-above-70", "title": "BTC Score Crosses 70 — Market Heating Up"},
    {"threshold": 80, "dir": "above", "slug": "crosses-above-80", "title": "BTC Score Hits 80 — Historical Caution Zone"},
    {"threshold": 90, "dir": "above", "slug": "crosses-above-90", "title": "BTC Score Hits 90 — Extreme Heat Warning"},
]

def check_milestones(score, prev_score):
    """Return list of triggered milestones"""
    triggered = []
    if prev_score is None:
        return triggered
    for m in MILESTONES:
        t = m["threshold"]
        if m["dir"] == "below" and prev_score >= t and score < t:
            triggered.append(m)
        elif m["dir"] == "above" and prev_score < t and score >= t:
            triggered.append(m)
    return triggered

def generate_milestone_page(milestone, data, ref_data, today_str):
    score = data["score"]
    raw = data.get("raw", {})
    price = raw.get("btc_price")
    phase = get_phase_name(score)
    phase_desc = get_phase_description(score)
    parallels = find_historical_parallels(score, ref_data)

    title = f"{milestone['title']} — {today_str}"
    desc = f"The BTC Cycle Indicator crossed the {milestone['threshold']} threshold on {today_str}. Here's what history tells us about this level."

    parallels_html = ""
    if parallels:
        parallels_html = "<h2>What Happened Last Time?</h2>\n"
        for p in parallels:
            parallels_html += f"""<div class="history-card">
  <div class="date">{p['date']} — Score: {p['score']}/100 | ${p['price']:,}</div>
  <div class="desc">{p['note']}</div>
  <div class="outcome">{p['recovery']}</div>
</div>\n"""

    html = page_head(title, desc, f"/milestones/{milestone['slug']}-{today_str}.html")
    html += page_nav()
    html += f"""
<article>
<h1>{milestone['title']}</h1>
<div class="meta">{today_str} · BTC Price: {'${:,.0f}'.format(price) if price else 'N/A'}</div>

<p>On {today_str}, the BTC Cycle Indicator {'dropped below' if milestone['dir']=='below' else 'crossed above'} <strong>{milestone['threshold']}</strong>, entering <strong>{phase}</strong> territory.</p>

<p>{phase_desc}</p>

{parallels_html}

{cta_block(score)}

<h2>What Should You Do?</h2>
<p>This indicator is a tool for awareness, not a trading signal. It helps you understand where the market sits relative to historical patterns. Whether you choose to act on this information depends on your own risk tolerance, time horizon, and financial situation.</p>

<p>The most important thing is to have a plan <em>before</em> the market moves. If you're just starting out, our <a href="/guide/when-to-buy-bitcoin.html" style="color:var(--orange)">guide on when to buy Bitcoin</a> provides a framework based on historical data.</p>

<p style="text-align:center;margin-top:24px"><a href="/" style="color:var(--orange);font-weight:600;text-decoration:none">← View Live Indicator</a></p>

{page_footer()}"""

    return html

# ============================================
# Update history.json
# ============================================

def update_history(data, today_str):
    history_path = "history.json"
    history = load_json(history_path) or []

    # Don't duplicate
    if any(h["date"] == today_str for h in history):
        return history

    raw = data.get("raw", {})
    entry = {
        "date": today_str,
        "score": data["score"],
        "price": raw.get("btc_price"),
        "fg": raw.get("fear_greed"),
        "dev": raw.get("deviation_pct"),
        "dom": raw.get("btc_dominance"),
    }
    history.append(entry)

    # Keep last 365 days
    history = history[-365:]
    save_json(history_path, history)
    return history

# ============================================
# Update sitemap
# ============================================

def update_sitemap(daily_pages, milestone_pages, guide_pages):
    urls = [
        {"loc": "/", "freq": "daily", "priority": "1.0"},
        {"loc": "/?lang=zh", "freq": "daily", "priority": "0.8"},
    ]

    for g in guide_pages:
        urls.append({"loc": g, "freq": "monthly", "priority": "0.9"})

    for d in sorted(daily_pages, reverse=True)[:90]:  # Last 90 days
        urls.append({"loc": d, "freq": "never", "priority": "0.6"})

    for m in milestone_pages:
        urls.append({"loc": m, "freq": "never", "priority": "0.7"})

    xml = '<?xml version="1.0" encoding="UTF-8"?>\n'
    xml += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    for u in urls:
        xml += f'  <url>\n    <loc>{SITE_URL}{u["loc"]}</loc>\n    <changefreq>{u["freq"]}</changefreq>\n    <priority>{u["priority"]}</priority>\n  </url>\n'
    xml += '</urlset>\n'

    with open("sitemap.xml", "w") as f:
        f.write(xml)
    print(f"  Sitemap updated with {len(urls)} URLs")

# ============================================
# Main
# ============================================

def main():
    print("\n" + "=" * 50)
    print("Generating content pages")
    print("=" * 50)

    # Load current data
    data = load_json("data.json")
    if not data:
        print("ERROR: data.json not found")
        return

    ref_data = load_json("scripts/history_reference.json") or []
    today_str = data.get("lastUpdated", datetime.now(timezone.utc).strftime("%Y-%m-%d"))
    score = data["score"]

    print(f"\nDate: {today_str}, Score: {score}")

    # 1. Update history
    print("\n[1] Updating history.json...")
    history = update_history(data, today_str)
    prev_score = history[-2]["score"] if len(history) >= 2 else None
    print(f"  History entries: {len(history)}, prev score: {prev_score}")

    # 2. Generate daily page
    print("\n[2] Generating daily page...")
    os.makedirs("daily", exist_ok=True)
    daily_html = generate_daily_page(data, ref_data, today_str)
    daily_path = f"daily/{today_str}.html"
    with open(daily_path, "w", encoding="utf-8") as f:
        f.write(daily_html)
    print(f"  Created: {daily_path}")

    # 3. Check milestones
    print("\n[3] Checking milestones...")
    os.makedirs("milestones", exist_ok=True)
    milestone_files = []
    triggered = check_milestones(score, prev_score)
    if triggered:
        for m in triggered:
            ms_html = generate_milestone_page(m, data, ref_data, today_str)
            ms_path = f"milestones/{m['slug']}-{today_str}.html"
            with open(ms_path, "w", encoding="utf-8") as f:
                f.write(ms_html)
            milestone_files.append(f"/milestones/{m['slug']}-{today_str}.html")
            print(f"  MILESTONE: {m['title']}")
    else:
        print("  No milestones triggered")

    # Collect existing milestone files
    if os.path.exists("milestones"):
        for f in os.listdir("milestones"):
            if f.endswith(".html"):
                path = f"/milestones/{f}"
                if path not in milestone_files:
                    milestone_files.append(path)

    # 4. Collect all daily pages
    daily_pages = []
    if os.path.exists("daily"):
        for f in sorted(os.listdir("daily")):
            if f.endswith(".html"):
                daily_pages.append(f"/daily/{f}")

    # 5. Guide pages
    guide_pages = []
    if os.path.exists("guide"):
        for f in os.listdir("guide"):
            if f.endswith(".html"):
                guide_pages.append(f"/guide/{f}")

    # 6. Update sitemap
    print("\n[4] Updating sitemap...")
    update_sitemap(daily_pages, milestone_files, guide_pages)

    print(f"\n✅ Content generation complete!")
    print(f"   Daily pages: {len(daily_pages)}")
    print(f"   Milestone pages: {len(milestone_files)}")
    print(f"   Guide pages: {len(guide_pages)}")

if __name__ == "__main__":
    main()
