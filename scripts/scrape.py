#!/usr/bin/env python3
"""
trending-scraper · scrape.py
Fetches trending posts from GitHub, HN, Product Hunt, YouTube, Reddit.
Usage: python scrape.py --platforms github hn producthunt youtube reddit --output output/today.json
"""

import os, json, argparse, datetime, sys
from pathlib import Path

try:
    import requests
except ImportError:
    print("Missing requests. Run: pip install requests --break-system-packages")
    sys.exit(1)

DATE = datetime.date.today().isoformat()

# ── GitHub ────────────────────────────────────────────────────────────────────
def fetch_github(token=None):
    headers = {"Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    since = (datetime.date.today() - datetime.timedelta(days=1)).isoformat()
    url = f"https://api.github.com/search/repositories?q=created:>{since}&sort=stars&order=desc&per_page=20"
    r = requests.get(url, headers=headers, timeout=10)
    r.raise_for_status()
    items = []
    for repo in r.json().get("items", []):
        items.append({
            "platform": "github",
            "title": repo["full_name"],
            "description": repo.get("description", ""),
            "url": repo["html_url"],
            "score_raw": repo.get("stargazers_count", 0),
            "meta": {"language": repo.get("language"), "stars": repo.get("stargazers_count")}
        })
    return items

# ── Hacker News ───────────────────────────────────────────────────────────────
def fetch_hn():
    top = requests.get("https://hacker-news.firebaseio.com/v0/topstories.json", timeout=10).json()[:30]
    items = []
    for story_id in top:
        s = requests.get(f"https://hacker-news.firebaseio.com/v0/item/{story_id}.json", timeout=5).json()
        if not s or s.get("type") != "story":
            continue
        items.append({
            "platform": "hackernews",
            "title": s.get("title", ""),
            "description": s.get("text", "")[:200],
            "url": s.get("url") or f"https://news.ycombinator.com/item?id={story_id}",
            "score_raw": s.get("score", 0),
            "meta": {"comments": s.get("descendants", 0), "by": s.get("by")}
        })
    return items

# ── Product Hunt ──────────────────────────────────────────────────────────────
def get_ph_token(client_id, client_secret):
    r = requests.post(
        "https://api.producthunt.com/v2/oauth/token",
        json={"client_id": client_id, "client_secret": client_secret, "grant_type": "client_credentials"},
        timeout=10,
    )
    r.raise_for_status()
    return r.json()["access_token"]

def fetch_producthunt(token):
    query = """
    {
      posts(first: 20, order: VOTES) {
        edges { node {
          name tagline url
          votesCount commentsCount
          topics { edges { node { name } } }
        }}
      }
    }
    """
    r = requests.post(
        "https://api.producthunt.com/v2/api/graphql",
        json={"query": query},
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        timeout=10
    )
    r.raise_for_status()
    items = []
    for edge in r.json()["data"]["posts"]["edges"]:
        node = edge["node"]
        topics = [e["node"]["name"] for e in node.get("topics", {}).get("edges", [])]
        items.append({
            "platform": "producthunt",
            "title": node["name"],
            "description": node["tagline"],
            "url": node["url"],
            "score_raw": node.get("votesCount", 0),
            "meta": {"comments": node.get("commentsCount"), "topics": topics}
        })
    return items

# ── YouTube ───────────────────────────────────────────────────────────────────
def fetch_youtube(api_key, queries=None):
    if queries is None:
        queries = ["AI tools 2025", "developer tools review", "tech product launch"]
    items = []
    seen = set()
    for q in queries:
        url = (
            f"https://www.googleapis.com/youtube/v3/search"
            f"?part=snippet&q={requests.utils.quote(q)}&type=video"
            f"&order=viewCount&maxResults=10&publishedAfter={DATE}T00:00:00Z"
            f"&key={api_key}"
        )
        r = requests.get(url, timeout=10)
        if r.status_code != 200:
            continue
        for v in r.json().get("items", []):
            vid = v["id"].get("videoId")
            if not vid or vid in seen:
                continue
            seen.add(vid)
            s = v["snippet"]
            items.append({
                "platform": "youtube",
                "title": s["title"],
                "description": s.get("description", "")[:200],
                "url": f"https://youtube.com/watch?v={vid}",
                "score_raw": 0,  # view count needs a separate API call
                "meta": {"channel": s.get("channelTitle"), "query": q}
            })
    return items

# ── Reddit ────────────────────────────────────────────────────────────────────
def fetch_reddit(client_id, client_secret, subreddits=None):
    if subreddits is None:
        subreddits = ["programming", "MachineLearning", "artificial", "SideProject", "webdev"]
    token_r = requests.post(
        "https://www.reddit.com/api/v1/access_token",
        data={"grant_type": "client_credentials"},
        auth=(client_id, client_secret),
        headers={"User-Agent": "trending-scraper/1.0"},
        timeout=10
    )
    token_r.raise_for_status()
    access_token = token_r.json()["access_token"]
    headers = {"Authorization": f"Bearer {access_token}", "User-Agent": "trending-scraper/1.0"}
    items = []
    for sub in subreddits:
        r = requests.get(
            f"https://oauth.reddit.com/r/{sub}/hot?limit=10",
            headers=headers, timeout=10
        )
        if r.status_code != 200:
            continue
        for post in r.json()["data"]["children"]:
            d = post["data"]
            if d.get("stickied"):
                continue
            items.append({
                "platform": f"reddit/r/{sub}",
                "title": d["title"],
                "description": d.get("selftext", "")[:200],
                "url": f"https://reddit.com{d['permalink']}",
                "score_raw": d.get("score", 0),
                "meta": {"comments": d.get("num_comments"), "flair": d.get("link_flair_text")}
            })
    return items

# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--platforms", nargs="+", default=["github","hn","producthunt","youtube"])
    parser.add_argument("--output", default="output/today.json")
    args = parser.parse_args()

    results = []
    p = args.platforms

    if "github" in p:
        try:
            results += fetch_github(token=os.getenv("GITHUB_TOKEN"))
            print(f"✓ GitHub: {len([x for x in results if x['platform']=='github'])} items")
        except Exception as e:
            print(f"✗ GitHub: {e}")

    if "hn" in p:
        try:
            before = len(results)
            results += fetch_hn()
            print(f"✓ Hacker News: {len(results)-before} items")
        except Exception as e:
            print(f"✗ Hacker News: {e}")

    if "producthunt" in p:
        cid  = os.getenv("PRODUCT_HUNT_CLIENT_ID")
        csec = os.getenv("PRODUCT_HUNT_CLIENT_SECRET")
        token = os.getenv("PRODUCT_HUNT_TOKEN")  # fallback if user has direct token
        if not token and (not cid or not csec):
            print("✗ Product Hunt: set PRODUCT_HUNT_CLIENT_ID + PRODUCT_HUNT_CLIENT_SECRET")
        else:
            try:
                if not token:
                    token = get_ph_token(cid, csec)
                before = len(results)
                results += fetch_producthunt(token)
                print(f"✓ Product Hunt: {len(results)-before} items")
            except Exception as e:
                print(f"✗ Product Hunt: {e}")

    if "youtube" in p:
        key = os.getenv("YOUTUBE_API_KEY")
        if not key:
            print("✗ YouTube: YOUTUBE_API_KEY not set")
        else:
            try:
                before = len(results)
                results += fetch_youtube(key)
                print(f"✓ YouTube: {len(results)-before} items")
            except Exception as e:
                print(f"✗ YouTube: {e}")

    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    payload = {"date": DATE, "items": results}
    with open(args.output, "w") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    print(f"\n✓ Saved {len(results)} items → {args.output}")

if __name__ == "__main__":
    main()
