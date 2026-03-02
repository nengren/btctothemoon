# btctothemoon.uk 开发路线图

---

## Phase 0 · 上线（第1周）

**目标：让网站能被访问**

- 把当前 HTML 部署到 btctothemoon.uk（Cloudflare Pages 或 Vercel，免费）
- 配置域名 DNS 解析
- 温度计分数由你手动填写，每周更新一次
- 币安邀请链接已嵌入，开始产生潜在收益

**交付物：** 一个能打开的网站，包含温度计 + 新手指南 + 币安链接

---

## Phase 1 · 内容 SEO（第2-4周）

**目标：让 Google 能搜到我们**

- 接入 Google Analytics + Search Console，追踪流量来源
- 新增独立页面，瞄准搜索关键词：
  - `/how-to-buy-bitcoin` — "如何购买比特币"（中文长尾词搜索量大）
  - `/what-is-bitcoin` — "比特币是什么"（入门级流量）
  - `/btc-cycle` — "比特币周期"（与温度计强关联）
- 每篇文章底部自然引导到温度计页面和币安注册
- 配置 sitemap.xml + robots.txt + Open Graph 标签（社交分享卡片）

**交付物：** 3-5篇SEO文章页面 + 流量监控就位

---

## Phase 2 · 温度计数据自动化（第3-5周）

**目标：温度计从手动更新变为自动更新**

- 确定评分模型，选取 3-5 个可免费获取的指标：
  - MVRV Z-Score（Glassnode 免费 API 或爬取 LookIntoBitcoin）
  - 200 周均线偏离度（CoinGecko API 可算）
  - 资金费率（Binance API 免费）
  - 恐惧贪婪指数（Alternative.me 免费 API）
  - 稳定币市值（CoinGecko API）
- 用 Python 脚本计算综合评分，输出 JSON
- 部署到 Oracle Cloud，每天定时运行，推送 JSON 到网站
- 网站前端读取 JSON 自动渲染

**交付物：** 温度计每日自动更新，无需手动干预

---

## Phase 3 · 传播与引流（第4-8周）

**目标：建立初始用户群**

- 温度计截图/数据同步发到 Twitter（你已有 n8n 实战日志账号，可以用加密货币相关的新号或同号发）
- 创建 Telegram 频道，每周发一次温度计周报（文字+截图）
- 在中文加密社区（如币乎、电报群、Twitter Crypto 中文圈）分享温度计
- 新手指南文章投放到知乎、Medium 中文版等平台，底部带链接回主站

**交付物：** Twitter 定期发布 + Telegram 频道启动 + 外部平台引流

---

## Phase 4 · 英文版（第6-10周）

**目标：打开英文市场，流量上一个量级**

- 新手指南和温度计页面做英文版
- 英文 SEO 关键词："bitcoin cycle indicator"、"is it too late to buy bitcoin"、"btc bull bear cycle"
- 英文内容发 Reddit（r/Bitcoin, r/CryptoCurrency）和 Medium

**交付物：** 双语网站，覆盖中英文搜索流量

---

## Phase 5 · 付费层（第8-12周，视流量决定是否启动）

**目标：验证付费意愿**

- 免费版：温度计只显示当前分数和大致阶段
- 付费版 Telegram Bot（$9.9/月）：
  - 每日详细指标数据推送
  - 关键信号变化实时提醒（如分数突破 80 或跌破 20）
  - 每周分析简报
- 前提：至少有 500+ 周活跃访客再启动这一步

**交付物：** 付费 Telegram Bot + Stripe/加密货币收款

---

## 关键里程碑

| 时间 | 里程碑 | 衡量标准 |
|------|--------|----------|
| 第1周末 | 网站上线 | 能正常访问 |
| 第4周末 | SEO内容就位 | Google 开始收录 |
| 第5周末 | 温度计自动化 | 每日自动更新 |
| 第8周末 | 初始流量 | 日均 50+ 访客 |
| 第12周末 | 验证变现 | 首批付费用户 or 币安佣金产生 |

---

## 技术栈

- **前端：** 纯 HTML/CSS/JS（当前），后续可迁移到 Next.js
- **数据采集：** Python + Oracle Cloud 定时任务
- **部署：** Cloudflare Pages（免费、全球 CDN、速度快）
- **监控：** Google Analytics + Search Console
- **推送：** Telegram Bot（你已有经验）
- **收款：** Stripe（法币）+ 链上收款（加密）

---

## 原则

1. **先有内容，再有功能。** SEO 文章比花哨功能更能带来真实流量。
2. **手动验证，再自动化。** 温度计先手动更新几周，确认评分模型合理再写代码。
3. **币安佣金是被动收入。** 不需要用户付费就能产生，是最早能验证的变现方式。
4. **诚实是护城河。** 不承诺预测准确率，只提供参考坐标。这反而让人信任。
