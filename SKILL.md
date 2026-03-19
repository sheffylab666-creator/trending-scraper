---
name: trending-scraper
description: Scrape trending posts from GitHub, Hacker News, Product Hunt, YouTube, and Reddit, then analyze them for content creator opportunities. Use this skill whenever the user wants to find trending topics, hot posts, viral content,爬热帖, 抓趋势, 找选题, research what's popular on tech platforms, or build a content calendar based on current trends. Trigger even if they just say "what's trending" or "give me today's hot topics". Also trigger when the user pastes raw trending data and asks for topic selection, hook generation, or copy writing.
---

# Trending Scraper Skill

Two modes: **Auto**（自动爬取 + 分析）or **Manual**（用户粘贴原始数据 + 分析）。

---

## MODE A · 自动模式（Auto）

用脚本爬取 + 分析，生成完整简报。

### Step 1: Check API keys

Check environment variables (or ask the user):
- `GITHUB_TOKEN` — optional, raises rate limit
- `PRODUCT_HUNT_CLIENT_ID` + `PRODUCT_HUNT_CLIENT_SECRET` — required for Product Hunt
- `YOUTUBE_API_KEY` — required for YouTube
- HN + Reddit — no key needed

Load keys from `.env`:
```bash
set -a && source .env && set +a
```

### Step 2: Run the scraper

```bash
python3 scripts/scrape.py \
  --platforms github hn producthunt youtube \
  --output output/today.json
```

### Step 3: Analyze and open briefing

```bash
python3 scripts/analyze.py \
  --input output/today.json \
  --format briefing \
  --output output/briefing-$(date +%Y-%m-%d).md \
&& open output/briefing-$(date +%Y-%m-%d).md
```

---

## MODE B · 手动模式（Manual Paste）

用户自己从四个平台复制标题列表粘贴进来，Claude 负责选题 + 分析 + 生成文案。

**触发条件**：用户粘贴了来自以下平台的内容，并要求选题或生成文案。

### 四个平台说明

| 平台 | 是什么 | 怎么获取 |
|------|--------|---------|
| **GitHub Trending** | 开发者社区今日最热开源项目，反映一线工程师在关注什么 | 打开 github.com/trending，复制项目名称列表 |
| **Hacker News** | 技术社区头版热帖，评论质量高，话题覆盖编程/创业/AI | 打开 news.ycombinator.com，复制前20条标题 |
| **Product Hunt** | 当日新品发布榜，科技早期采用者聚集地，AI工具首选来源 | 打开 producthunt.com，复制今日TOP10产品名+票数 |
| **YouTube** | 搜索「AI tools 2026」，观看量排名前10的视频标题，反映大众关注的科技内容方向 | 在YouTube搜索，复制前10条视频标题 |

### 粘贴格式（用户按此格式提供内容）

```
【GitHub Trending】
（直接复制项目名称列表）

【Hacker News】
（前20条标题）

【Product Hunt】
（今日TOP10，带票数更好）

【YouTube · AI tools 2026】
（排名前10视频标题）
```

### 当用户粘贴数据后，执行以下步骤：

#### Step 1 · 选题

从所有条目中选出 **1个** 最适合今天发布的选题，方向优先：
1. **AI 工具 / 新产品发布**（Product Hunt 有 AI 标签 或 HN 讨论 AI 工具）
2. **科技新品测评**（有明确产品、有数据支撑）
3. **开发者工具 / 效率工具**（GitHub 高 Star 或 HN 高分）

过滤规则：
- 排除非英文/中文标题（避免小语种内容噪音）
- 排除纯政治/社会话题（受众不匹配）
- 优先选「今日首发」而非「持续讨论中」的老帖

#### Step 2 · 说明选题理由

用三个维度说明为什么选这条：
- **新鲜度**：发布时间、是否今日首发
- **受众匹配**：谁在讨论它，和目标受众（科技创作者/AI 用户）重合度
- **差异化空间**：国内/中文圈覆盖程度，信息差大小

#### Step 3 · 生成三个钩子方向

针对选出的选题，生成三个不同风格的钩子：

**版本A · 悬念型**
- 核心逻辑：制造好奇缺口，让人因为「想知道答案」而点进来
- 句式参考：「为什么 XX 突然爆火？答案和你想的不一样」
- 输出：核心角度一句话 + 示例封面标题

**版本B · 数字型**
- 核心逻辑：用具体数字开头，让人因为「相信数据」而停下来
- 句式参考：「XX 票 / XX Stars：实测值不值这个热度？」
- 输出：核心角度一句话 + 示例封面标题

**版本C · 故事/痛点型**
- 核心逻辑：第一人称经历开头，制造共鸣
- 句式参考：「用了 XX 一周之后，我把它从工具箱里删掉了」
- 输出：核心角度一句话 + 示例封面标题

#### Step 4 · 可选：生成 12 条完整文案

如果用户要求完整文案，按以下格式输出（A/B/C × 小红书/X/Threads/INS）：

```
## 版本A · 悬念型

### 小红书（中文，400-600字，口语化，含话题标签）
[封面标题]
[首图建议]
[正文：它是什么 / 为什么火 / 我的判断 / CTA]
[话题标签]

### X / Twitter（英文，Thread格式，每段≤280字）
[Thread开头]
[1/ 2/ 3/ ...]

### Threads（中文，与小红书同结构，更简洁）
[正文]

### INS（英文，同X结构，配图说明）
[正文]
```

---

## 选题评分维度（参考）

| 维度 | 说明 |
|------|------|
| 新鲜度 | 今日上线=10，48h内=7，更早=3 |
| 受众规模 | Stars/票数/Score 归一化 |
| AI相关度 | 含AI关键词加分 |
| 差异化空间 | 中文圈已有覆盖=扣分，信息差大=加分 |
| 制作难度 | 话题越复杂越难做，逆向加分 |

---

## Output format（简报结构）

```
# 今日内容创作简报 · [date]

## ❓ 什么是 ABC 测试？
[说明]

## 📄 今日选题原文
[标题 / 来源 / 热度 / 描述 / 选题理由]

## 🪝 三版钩子方向
[A / B / C 各一条]

## 📱 12条完整文案
[A/B/C × 4平台，每条含正文+CTA+标签]

## 🚀 发布分配方案 + 📊 ABC测试看板

## 📖 TOP 10原文拆解
[每条：标题 / 内容类型 / 钩子位置 / 可复用模板]
```

---

## Notes

- 自动模式结果缓存到 `output/YYYY-MM-DD.json`
- Reddit 默认爬 r/programming, r/MachineLearning, r/artificial
- YouTube 默认搜索「AI tools 2025」「developer tools review」「tech product launch」
- 手动模式不依赖任何 API，用户粘贴即可使用
