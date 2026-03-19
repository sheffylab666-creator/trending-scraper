#!/bin/bash
# Daily trending report: scrape → analyze → email
# Called by launchd at 9am every day

cd /Users/huihui/Downloads/trending-scraper-2

set -a && source .env && set +a

DATE=$(date +%Y-%m-%d)

# Step 1: Scrape
python3 scripts/scrape.py \
  --platforms github hn producthunt youtube \
  --output output/today.json

# Step 2: Generate scores report
python3 scripts/analyze.py \
  --input output/today.json \
  --format scores \
  --output output/scores-${DATE}.md

# Step 3: Send email
python3 scripts/mailer.py \
  --file output/scores-${DATE}.md \
  --date "${DATE}"
