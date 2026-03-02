"""
btctothemoon.uk - BTC Cycle Score
Runs daily via GitHub Actions, outputs data.json

Data sources (all free, no API key):
1. Alternative.me - Fear & Greed Index
2. CoinGecko - BTC price + 200DMA + dominance
3. Binance - Perpetual funding rate (with fallbacks)
"""

import json
import urllib.request
import time
from datetime import datetime, timezone


def fetch_json(url, retries=2):
    for i in range(retries + 1):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "btctothemoon/1.0"})
            with urllib.request.urlopen(req, timeout=15) as resp:
                return json.loads(resp.read().decode())
        except Exception as e:
            if i < retries:
                time.sleep(2)
            else:
                print(f"  [FAIL] {url}: {e}")
                return None


def get_fear_greed():
    data = fetch_json("https://api.alternative.me/fng/?limit=1")
    if data and "data" in data:
        return int(data["data"][0]["value"])
    return None


def get_btc_price_and_200dma():
    data = fetch_json(
        "https://api.coingecko.com/api/v3/coins/bitcoin/market_chart"
        "?vs_currency=usd&days=201&interval=daily"
    )
    if not data or "prices" not in data:
        return None, None, None
    prices = [p[1] for p in data["prices"]]
    if len(prices) < 200:
        return None, None, None
    current_price = prices[-1]
    ma_200 = sum(prices[-200:]) / 200
    deviation_pct = ((current_price / ma_200) - 1) * 100
    return current_price, ma_200, deviation_pct


def get_funding_rate():
    domains = ["fapi.binance.com", "fapi1.binance.com", "fapi2.binance.com"]
    for domain in domains:
        data = fetch_json(f"https://{domain}/fapi/v1/fundingRate?symbol=BTCUSDT&limit=1", retries=1)
        if data and len(data) > 0:
            print(f"  [OK] from {domain}/fundingRate")
            return float(data[0]["fundingRate"])
    for domain in domains:
        data = fetch_json(f"https://{domain}/fapi/v1/premiumIndex?symbol=BTCUSDT", retries=1)
        if data and "lastFundingRate" in data:
            print(f"  [OK] from {domain}/premiumIndex")
            return float(data["lastFundingRate"])
    return None


def get_btc_dominance():
    data = fetch_json("https://api.coingecko.com/api/v3/global")
    if data and "data" in data:
        return data["data"]["market_cap_percentage"].get("btc")
    return None


def clamp(v, lo=0, hi=100):
    return max(lo, min(hi, v))


def score_fear_greed(v):
    return clamp(v) if v is not None else 50

def score_price_deviation(d):
    if d is None: return 50
    if d <= -40: return 5
    if d <= -20: return 15 + (d + 40)
    if d <= 0: return 35 + (d + 20) * 0.5
    if d <= 50: return 45 + d * 0.4
    if d <= 100: return 65 + (d - 50) * 0.4
    if d <= 200: return 85 + (d - 100) * 0.12
    return 98

def score_funding_rate(r):
    if r is None: return 50
    b = r * 10000
    if b <= -5: return 10
    if b <= 0: return 10 + (b + 5) * 6
    if b <= 1: return 40 + b * 10
    if b <= 3: return 50 + (b - 1) * 10
    if b <= 8: return 70 + (b - 3) * 4
    return clamp(90 + (b - 8) * 2)

def score_dominance(d):
    if d is None: return 50
    if d >= 65: return 15
    if d >= 55: return 15 + (65 - d) * 2.5
    if d >= 48: return 40 + (55 - d) * 2.86
    if d >= 40: return 60 + (48 - d) * 2.5
    return clamp(80 + (40 - d) * 2)


def get_status(s):
    if s <= 25: return "cold"
    if s <= 45: return "cool"
    if s <= 60: return "neutral"
    if s <= 80: return "warm"
    return "hot"


SUMMARIES = {
    "en": [
        (15, "Multiple on-chain metrics are at historical lows. Extreme fear dominates. Historically, similar phases tend to be near cycle bottoms — but bottoms can persist for a long time."),
        (30, "The market is in a cool zone with prices below long-term averages. Historically, similar phases have been accumulation periods, though downside risk remains."),
        (45, "The market is in a moderate zone with neutral indicators. Could be recovering from a bottom or consolidating sideways."),
        (60, "Indicators suggest the market is mid-cycle. Sentiment is warming. Risk is manageable but worth monitoring closely."),
        (75, "The market is entering a warm zone. Some indicators deviate from the mean. Historically, this comes with accelerating prices and accumulating risk. Consider your exit plan."),
        (90, "Multiple indicators are in historically elevated territory. Sentiment is running hot. Similar signals have preceded cycle tops by weeks to months. Review your risk exposure."),
        (100, "Indicators are near historical extremes. High vigilance warranted. Not a precise prediction, but risk is very elevated."),
    ],
    "zh": [
        (15, "多项链上指标处于历史低位区域。市场极度恐慌，长期来看可能接近周期底部，但底部可能持续很久。"),
        (30, "市场处于偏冷区域，价格低于长期均值。历史上类似阶段往往是长期积累的时期，但下行风险仍然存在。"),
        (45, "市场处于温和区域，各项指标趋于中性。可能正在从底部恢复，也可能处于横盘整理阶段。"),
        (60, "多项指标显示市场处于周期中段。情绪逐步回暖，风险在可控范围内，但需持续关注变化趋势。"),
        (75, "市场进入偏热区域，部分指标偏离均值。历史上类似阶段伴随加速上涨与风险累积。建议制定风控计划。"),
        (90, "多项指标进入历史高位区域。类似信号出现后，顶部可能在数周到数月内到来。建议审视持仓风险。"),
        (100, "多项指标处于历史极端值附近。需要高度警惕。这不是精确预测，但风险已经很高。"),
    ]
}

def get_summary(score, lang):
    for threshold, text in SUMMARIES[lang]:
        if score <= threshold:
            return text
    return SUMMARIES[lang][-1][1]


def fmt_fg(v, lang):
    if v is None: return "N/A"
    bounds = [(25, ("Extreme Fear", "极度恐惧")), (40, ("Fear", "恐惧")), (60, ("Neutral", "中性")), (75, ("Greed", "贪婪")), (101, ("Extreme Greed", "极度贪婪"))]
    idx = 0 if lang == "en" else 1
    for t, labels in bounds:
        if v < t: return f"{v}/100, {labels[idx]}"
    return f"{v}/100"

def fmt_dev(d, lang):
    if d is None: return "N/A"
    if lang == "en": return f"{abs(d):.0f}% {'above' if d >= 0 else 'below'} 200DMA"
    return f"{'上方' if d >= 0 else '下方'} {abs(d):.0f}%"

def fmt_fund(r, lang):
    if r is None: return "N/A"
    p = f"{r*100:.4f}%"
    bounds = [(0, ("bearish", "偏空")), (0.0003, ("normal", "正常")), (0.0008, ("bullish", "偏多")), (999, ("extreme", "极度看多"))]
    idx = 0 if lang == "en" else 1
    for t, labels in bounds:
        if r < t: return f"{p}, {labels[idx]}"
    return p

def fmt_dom(d, lang):
    if d is None: return "N/A"
    if lang == "en":
        if d > 58: return f"{d:.1f}%, high"
        if d > 45: return f"{d:.1f}%, normal"
        return f"{d:.1f}%, low (alt season)"
    if d > 58: return f"{d:.1f}%，偏高"
    if d > 45: return f"{d:.1f}%，正常"
    return f"{d:.1f}%，偏低（山寨季）"


def main():
    print("=" * 50)
    print(f"BTC Cycle Score - {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print("=" * 50)

    print("\n[1/4] Fear & Greed...")
    fg = get_fear_greed()
    print(f"  -> {fg}")

    print("[2/4] Price & 200DMA...")
    price, ma200, dev = get_btc_price_and_200dma()
    print(f"  -> ${price:,.0f}, dev: {dev:+.1f}%" if price else "  -> Failed")

    time.sleep(2)

    print("[3/4] Funding Rate...")
    fund = get_funding_rate()
    print(f"  -> {fund:.6f}" if fund is not None else "  -> Failed")

    print("[4/4] Dominance...")
    dom = get_btc_dominance()
    print(f"  -> {dom:.1f}%" if dom else "  -> Failed")

    s_fg = score_fear_greed(fg)
    s_pr = score_price_deviation(dev)
    s_fu = score_funding_rate(fund)
    s_do = score_dominance(dom)
    composite = round(clamp(s_fg * 0.25 + s_pr * 0.35 + s_fu * 0.15 + s_do * 0.25))

    print(f"\nScores: FG={s_fg} Price={s_pr} Fund={s_fu} Dom={s_do}")
    print(f"Composite: {composite}/100")

    now = datetime.now(timezone.utc)
    indicators = []
    if fg is not None:
        indicators.append({"key": "fear_greed", "status": get_status(s_fg), "value": fg,
            "en": {"name": "Fear & Greed", "note": fmt_fg(fg, "en")},
            "zh": {"name": "恐惧贪婪", "note": fmt_fg(fg, "zh")}})
    if dev is not None:
        indicators.append({"key": "price_200dma", "status": get_status(s_pr), "value": round(dev, 1),
            "en": {"name": "Price vs 200DMA", "note": fmt_dev(dev, "en")},
            "zh": {"name": "价格vs均线", "note": fmt_dev(dev, "zh")}})
    if fund is not None:
        indicators.append({"key": "funding_rate", "status": get_status(s_fu), "value": fund,
            "en": {"name": "Funding Rate", "note": fmt_fund(fund, "en")},
            "zh": {"name": "资金费率", "note": fmt_fund(fund, "zh")}})
    if dom is not None:
        indicators.append({"key": "dominance", "status": get_status(s_do), "value": round(dom, 1),
            "en": {"name": "BTC Dominance", "note": fmt_dom(dom, "en")},
            "zh": {"name": "BTC占比", "note": fmt_dom(dom, "zh")}})

    output = {
        "score": composite,
        "lastUpdated": now.strftime("%Y-%m-%d"),
        "summary": {"en": get_summary(composite, "en"), "zh": get_summary(composite, "zh")},
        "indicators": indicators,
        "raw": {
            "btc_price": round(price) if price else None,
            "ma_200": round(ma200) if ma200 else None,
            "fear_greed": fg,
            "deviation_pct": round(dev, 2) if dev else None,
            "funding_rate": fund,
            "btc_dominance": round(dom, 2) if dom else None,
        }
    }

    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"\n✅ data.json updated (score={composite})")

if __name__ == "__main__":
    main()
