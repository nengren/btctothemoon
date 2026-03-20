"""
Send BTC Cycle Score updates to Telegram channel
Runs after generate_pages.py in GitHub Actions

Two types of messages:
1. Daily score update (every day)
2. Milestone alert (when score crosses key thresholds)
"""

import json
import os
import urllib.request
import urllib.error

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
CHANNEL = "@btctothemoon_alerts"
SITE = "https://btctothemoon.uk"
REF = "https://accounts.binance.com/en/register?ref=GXWQ97QK"

def send_telegram(text):
    """Send message to Telegram channel with MarkdownV2"""
    if not BOT_TOKEN:
        print("  [SKIP] No TELEGRAM_BOT_TOKEN set")
        return False
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = json.dumps({
        "chat_id": CHANNEL,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": False
    }).encode("utf-8")
    req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            result = json.loads(resp.read().decode())
            if result.get("ok"):
                print("  [OK] Message sent to Telegram")
                return True
            else:
                print(f"  [FAIL] Telegram API: {result}")
                return False
    except Exception as e:
        print(f"  [FAIL] Telegram send: {e}")
        return False


def get_phase(score):
    if score <= 15: return "Extreme Cold ❄️"
    if score <= 30: return "Cold 🥶"
    if score <= 45: return "Neutral ⚖️"
    if score <= 60: return "Warm 🌤"
    if score <= 75: return "Hot 🔥"
    if score <= 90: return "Very Hot 🌡"
    return "Extreme Hot 🚨"


def get_bar(score):
    """Visual score bar"""
    filled = round(score / 5)
    return "▓" * filled + "░" * (20 - filled)


def build_daily_message(data, prev_score):
    score = data["score"]
    raw = data.get("raw", {})
    price = raw.get("btc_price")
    fg = raw.get("fear_greed")
    dev = raw.get("deviation_pct")
    dom = raw.get("btc_dominance")
    date = data.get("lastUpdated", "")
    phase = get_phase(score)
    bar = get_bar(score)

    # Score change arrow
    if prev_score is not None:
        diff = score - prev_score
        if diff > 0:
            change = f"↑{diff}"
        elif diff < 0:
            change = f"↓{abs(diff)}"
        else:
            change = "→ unchanged"
    else:
        change = ""

    price_str = f"${price:,.0f}" if price else "N/A"
    fg_str = f"{fg}/100" if fg is not None else "N/A"
    dev_str = f"{dev:+.1f}%" if dev is not None else "N/A"
    dom_str = f"{dom:.1f}%" if dom is not None else "N/A"

    msg = f"""<b>📊 BTC Cycle Score — {date}</b>

<code>{bar}</code>
<b>{score}/100 — {phase}</b> {change}

BTC Price: <b>{price_str}</b>
Fear & Greed: {fg_str}
vs 200DMA: {dev_str}
BTC Dominance: {dom_str}

🔗 <a href="{SITE}/daily/{date}.html">Full daily analysis</a>
📈 <a href="{SITE}">Live indicator</a>"""

    return msg


def build_milestone_message(data, milestone_type, prev_score):
    score = data["score"]
    raw = data.get("raw", {})
    price = raw.get("btc_price")
    date = data.get("lastUpdated", "")
    price_str = f"${price:,.0f}" if price else "N/A"

    if "below_20" == milestone_type:
        emoji = "🚨"
        title = "Score dropped below 20"
        body = "Extreme fear territory. In Bitcoin's history, this has only happened during major crashes — 2018 bottom, COVID crash, FTX collapse. Every previous instance was followed by significant recovery within 6-12 months."
    elif "below_30" == milestone_type:
        emoji = "❄️"
        title = "Score dropped below 30"
        body = "Bottom zone. Historically, buying when the score was below 30 and holding for 12+ months has been profitable in every past cycle. The average time spent below 30 was 4-10 weeks."
    elif "above_50" == milestone_type:
        emoji = "⚖️"
        title = "Score crossed above 50"
        body = "Entering neutral territory. The market is recovering. In past cycles, crossing 50 from below has signaled the start of a new uptrend."
    elif "above_70" == milestone_type:
        emoji = "🔥"
        title = "Score crossed above 70"
        body = "Market is heating up. Historically, sustained scores above 70 have preceded the most explosive moves — but also significant risk accumulation. Time to review your plan."
    elif "above_80" == milestone_type:
        emoji = "⚠️"
        title = "Score hit 80"
        body = "Historical caution zone. Every past cycle saw major corrections after sustained scores above 80. Consider your exit strategy."
    elif "above_90" == milestone_type:
        emoji = "🚨"
        title = "Score hit 90 — Extreme Heat"
        body = "Historically, scores above 90 have only lasted 2-8 weeks before 50%+ crashes. This is not a prediction, but risk is extremely elevated."
    else:
        return None

    msg = f"""{emoji} <b>MILESTONE ALERT: {title}</b>

<b>Score: {score}/100</b> (was {prev_score})
BTC Price: <b>{price_str}</b>
Date: {date}

{body}

🔗 <a href="{SITE}/daily/{date}.html">Today's full analysis</a>
📈 <a href="{SITE}">Live indicator</a>"""

    return msg


def check_and_send_milestones(score, prev_score, data):
    if prev_score is None:
        return
    milestones = [
        (20, "below", "below_20"),
        (30, "below", "below_30"),
        (50, "above", "above_50"),
        (70, "above", "above_70"),
        (80, "above", "above_80"),
        (90, "above", "above_90"),
    ]
    for threshold, direction, key in milestones:
        if direction == "below" and prev_score >= threshold and score < threshold:
            msg = build_milestone_message(data, key, prev_score)
            if msg:
                print(f"  Milestone: {key}")
                send_telegram(msg)
        elif direction == "above" and prev_score < threshold and score >= threshold:
            msg = build_milestone_message(data, key, prev_score)
            if msg:
                print(f"  Milestone: {key}")
                send_telegram(msg)


def main():
    print("\n" + "=" * 50)
    print("Telegram Notifications")
    print("=" * 50)

    # Load data
    if not os.path.exists("data.json"):
        print("ERROR: data.json not found")
        return

    with open("data.json", "r") as f:
        data = json.load(f)

    score = data["score"]

    # Load history for previous score
    prev_score = None
    if os.path.exists("history.json"):
        with open("history.json", "r") as f:
            history = json.load(f)
        if len(history) >= 2:
            prev_score = history[-2]["score"]

    print(f"Score: {score}, Previous: {prev_score}")

    # 1. Send daily message
    print("\n[1] Sending daily update...")
    daily_msg = build_daily_message(data, prev_score)
    send_telegram(daily_msg)

    # 2. Check milestones
    print("\n[2] Checking milestones...")
    check_and_send_milestones(score, prev_score, data)

    print("\n✅ Telegram notifications done")


if __name__ == "__main__":
    main()
