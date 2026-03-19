# 📡 Trending Scraper — 科技内容创作者每日选题工具

> 每天自动爬取 GitHub / Hacker News / Product Hunt / YouTube 热帖，
> 打分排名 + 拆解分析 + 邮件推送，帮你找到今天最值得做的内容选题。

---

## 它能做什么

- **爬取四个平台**的今日热帖（GitHub Trending / HN / Product Hunt / YouTube）
- **四维度评分**：新鲜度 · 受众规模 · 差异化空间 · 制作难度
- **每条热帖三句话拆解**：是什么 · 为什么火 · 适合什么内容角度
- **HN 开发者趋势分析**：本周技术社区在关注什么
- **钩子公式库**：从今日标题归纳悬念型/数字型/对比型/痛点型模板
- **YouTube 内容结构模板**：工具测评 / 行业深度 / 新手教程
- **每天早上 9 点自动邮件推送**

---

## 快速开始

### 1. 安装依赖

```bash
pip3 install requests
```

### 2. 配置 API Keys

复制模板，填入你的 key：

```bash
cp .env.example .env
```

```
# .env
GITHUB_TOKEN=        # 可选，不填也能跑，只是有频率限制
PRODUCT_HUNT_CLIENT_ID=      # 必填，去 producthunt.com/v2/oauth/applications 申请
PRODUCT_HUNT_CLIENT_SECRET=  # 必填，同上
YOUTUBE_API_KEY=     # 必填，去 console.cloud.google.com 开启 YouTube Data API v3

# 邮件推送（可选）
MAIL_SENDER=         # 发件 Gmail
MAIL_PASSWORD=       # Gmail 应用专用密码（不是登录密码）
MAIL_RECEIVER=       # 收件邮箱
```

### 3. 运行

```bash
# 加载环境变量
set -a && source .env && set +a

# 抓取
python3 scripts/scrape.py --platforms github hn producthunt youtube --output output/today.json

# 生成评分简报
python3 scripts/analyze.py --input output/today.json --format scores --output output/scores-$(date +%Y-%m-%d).md

# 用 TextEdit 打开
open output/scores-$(date +%Y-%m-%d).md
```

### 4. 设置每日自动推送（macOS）

```bash
# 加载定时任务
launchctl load ~/Library/LaunchAgents/com.trending.dailyreport.plist
```

每天早上 9 点自动抓取 → 生成简报 → 发到你的邮箱。

---

## 简报结构

```
🛍️ Product Hunt TOP 10     — 今日新品，按票数排
💬 Hacker News TOP 10      — 技术社区热帖 + 开发者趋势分析
⚙️ GitHub Trending TOP 10  — 开源项目，按 Stars 排
🎬 YouTube TOP 10          — 热门视频 + 3种内容结构模板
📐 钩子公式库               — 从今日标题归纳的爆款句式
```

每条热帖包含：

```
标题 · 热度数据 · 综合评分
评分明细：新鲜度 / 受众规模 / 差异化 / 制作难度
是什么：一句话解释
为什么火：具体原因，不是模板话术
内容角度：针对这条内容的具体切入建议
```

---

## 目录结构

```
trending-scraper/
├── scripts/
│   ├── scrape.py          # 爬虫：抓取四个平台数据
│   ├── analyze.py         # 分析：评分 + 生成简报
│   ├── mailer.py          # 邮件：发送简报
│   └── daily_report.sh    # 定时任务入口
├── output/                # 每日数据和简报
├── .env.example           # 环境变量模板
└── SKILL.md               # Claude Code skill 配置
```

---

## API 申请指南

| 平台 | 申请地址 | 是否必须 |
|------|---------|---------|
| GitHub Token | github.com/settings/tokens | 否（不填有频率限制） |
| Product Hunt | producthunt.com/v2/oauth/applications | 是 |
| YouTube Data API | console.cloud.google.com | 是 |
| Gmail 应用密码 | myaccount.google.com → 安全性 → 应用专用密码 | 仅邮件推送需要 |

---

## 也可以手动使用（不需要任何 API）

如果你不想配置 API，可以手动把四个平台的标题复制粘贴，
在 Claude Code 里直接分析：

```
【GitHub Trending】
（复制 github.com/trending 的项目列表）

【Hacker News】
（复制 news.ycombinator.com 前20条标题）

【Product Hunt】
（复制今日 TOP10 产品名 + 票数）

【YouTube · AI tools 2026】
（复制搜索结果前10条视频标题）
```

粘贴后 Claude 会自动完成选题分析、评分、内容建议。

---

## License

MIT
