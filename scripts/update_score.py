"""
btctothemoon.uk - BTC 周期评分脚本
每天由 GitHub Actions 自动运行，输出 data.json

数据源（全部免费，无需 API Key）：
1. Alternative.me - 恐惧贪婪指数
2. CoinGecko - BTC 价格 + 200日均线 + 市场占比
3. Binance - 永续合约资金费率
"""

import json
import urllib.request
import urllib.error
import time
from datetime import datetime, timezone

# ============================================
# 数据采集
# ============================================

def fetch_json(url, retries=2):
    """带重试的 JSON 请求"""
    for i in range(retries + 1):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "btctothemoon/1.0"})
            with urllib.request.urlopen(req, timeout=15) as resp:
                return json.loads(resp.read().decode())
        except Exception as e:
            if i < retries:
                time.sleep(2)
            else:
                print(f"[ERROR] {url}: {e}")
                return None


def get_fear_greed():
    """恐惧贪婪指数 (0-100)"""
    data = fetch_json("https://api.alternative.me/fng/?limit=1")
    if data and "data" in data:
        return int(data["data"][0]["value"])
    return None


def get_btc_price_and_200dma():
    """当前价格 + 200日均线"""
    # 获取 201 天的日线数据（多取1天确保够200天计算）
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
    deviation_pct = ((current_price / ma_200) - 1) * 100  # +50 means 50% above MA

    return current_price, ma_200, deviation_pct


def get_funding_rate():
    """Binance BTCUSDT 永续合约最近一次资金费率"""
    data = fetch_json(
        "https://fapi.binance.com/fapi/v1/fundingRate"
        "?symbol=BTCUSDT&limit=1"
    )
    if data and len(data) > 0:
        return float(data[0]["fundingRate"])
    return None


def get_btc_dominance():
    """BTC 市场占比 (%)"""
    data = fetch_json("https://api.coingecko.com/api/v3/global")
    if data and "data" in data:
        return data["data"]["market_cap_percentage"].get("btc")
    return None


# ============================================
# 评分逻辑
# ============================================

def clamp(val, lo=0, hi=100):
    return max(lo, min(hi, val))


def score_fear_greed(value):
    """恐惧贪婪指数直接作为子分 (0-100)"""
    if value is None:
        return 50  # 默认中性
    return clamp(value)


def score_price_deviation(deviation_pct):
    """
    价格相对200日均线的偏离度 → 子分
    历史参考：
    - 熊市底部：-30% ~ -50%（2018, 2022）
    - 均线附近：0%（积累期）
    - 牛市中段：+50% ~ +80%
    - 牛市顶部：+100% ~ +200%（2017: +200%, 2021: +120%）
    """
    if deviation_pct is None:
        return 50

    if deviation_pct <= -40:
        return 5
    elif deviation_pct <= -20:
        return 15 + (deviation_pct + 40) * (20 / 20)  # 15-35
    elif deviation_pct <= 0:
        return 35 + (deviation_pct + 20) * (10 / 20)   # 35-45
    elif deviation_pct <= 50:
        return 45 + deviation_pct * (20 / 50)           # 45-65
    elif deviation_pct <= 100:
        return 65 + (deviation_pct - 50) * (20 / 50)    # 65-85
    elif deviation_pct <= 200:
        return 85 + (deviation_pct - 100) * (12 / 100)  # 85-97
    else:
        return 98


def score_funding_rate(rate):
    """
    资金费率 → 子分
    正常值：0.01% (0.0001)
    极端看多：>0.1% (0.001)
    负值：看空情绪
    """
    if rate is None:
        return 50

    rate_pct = rate * 100  # 转成百分比，如 0.01 = 1%... 不对
    # rate 本身就是小数，如 0.0001 = 0.01%
    rate_bps = rate * 10000  # 转成基点，0.0001 → 1 bps = 0.01%

    if rate_bps <= -5:
        return 10
    elif rate_bps <= 0:
        return 10 + (rate_bps + 5) * (-6)  # 10-40
    elif rate_bps <= 1:
        return 40 + rate_bps * 10           # 40-50
    elif rate_bps <= 3:
        return 50 + (rate_bps - 1) * 10     # 50-70
    elif rate_bps <= 8:
        return 70 + (rate_bps - 3) * 4      # 70-90
    else:
        return clamp(90 + (rate_bps - 8) * 2)  # 90+


def score_dominance(dom):
    """
    BTC 市场占比 → 子分
    高占比（>60%）通常在周期早期/熊市 → 低分
    低占比（<40%）通常在山寨季/周期末 → 高分
    """
    if dom is None:
        return 50

    if dom >= 65:
        return 15
    elif dom >= 55:
        return 15 + (65 - dom) * (25 / 10)  # 15-40
    elif dom >= 48:
        return 40 + (55 - dom) * (20 / 7)   # 40-60
    elif dom >= 40:
        return 60 + (48 - dom) * (20 / 8)   # 60-80
    else:
        return clamp(80 + (40 - dom) * 2)    # 80+


def calculate_composite(fg_score, price_score, funding_score, dom_score):
    """加权综合评分"""
    weights = {
        "fear_greed": 0.25,
        "price_200dma": 0.35,
        "funding_rate": 0.15,
        "dominance": 0.25,
    }
    composite = (
        fg_score * weights["fear_greed"]
        + price_score * weights["price_200dma"]
        + funding_score * weights["funding_rate"]
        + dom_score * weights["dominance"]
    )
    return round(clamp(composite))


# ============================================
# 输出
# ============================================

def get_status(sub_score):
    if sub_score <= 25:
        return "cold"
    elif sub_score <= 45:
        return "positive"
    elif sub_score <= 60:
        return "neutral"
    elif sub_score <= 80:
        return "warm"
    else:
        return "hot"


def generate_summary(score):
    if score <= 15:
        return "多项链上指标处于历史低位区域。市场极度恐慌，长期来看可能接近周期底部。但底部可能持续很久，不建议试图精确抄底。"
    elif score <= 30:
        return "市场处于偏冷区域，价格低于长期均值。历史上类似阶段往往是长期积累的时期，但下行风险仍然存在。"
    elif score <= 45:
        return "市场处于温和区域，各项指标趋于中性。可能正在从底部恢复，也可能处于横盘整理阶段。"
    elif score <= 60:
        return "多项指标显示市场处于周期中段。情绪逐步回暖，风险在可控范围内，但需要持续关注变化趋势。"
    elif score <= 75:
        return "市场进入偏热区域，部分指标开始偏离均值。历史上类似阶段往往伴随加速上涨，但也意味着风险在累积。建议开始考虑风控计划。"
    elif score <= 90:
        return "多项指标进入历史高位区域，市场情绪偏向过热。历史上类似信号出现后，顶部可能在数周到数月内到来。建议认真审视持仓风险。"
    else:
        return "多项指标处于历史极端值附近。需要高度警惕，历史上类似阶段距离周期顶部往往不远。这不是精确预测，但风险已经很高。"


def main():
    print("=" * 50)
    print(f"BTC 周期评分 - {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print("=" * 50)

    # 采集数据
    print("\n[1/4] 获取恐惧贪婪指数...")
    fg_value = get_fear_greed()
    print(f"  → {fg_value}")

    print("[2/4] 获取 BTC 价格和 200 日均线...")
    price, ma_200, deviation = get_btc_price_and_200dma()
    print(f"  → 价格: ${price:,.0f}, 200DMA: ${ma_200:,.0f}, 偏离: {deviation:+.1f}%" if price else "  → 获取失败")

    # CoinGecko 有频率限制，等一下
    time.sleep(2)

    print("[3/4] 获取资金费率...")
    funding = get_funding_rate()
    print(f"  → {funding:.6f} ({funding*100:.4f}%)" if funding is not None else "  → 获取失败")

    print("[4/4] 获取 BTC 市场占比...")
    dominance = get_btc_dominance()
    print(f"  → {dominance:.1f}%" if dominance else "  → 获取失败")

    # 计算子分
    fg_score = score_fear_greed(fg_value)
    price_score = score_price_deviation(deviation)
    funding_score = score_funding_rate(funding)
    dom_score = score_dominance(dominance)

    print(f"\n子分: 恐惧贪婪={fg_score}, 价格偏离={price_score}, 资金费率={funding_score}, 占比={dom_score}")

    # 综合评分
    composite = calculate_composite(fg_score, price_score, funding_score, dom_score)
    print(f"综合评分: {composite}/100")

    # 生成输出
    now = datetime.now(timezone.utc)
    output = {
        "score": composite,
        "lastUpdated": now.strftime("%Y-%m-%d"),
        "lastUpdatedFull": now.isoformat(),
        "summary": generate_summary(composite),
        "indicators": [
            {
                "name": "恐惧贪婪指数",
                "value": fg_value,
                "sub_score": fg_score,
                "status": get_status(fg_score),
                "note": (
                    f"{fg_value}/100，" + (
                        "极度恐惧" if fg_value < 25
                        else "恐惧" if fg_value < 40
                        else "中性" if fg_value < 60
                        else "贪婪" if fg_value < 75
                        else "极度贪婪"
                    ) if fg_value is not None else "数据获取失败"
                )
            },
            {
                "name": "价格 vs 200日均线",
                "value": round(deviation, 1) if deviation else None,
                "sub_score": price_score,
                "status": get_status(price_score),
                "note": (
                    f"价格在200日均线{'上方' if deviation >= 0 else '下方'} {abs(deviation):.0f}%"
                    if deviation is not None else "数据获取失败"
                )
            },
            {
                "name": "永续合约资金费率",
                "value": funding,
                "sub_score": funding_score,
                "status": get_status(funding_score),
                "note": (
                    f"{funding*100:.4f}%"
                    + ("，偏空" if funding and funding < 0
                       else "，正常" if funding and funding < 0.0003
                       else "，偏多" if funding and funding < 0.0008
                       else "，极度看多" if funding else "")
                    if funding is not None else "数据获取失败"
                )
            },
            {
                "name": "BTC 市场占比",
                "value": round(dominance, 1) if dominance else None,
                "sub_score": dom_score,
                "status": get_status(dom_score),
                "note": (
                    f"{dominance:.1f}%"
                    + ("，占比较高（早期/熊市特征）" if dominance > 58
                       else "，正常区间" if dominance > 45
                       else "，偏低（山寨季特征）")
                    if dominance else "数据获取失败"
                )
            }
        ],
        "raw": {
            "fear_greed": fg_value,
            "btc_price": round(price) if price else None,
            "ma_200": round(ma_200) if ma_200 else None,
            "deviation_pct": round(deviation, 2) if deviation else None,
            "funding_rate": funding,
            "btc_dominance": round(dominance, 2) if dominance else None,
        }
    }

    # 写入 data.json
    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n✅ data.json 已更新 (score={composite})")


if __name__ == "__main__":
    main()
