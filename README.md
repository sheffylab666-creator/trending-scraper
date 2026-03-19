# Trending Scraper

> Daily trending posts from GitHub, Hacker News, Product Hunt, and YouTube — scored, analyzed, and delivered to your inbox every morning.

Built for tech content creators who want to find today's best topics without spending hours on research.

---

## What it does

- **Scrapes four platforms** — GitHub Trending, Hacker News, Product Hunt, YouTube
- **Scores every post** across four dimensions: freshness · audience size · differentiation · production difficulty
- **Three-sentence breakdown per post** — what it is · why it's trending · best content angle
- **HN developer trend summary** — what the tech community is focused on this week
- **Hook formula library** — suspense / number / contrast / pain-point templates extracted from today's titles
- **YouTube content structure templates** — tool review / industry deep-dive / beginner tutorial
- **Automated email delivery at 9 AM daily**

---

## Quickstart

### 1. Install dependencies

```bash
pip3 install requests
```

### 2. Configure API keys

Copy the template and fill in your keys:

```bash
cp .env.example .env
```

```
# .env
GITHUB_TOKEN=               # Optional — works without it, but rate-limited
PRODUCT_HUNT_CLIENT_ID=     # Required — get it at producthunt.com/v2/oauth/applications
PRODUCT_HUNT_CLIENT_SECRET= # Required — same as above
YOUTUBE_API_KEY=            # Required — enable YouTube Data API v3 at console.cloud.google.com

# Email delivery (optional)
MAIL_SENDER=                # Your Gmail address
MAIL_PASSWORD=              # Gmail app password (not your login password)
MAIL_RECEIVER=              # Destination email
```

### 3. Run

```bash
# Load environment variables
set -a && source .env && set +a

# Scrape
python3 scripts/scrape.py --platforms github hn producthunt youtube --output output/today.json

# Generate scored briefing
python3 scripts/analyze.py --input output/today.json --format scores --output output/scores-$(date +%Y-%m-%d).md

# Open the briefing
open output/scores-$(date +%Y-%m-%d).md
```

### 4. Schedule daily delivery (macOS)

```bash
launchctl load ~/Library/LaunchAgents/com.trending.dailyreport.plist
```

Every morning at 9 AM: scrape → score → email.

---

## Briefing structure

```
🛍️ Product Hunt TOP 10     — today's new launches, ranked by votes
💬 Hacker News TOP 10      — tech community hot posts + developer trend summary
⚙️ GitHub Trending TOP 10  — open source projects, ranked by stars
🎬 YouTube TOP 10          — trending videos + 3 content structure templates
📐 Hook formula library    — viral sentence patterns extracted from today's titles
```

Each post includes:

```
Title · engagement data · composite score
Score breakdown: freshness / audience / differentiation / difficulty
What it is: one-sentence explanation
Why it's trending: specific reasons, not generic filler
Content angle: a concrete take on how to cover this topic
```

---

## Project structure

```
trending-scraper/
├── scripts/
│   ├── scrape.py          # Scraper: fetches data from all four platforms
│   ├── analyze.py         # Analyzer: scoring + briefing generation
│   ├── mailer.py          # Mailer: sends the briefing
│   └── daily_report.sh    # Scheduler entry point
├── output/                # Daily data and briefings
├── .env.example           # Environment variable template
└── SKILL.md               # Claude Code skill config
```

---

## API setup

| Platform | Where to apply | Required |
|----------|---------------|----------|
| GitHub Token | github.com/settings/tokens | No (rate-limited without it) |
| Product Hunt | producthunt.com/v2/oauth/applications | Yes |
| YouTube Data API | console.cloud.google.com | Yes |
| Gmail app password | myaccount.google.com → Security → App passwords | Only for email delivery |
---

## License

MIT
