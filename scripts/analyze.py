#!/usr/bin/env python3
"""
trending-scraper · analyze.py
Picks today's best topic and generates 12 ready-to-post copies + ABC test sheet.
Usage: python analyze.py --input output/today.json --format briefing
"""

import json, argparse, datetime
from pathlib import Path

DATE = datetime.date.today().isoformat()

# ── Scoring ────────────────────────────────────────────────────────────────────

def score_item(item):
    """
    Score each item on 4 real dimensions (each 0-10), return total and breakdown.

    新鲜度   — how fresh is this (platform launch cycle)
    受众规模 — normalized raw engagement number
    差异化   — how underserved is this topic in Chinese content
    制作难度 — inverse of complexity; simpler topic = easier to make = higher score
    """
    raw     = item.get("score_raw", 0)
    p       = item["platform"]
    title   = item["title"].lower()
    desc    = (item.get("description") or "").lower()
    topics  = item.get("meta", {}).get("topics", [])
    lang    = (item.get("meta", {}).get("language") or "").lower()

    ai_kw   = ["ai", "gpt", "llm", "claude", "gemini", "copilot", "agent",
               "model", "neural", "diffusion", "vision", "embedding"]
    tool_kw = ["tool", "app", "launch", "product", "built", "open source",
               "library", "framework", "sdk", "api", "cli"]
    deep_kw = ["theory", "research", "paper", "math", "kernel", "compiler",
               "cryptography", "distributed", "consensus", "proof"]

    # ── 新鲜度 (Freshness) ─────────────────────────────────────────────────────
    # PH / GitHub Trending = today's content by definition = 9
    # HN = real-time but mix of old links = 7
    # YouTube = search result, may not be today = 6
    if   "producthunt" in p: freshness = 9
    elif "github"      in p: freshness = 9
    elif "hackernews"  in p: freshness = 7
    elif "youtube"     in p: freshness = 6
    elif "reddit"      in p: freshness = 7
    else:                    freshness = 5

    # ── 受众规模 (Audience) ────────────────────────────────────────────────────
    # Normalize raw score to 0-10 per platform scale
    if   "github"      in p: audience = round(min(10, raw / 3000 * 10), 1)
    elif "hackernews"  in p: audience = round(min(10, raw / 500  * 10), 1)
    elif "producthunt" in p: audience = round(min(10, raw / 1000 * 10), 1)
    elif "youtube"     in p: audience = 6   # no view count available
    elif "reddit"      in p: audience = round(min(10, raw / 5000 * 10), 1)
    else:                    audience = 5

    # ── 差异化空间 (Differentiation) ──────────────────────────────────────────
    # GitHub projects in non-Python/JS niche lang = high diff (less covered in CN)
    # PH AI products = medium-high (growing but still underserved in CN)
    # HN discussion/opinion = medium (some CN creators do this)
    # YouTube mainstream = low (already heavy competition)
    diff = 5  # baseline
    if "github" in p:
        if lang in ["rust", "zig", "go", "c", "c++", "haskell", "julia"]:
            diff = 9   # niche language = almost no CN coverage
        elif any(k in title for k in ai_kw):
            diff = 8   # AI + GitHub = high diff
        else:
            diff = 7
    elif "producthunt" in p:
        if any(k in title or k in desc for k in ai_kw):
            diff = 8
        else:
            diff = 6
    elif "hackernews" in p:
        if any(k in title for k in ["ask hn", "show hn"]):
            diff = 7   # first-person or debate = differentiated angle
        else:
            diff = 5
    elif "youtube" in p:
        diff = 4       # YouTube titles already saturated

    # ── 制作难度 (Production ease, higher = easier to make) ───────────────────
    # Simple product launch or tool intro = easy (high score)
    # Deep theory / research / architecture = hard (low score)
    if any(k in title or k in desc for k in deep_kw):
        ease = 3
    elif any(k in title for k in ["ask hn", "why", "how", "what"]):
        ease = 6   # opinion / explainer = moderate
    elif any(k in title or k in desc for k in tool_kw):
        ease = 8   # product/tool intro = easy
    elif "producthunt" in p:
        ease = 8
    elif "github" in p:
        ease = 6
    else:
        ease = 5

    total = round((freshness + audience + diff + ease) / 4, 1)
    return total, {
        "新鲜度": round(freshness, 1),
        "受众规模": round(audience, 1),
        "差异化": round(diff, 1),
        "制作难度": round(ease, 1),
    }


def _is_cjk_or_latin(text):
    """Return True if text is mostly ASCII/CJK (English or Chinese), not other scripts."""
    suspicious = 0
    for ch in text:
        cp = ord(ch)
        # Allow ASCII, CJK unified, CJK ext, Hangul would be False here
        if cp > 127 and not (0x4E00 <= cp <= 0x9FFF) and not (0x3400 <= cp <= 0x4DBF):
            suspicious += 1
    return suspicious / max(len(text), 1) < 0.15


def pick_best(scored):
    """Return the single best item for today's content."""
    ai_keywords = ["ai", "gpt", "llm", "claude", "gemini", "copilot", "agent",
                   "model", "tool", "launch", "built", "open source", "product"]

    # Priority 1: producthunt with AI/tech keywords
    ph = [x for x in scored if "producthunt" in x["platform"] and _is_cjk_or_latin(x["title"])]
    ph_ai = [x for x in ph if any(k in x["title"].lower() for k in ai_keywords)]
    if ph_ai:
        return sorted(ph_ai, key=lambda x: -x["score_raw"])[0]
    if ph:
        return sorted(ph, key=lambda x: -x["score_raw"])[0]

    # Priority 2: hackernews
    hn = [x for x in scored if "hackernews" in x["platform"] and _is_cjk_or_latin(x["title"])]
    if hn:
        return sorted(hn, key=lambda x: -x["score_raw"])[0]

    # Priority 3: github
    gh = [x for x in scored if "github" in x["platform"] and _is_cjk_or_latin(x["title"])]
    if gh:
        return sorted(gh, key=lambda x: -x["total"])[0]

    # Fallback: highest score with clean title
    clean = [x for x in scored if _is_cjk_or_latin(x["title"])]
    return sorted(clean or scored, key=lambda x: -x["total"])[0]


# ── Hook generation ────────────────────────────────────────────────────────────

def make_hooks(item):
    title = item["title"]
    desc  = item.get("description") or ""
    stars = item.get("meta", {}).get("stars", "")
    pts   = item.get("score_raw", 0)
    p     = item["platform"]
    short = title.split("/")[-1] if "/" in title else title
    short30 = short[:35].rstrip(" –-,")
    short20 = short[:25].rstrip(" –-,")

    # A — Suspense
    if "quietly" in title.lower() or "secret" in title.lower():
        a_angle = "悄悄改变规则，大多数人还没意识到"
        a_title = f"大家都没注意到：{short30} 刚刚悄悄改变了规则"
    elif stars and int(str(stars).replace(",", "")) > 10000:
        a_angle = "爆火背后有一个没人说清楚的真相"
        a_title = f"GitHub {stars} Stars 背后，没人说清楚它到底解决了什么问题"
    elif "ask hn" in title.lower():
        a_angle = "工程师争论的答案，可能和你想的不一样"
        a_title = f"HN 工程师在争论这个问题，正确答案可能和你想的不一样"
    elif "price" in title.lower() or "cost" in title.lower():
        a_angle = "悄悄涨价了，用之前先看这条"
        a_title = f"悄悄涨价了——用 {short30} 之前你需要先看这条"
    else:
        a_angle = "突然爆火的背后，答案很意外"
        a_title = f"为什么 {short30} 突然爆火？我研究了评论区，答案很意外"

    # B — Number
    if stars and int(str(stars).replace(",", "")) > 0:
        b_angle = "用数据说话，实测值不值这个热度"
        b_title = f"GitHub {stars} Stars：{short} 实测值不值这个热度？"
    elif "producthunt" in p and pts > 0:
        b_angle = f"Product Hunt {pts} 票，48小时实测结论"
        b_title = f"Product Hunt {pts} 票第一：{short}，我用了 48 小时来告诉你答案"
    elif "hackernews" in p and pts > 0:
        b_angle = f"HN {pts} 分热帖，核心结论只有一句话"
        b_title = f"HN {pts} 分热帖，{short[:30]}——核心结论只有一句话"
    else:
        b_angle = "测了 7 款同类工具，数据说话"
        b_title = f"测了 7 款同类工具，{short} 最终排第几？数据说话"

    # C — Story / Pain
    if "minute" in desc.lower() or "second" in desc.lower():
        c_angle = "2小时的事它几分钟搞定，有点慌"
        c_title = f"我平时要花 2 小时的事，{short20} 用几分钟搞定了——我有点慌"
    elif "quit" in title.lower() or "mrr" in title.lower():
        c_angle = "辞职创业最反直觉的一件事"
        c_title = f"他辞职 6 个月后做到月入 $10k，说最反直觉的一件事是……"
    elif "ai" in title.lower() and ("engineer" in title.lower() or "senior" in title.lower()):
        c_angle = "同一个需求交给 AI 和同事，结果让我沉默了"
        c_title = f"我把同一个需求丢给 AI 和同事，结果让我沉默了 10 分钟"
    elif "ask hn" in title.lower():
        c_angle = "200条高赞回复，最有价值的只有一句话"
        c_title = f"我整理了 200 条高赞回复，最有价值的答案其实只有一句话"
    else:
        c_angle = "用了一周之后，我把它从工具箱里删掉了"
        c_title = f"用了 {short20} 一周之后，我把它从工具箱里删掉了——理由出乎意料"

    return {
        "A": {"angle": a_angle, "title": a_title},
        "B": {"angle": b_angle, "title": b_title},
        "C": {"angle": c_angle, "title": c_title},
    }


# ── Analysis body builder ──────────────────────────────────────────────────────

def _build_analysis_body(item):
    """
    Build genuinely long, opinionated analysis paragraphs (4-6 sentences each).
    Returns (what_cn, why_cn, how_cn, what_en, why_en, how_en).
    Each string is a full paragraph ready to drop into a post.
    """
    title    = item["title"]
    desc     = (item.get("description") or "").strip()
    p        = item["platform"]
    pts      = item.get("score_raw", 0)
    stars    = item.get("meta", {}).get("stars", "")
    comments = item.get("meta", {}).get("comments", 0)
    topics   = item.get("meta", {}).get("topics", [])
    lang     = item.get("meta", {}).get("language", "")
    short    = title.split("/")[-1] if "/" in title else title
    tlower   = title.lower()

    # ── WHAT ─────────────────────────────────────────────────────────────────
    if desc and "producthunt" in p:
        topic_str = "、".join(topics[:2]) if topics else "AI工具"
        what_cn = (
            f"{short} 是今天在 Product Hunt 上线的新产品，一句话描述是：{desc}。\n\n"
            f"我看了产品页之后的第一感觉是：这个方向有意思，但有没有说的那么好用，还得用了才知道。"
            f"它主攻的是 {topic_str} 这个方向，定位非常精准——不是什么都做的大而全平台，"
            f"而是把一件具体的事做到极致。\n"
            f"这种「单点突破」的产品逻辑，往往比功能堆砌的产品更容易出圈，"
            f"因为用户在搜这类内容的时候，需求是明确的，找到了就会用，不需要太多说服成本。"
        )
        what_en = (
            f"{short} launched on Product Hunt today. In one sentence: {desc}.\n\n"
            f"First impression: the direction is interesting, but whether it actually delivers is another question. "
            f"It's focused on {' and '.join(topics[:2]) if topics else 'productivity'} — "
            f"not a 'do everything' platform, but a single-point solution.\n"
            f"That's actually a strength. Products that do one thing extremely well tend to break through "
            f"because users searching for this have a clear need — no heavy persuasion required."
        )
    elif desc and "hackernews" in p:
        what_cn = (
            f"今天 Hacker News 首页有一篇帖子引发了 {comments} 条讨论，标题是「{title}」。\n\n"
            f"这篇帖子在说的核心事情是：{desc[:100]}。\n"
            f"在 HN，「{title[:30]}」这样的标题能上首页，背后一定有原因——"
            f"HN 的用户普遍不感冒标题党，他们投票投的是「这个话题让我有话说」。\n"
            f"所以光是这篇帖子能拿到 {pts} 分，就已经说明它触动了一个真实的技术圈痛点，"
            f"而不是某个人的一时兴起。"
        )
        what_en = (
            f"This hit the front page of Hacker News today with {comments} comments: '{title}'.\n\n"
            f"The core of what it's saying: {desc[:120]}.\n"
            f"On HN, a title like this doesn't make the front page by accident — "
            f"the community votes for 'this is something I have an opinion on', not clickbait.\n"
            f"Getting {pts} points means it genuinely landed on a real pain point or debate, "
            f"not just a curiosity spike."
        )
    elif desc and "github" in p:
        lang_str = f"，主要用 {lang} 写的" if lang else ""
        what_cn = (
            f"{short} 是今天 GitHub Trending 上排名靠前的开源项目{lang_str}，"
            f"它在做的事情是：{desc[:80]}。\n\n"
            f"现在已经有 {stars} 个 Star——这个数字比很多人想象的更有参考价值。\n"
            f"Star 不是点赞，开发者 Star 一个项目，通常意味着「我认为这东西有用，我想留着以后用」。\n"
            f"所以 {stars} Stars，就是 {stars} 个开发者说「这个工具解决了我真实存在的问题」——"
            f"这比任何产品文案都有说服力。"
        )
        what_en = (
            f"{short} is trending on GitHub today{f', written in {lang}' if lang else ''}. "
            f"What it does: {desc[:100]}.\n\n"
            f"It has {stars} stars already — a more meaningful number than it looks.\n"
            f"A GitHub star isn't a like. Developers star things they actually intend to use.\n"
            f"So {stars} stars = {stars} developers saying 'this solves a real problem I have' — "
            f"that's stronger than any product copy."
        )
    elif desc:
        what_cn = (
            f"{short} 最近在科技圈引发了讨论，它在做的事情是：{desc[:100]}。\n\n"
            f"我第一次看到这个产品的时候，第一反应是「这个方向早就应该有人做了」。\n"
            f"不是说它多革命性，而是它解决的问题足够具体、足够真实——"
            f"这类产品的特点是，用过的人会立刻理解它的价值，没用过的人光看描述可能会觉得「就这？」\n"
            f"但「就这」通常是最高效的产品逻辑：不试图做所有事，只把一件事做到不可替代。"
        )
        what_en = (
            f"{short} is getting attention in the tech community. What it does: {desc[:120]}.\n\n"
            f"My first reaction when I saw this: 'someone should have built this already.'\n"
            f"Not because it's revolutionary, but because the problem it solves is specific and real.\n"
            f"Products like this have a split reaction: people who've felt the pain get it immediately, "
            f"others wonder 'that's it?' But 'that's it' is often the strongest product logic — "
            f"do one thing, make it irreplaceable."
        )
    elif "producthunt" in p:
        topic_str = "、".join(topics[:2]) if topics else "科技工具"
        what_cn = (
            f"{short} 今天在 Product Hunt 上线，主攻方向是 {topic_str}。\n\n"
            f"产品页的信息不多，但从它被投票的方式来看——{pts:,} 票、排在今日前列——"
            f"说明它切中了某个早期用户的真实需求。\n"
            f"Product Hunt 上的高票产品有一个共同特点：要么功能极简、要么解决了一个被忽视已久的痛点。\n"
            f"从这个产品的定位来看，更接近后者——它不是在和大工具抢用户，"
            f"而是在服务一个大工具懒得照顾的细分场景。"
        )
        what_en = (
            f"{short} launched on Product Hunt today, focused on {' and '.join(topics[:2]) if topics else 'productivity'}.\n\n"
            f"Limited product info available, but the voting pattern — {pts:,} votes, top of today's list — "
            f"signals it hit a real early-adopter need.\n"
            f"High-vote PH products share one trait: either extremely simple UX, or a long-ignored pain point.\n"
            f"This one looks like the second — it's not competing with big tools, "
            f"it's serving a niche those tools are too lazy to address."
        )
    elif "hackernews" in p:
        what_cn = (
            f"今天 Hacker News 首页：「{title}」，{pts} 分，{comments} 条评论。\n\n"
            f"能上 HN 首页的内容，有一个基本门槛：要么技术含量够高，要么观点够有争议，要么两者都有。\n"
            f"这篇帖子的标题本身就在制造一种张力——它不是在陈述事实，而是在提出一个让人想反驳的观点。\n"
            f"HN 社区里最好的讨论往往不是「原帖说得对」，而是「原帖说得不全对，但引出了更深的问题」——"
            f"这篇帖子正在做的，就是这件事。"
        )
        what_en = (
            f"Hacker News front page today: '{title}' — {pts} points, {comments} comments.\n\n"
            f"HN front-page content clears a basic bar: high technical depth, controversial opinion, or both.\n"
            f"This title creates tension — it's not stating a fact, it's making a claim people want to argue with.\n"
            f"The best HN threads aren't 'the post was right' but 'the post was partly wrong and "
            f"that led to something more interesting' — and that's exactly what this is doing."
        )
    else:
        what_cn = (
            f"{short} 今天在技术社区引发了广泛讨论，热度来自多个平台同时发酵。\n\n"
            f"这类内容能火，通常是因为它踩中了某个「大家都感受到了、但没人说清楚」的现象。\n"
            f"我自己看了一遍，觉得最值得关注的不是它的结论，而是它提出问题的方式——"
            f"把一个复杂的现象压缩成一个让人想转发的句子，这本身就是一种能力，值得学。\n"
            f"如果你在做内容，这种「把模糊的感受说清楚」的技能，比任何写作技巧都更核心。"
        )
        what_en = (
            f"{short} is generating discussion across tech communities today.\n\n"
            f"Content like this takes off because it names something people feel but haven't articulated.\n"
            f"What I find most interesting isn't the conclusion — it's how the question is framed.\n"
            f"Compressing a complex phenomenon into one shareable sentence is a skill. "
            f"If you're a content creator, 'making the vague feeling concrete' is more valuable than any writing hack."
        )

    # ── WHY ──────────────────────────────────────────────────────────────────
    if "producthunt" in p and pts > 800:
        why_cn = (
            f"上线当天 {pts:,} 票——我查了一下，Product Hunt 上大多数产品首日能到 100 票已经算不错了，"
            f"500 票以上属于当日头部，超过 1000 票基本是年度级别的产品。\n\n"
            f"{pts:,} 票意味着什么？意味着今天有至少 {pts:,} 个真实的科技从业者或爱好者，"
            f"看到这个产品之后觉得「值得投票支持」。\n"
            f"Product Hunt 的投票机制决定了这个数字很难造假——用户要登录、要有一定账号历史才能投票，"
            f"而且社区对刷票行为非常敏感，一旦发现会被降权。\n"
            f"所以 {pts:,} 票，就是 {pts:,} 个人在用真实的行动说：「我觉得这个东西有价值。」"
        )
        why_en = (
            f"{pts:,} votes on launch day. For context: most PH products get under 100 votes, "
            f"500+ puts you in the day's top tier, 1000+ is annual-level traction.\n\n"
            f"What {pts:,} votes actually means: at least {pts:,} real tech professionals looked at this "
            f"and decided it was worth their endorsement.\n"
            f"PH's voting mechanism makes this hard to fake — you need login history, "
            f"and the community actively polices vote manipulation.\n"
            f"So {pts:,} votes = {pts:,} people taking a real action to say 'I believe this has value.'"
        )
    elif "producthunt" in p and pts > 0:
        why_cn = (
            f"{pts:,} 票，这是今天上线的产品里的前列成绩。\n\n"
            f"Product Hunt 的用户画像很有意思：他们大多数是设计师、开发者、产品经理、创业者——"
            f"恰好也是最愿意尝鲜、最容易成为早期传播节点的人群。\n"
            f"这些人今天在 PH 上投票，两周后就会出现在 Twitter、YouTube、播客里谈论它。\n"
            f"所以 Product Hunt 的热度，不只是 PH 自己的事——它其实是整个科技内容圈下一波讨论的预告片。\n"
            f"你现在做这条内容，等于在预告片还没播完的时候，先把影评写好了。"
        )
        why_en = (
            f"{pts:,} votes — top of today's Product Hunt list.\n\n"
            f"The PH user profile is interesting: mostly designers, developers, PMs, founders — "
            f"exactly the people most likely to try new things and become early evangelists.\n"
            f"People who vote on PH today will be talking about it on Twitter, YouTube, and podcasts in two weeks.\n"
            f"So PH traction isn't just a PH story — it's a preview of what the broader tech content world "
            f"will be discussing next.\n"
            f"Publishing now means your review is ready before the mainstream wave hits."
        )
    elif "hackernews" in p and comments > 300:
        why_cn = (
            f"{comments} 条评论——这在 HN 是非常高的数字，大多数帖子连 50 条都达不到。\n\n"
            f"HN 用户有一个特点：他们不爱评论，但一旦评论，质量通常很高。\n"
            f"这意味着 {comments} 条回复里，有大量有观点、有经验、值得引用的内容——"
            f"你完全不需要自己原创什么，只需要去找 3-5 条最有代表性的高赞评论，整理成你的内容框架。\n"
            f"「我整理了 {comments} 条评论，挑出了最有价值的几个观点」——"
            f"这句话本身就是一个足够强的钩子，因为你替读者做了他们没时间做的事。"
        )
        why_en = (
            f"{comments} comments — that's exceptionally high for HN. Most posts don't hit 50.\n\n"
            f"HN users have a specific trait: they rarely comment, but when they do, the quality is high.\n"
            f"That means inside those {comments} replies, there's a lot of opinionated, experienced, citable content — "
            f"you don't need to originate anything yourself.\n"
            f"Just find 3-5 most-upvoted comments, structure them into your content.\n"
            f"'I went through {comments} comments and pulled the most valuable takes' — "
            f"that sentence alone is a strong hook, because you did the work your readers didn't have time to do."
        )
    elif "hackernews" in p:
        why_cn = (
            f"HN {pts} 分，{comments} 条评论。我看了一下评论区的讨论走向。\n\n"
            f"有趣的是，最高赞的评论不是在「支持」原帖观点，而是在「补充和质疑」——"
            f"这恰恰说明这个话题有真实的争议空间，不是一边倒的共识。\n"
            f"有争议的话题有一个内容创作的优势：读者会因为「我有不同看法」而主动评论，"
            f"而评论量是所有平台算法最喜欢的信号。\n"
            f"你不需要站队，你只需要把争议的两边都呈现出来，然后说「你们觉得呢？」——"
            f"这种内容的互动率通常是普通内容的 2-3 倍。"
        )
        why_en = (
            f"HN: {pts} points, {comments} comments. I looked at how the discussion played out.\n\n"
            f"Interestingly, the top comments aren't 'agreeing' with the original post — "
            f"they're adding nuance and pushing back. That means real controversy exists here, "
            f"not just a one-sided consensus.\n"
            f"Controversial topics have a content creation advantage: readers comment because "
            f"'I have a different view', and comment volume is what every platform algorithm loves.\n"
            f"You don't need to take a side. Just present both perspectives and ask 'what do you think?' — "
            f"that format consistently drives 2-3x the engagement of regular content."
        )
    elif "github" in p:
        star_int = int(str(stars).replace(",", "") or "0") if stars else 0
        if star_int > 2000:
            why_cn = (
                f"{stars} Stars，今天上了 GitHub Trending。\n\n"
                f"我来解释一下 GitHub Star 这个数字为什么比大多数人以为的更有含金量：\n"
                f"Star 不是算法推荐出来的，是开发者主动搜索、看到、觉得有价值之后手动点的。\n"
                f"而且开发者是一个「沉默的多数」——他们不爱在社交媒体上叫嚷，"
                f"但 Star 行为是真实需求的直接体现。\n"
                f"{stars} 个开发者的 Star，换算成普通内容平台的逻辑，"
                f"大概相当于几十万次「深度互动」——这个热度是真实的，不是泡沫。"
            )
            why_en = (
                f"{stars} stars, now on GitHub Trending.\n\n"
                f"Let me explain why GitHub stars are more meaningful than most people assume:\n"
                f"Stars aren't algorithm-pushed. A developer had to search, find it, read it, "
                f"decide it's worth something, and manually click.\n"
                f"Developers are a 'silent majority' — they don't shout on social media, "
                f"but a star is a direct signal of genuine need.\n"
                f"{stars} developer stars, translated to mainstream platform logic, "
                f"is roughly equivalent to hundreds of thousands of 'deep engagements' — "
                f"this is real traction, not noise."
            )
        else:
            why_cn = (
                f"刚上 GitHub Trending，{stars} Stars。这个阶段是关注的最佳时机。\n\n"
                f"GitHub Trending 的流量窗口比大多数人意识到的要短——"
                f"一个项目在 Trending 上通常只有 1-3 天，之后会被新项目替代。\n"
                f"但在这 1-3 天里，它会被大量开发者发现、Star、Fork，然后出现在各种 Newsletter 和 Twitter 帖子里。\n"
                f"你现在做内容，是在这个传播链的最前端——"
                f"等到主流科技媒体报道这个项目，那已经是 2-4 周之后的事了，"
                f"而你的内容到那时候可能已经沉淀了一批真实的观看和互动数据。"
            )
            why_en = (
                f"Just hit GitHub Trending with {stars} stars. This is the optimal window.\n\n"
                f"The Trending window is shorter than most realize — a project typically stays on the list "
                f"for 1-3 days before being replaced.\n"
                f"But in that window, it gets discovered, starred, and forked by a wave of developers, "
                f"then starts appearing in newsletters and Twitter threads.\n"
                f"Publishing now puts you at the front of that distribution chain — "
                f"by the time mainstream tech media covers this in 2-4 weeks, "
                f"your content will already have real engagement data."
            )
    else:
        why_cn = (
            f"这条内容今天能在多个平台同时出现，本身就说明了一件事：它的时机踩得很准。\n\n"
            f"互联网上的热度有一个规律：真正能爆发的内容，往往是「这个问题大家其实早就想过，"
            f"但今天才有人把它说得这么清楚」。\n"
            f"这类内容的传播路径是：少数人发现 → 转发给朋友 → 朋友觉得「我也有这个感受」→ 继续转发。\n"
            f"每一个转发节点的核心驱动力，不是「这个内容牛」，而是「这个内容让我觉得被理解了」。\n"
            f"这就是为什么共鸣型内容的传播速度，往往比纯干货型内容快得多。"
        )
        why_en = (
            f"This appearing across multiple platforms simultaneously signals something: perfect timing.\n\n"
            f"Viral content follows a pattern: 'this question existed for a while, "
            f"but today someone finally said it clearly.'\n"
            f"The distribution path: a few people discover it → share with friends → "
            f"friends think 'I feel this too' → keep sharing.\n"
            f"The core driver at each node isn't 'this content is great' — "
            f"it's 'this content makes me feel understood.'\n"
            f"That's why resonance-driven content spreads faster than pure information content."
        )

    # ── HOW ──────────────────────────────────────────────────────────────────
    if any(w in tlower for w in ["replace", "alternative", "import", "migrate", "switch", "from chatgpt", "to claude"]):
        how_cn = (
            f"我觉得这条内容最值得切入的角度是「迁移成本」。\n\n"
            f"很多人想从一个工具切换到另一个，卡住的不是「新工具好不好用」，"
            f"而是「我的数据、我的习惯、我的历史记录，能带走吗？」\n"
            f"这个产品在做的事，就是把这个迁移门槛降低——这是一个非常聪明的切入点，"
            f"因为它不是在和竞品争功能，而是在争「迁移意愿」。\n"
            f"你的内容框架建议：第一步，解释「迁移痛点」是什么（让读者点头）；"
            f"第二步，展示这个产品怎么解决它（让读者觉得有用）；"
            f"第三步，告诉读者「你现在可以这样做」（推动行动）。\n"
            f"这三步走下来，不需要你是专家，读者就会觉得你帮了他们一个大忙。"
        )
        how_en = (
            f"The angle I'd take: migration cost.\n\n"
            f"Most people who want to switch tools aren't stuck on 'is the new tool better?' — "
            f"they're stuck on 'can I bring my data, habits, and history with me?'\n"
            f"What this product does is lower that migration threshold — a smart move "
            f"because it's not competing on features, it's competing on switching willingness.\n"
            f"Suggested content structure: Step 1, name the migration pain (get readers nodding); "
            f"Step 2, show how this product solves it (make them feel the value); "
            f"Step 3, tell them exactly what to do now (drive action).\n"
            f"You don't need to be an expert. This three-step structure makes readers feel you saved them real effort."
        )
    elif any(w in tlower for w in ["rules", "principles", "lessons", "programming"]):
        how_cn = (
            f"这篇英文帖子的内容，大多数中文创作者根本不知道存在——这就是你的信息差。\n\n"
            f"但我建议你不要做纯翻译，原因是：翻译没有门槛，你翻别人也能翻，没有护城河。\n"
            f"你要做的是「翻译 + 本土化解读」：这些规则放在中国的工作环境里，哪些适用？哪些根本用不上？\n"
            f"这种「时间检验」的角度，比直接翻译有意思得多，而且读者会觉得你有独立的判断，而不是一个搬运工。\n"
            f"目标长度：中文内容 800-1200 字，附上原文链接，说明你的信息来源，建立可信度。"
        )
        how_en = (
            f"Most Chinese-language creators don't know this English post exists — that's your edge.\n\n"
            f"But I'd skip pure translation. Translation has no moat — if you can do it, so can anyone else.\n"
            f"Do translation + localized interpretation: which of these rules hold in your audience's work environment? "
            f"Which don't apply at all?\n"
            f"That 'time test' framing is more interesting than a straight translation, "
            f"and readers will feel you have independent judgment, not just a copy-paste operation.\n"
            f"Target: 800-1200 words, link to original, cite your source clearly — builds credibility."
        )
    elif "producthunt" in p:
        how_cn = (
            f"绝大多数人不看 Product Hunt——这本身就是你做这类内容的核心优势。\n\n"
            f"你的定位可以是：「我每天替你盯着 PH，挑出一个值得你花 5 分钟了解的产品。」\n"
            f"这个定位有三个好处：一，持续更新的理由（每天都有新内容）；"
            f"二，建立专业感（你成了「AI工具情报站」）；"
            f"三，读者黏性强（他们会等你的下一条）。\n"
            f"今天这条内容的具体写法建议：开头用「{short} 今天在 PH 拿了 {pts} 票」这个数字做钩子，"
            f"然后用 3 分钟能读完的篇幅，说清楚「它是什么、为什么值得关注、你现在能怎么用」。\n"
            f"不需要你真的深度测试，「我替你研究了」这个姿态本身就有价值。"
        )
        how_en = (
            f"Most people don't browse Product Hunt — that's your core content advantage.\n\n"
            f"Your positioning: 'I monitor PH daily and surface the one product worth 5 minutes of your attention.'\n"
            f"Three benefits of this positioning: repeatable format (new content every day); "
            f"builds expertise perception ('AI tool intelligence source'); "
            f"creates reader loyalty (they come back for the next one).\n"
            f"Specific approach for today's post: open with the {pts} vote number as your hook, "
            f"then use a 3-minute read to cover what it is, why it matters, and what to do with it.\n"
            f"You don't need to do deep testing. 'I researched this for you' is itself the value."
        )
    elif "github" in p:
        how_cn = (
            f"大多数做科技内容的人，素材来源是国内科技媒体——但这些媒体往往比 GitHub Trending 慢 2-4 周。\n\n"
            f"你做这条内容的优势就是「时间差」：等别人开始写这个项目，你已经发出去了，"
            f"甚至可能已经收到了第一批评论和数据。\n"
            f"内容框架我建议这样走：\n"
            f"① 它是什么（一句话，不超过 30 字）\n"
            f"② 解决什么问题（用一个具体的场景，不要讲技术细节）\n"
            f"③ 和同类工具比有什么不同（找一个最明显的差异点）\n"
            f"④ 适合谁用（越具体越好，比如「如果你每天要处理 XX 这类事情」）\n"
            f"这个框架不需要你很懂技术，只需要你能把复杂的东西讲清楚——而这恰好是内容创作者的本职工作。"
        )
        how_en = (
            f"Most tech content creators source from mainstream tech media — "
            f"which is 2-4 weeks behind GitHub Trending.\n\n"
            f"Your edge is the time gap: by the time others write about this project, "
            f"you've already published and may have first engagement data.\n"
            f"Content framework I'd suggest:\n"
            f"① What it is (one sentence, no jargon)\n"
            f"② What problem it solves (use a specific scenario, not technical details)\n"
            f"③ How it's different from alternatives (one clearest differentiator)\n"
            f"④ Who should use it (the more specific the better — 'if you regularly deal with X')\n"
            f"This framework doesn't require deep technical knowledge. "
            f"You just need to make complex things clear — which is exactly what content creators do best."
        )
    else:
        how_cn = (
            f"这条内容你完全可以用「信息整合」的视角来做，不需要你是这个领域的专家。\n\n"
            f"具体怎么做：去看原帖的评论区，找到获赞最高的 3-5 条评论，"
            f"把这些评论里最有价值的观点整理出来，加上你自己的一句话判断。\n"
            f"「我整理了 XX 条评论，最有共识的观点是……最有争议的是……我自己的看法是……」\n"
            f"——这个结构本身就是一个完整的内容，而且比你自己瞎想 1000 字要有说服力得多。\n"
            f"为什么？因为评论区里说话的人是真实的用户，而不是产品自己的宣传文案。\n"
            f"「真实用户怎么说」这个角度，永远比「产品自己怎么说」更有信任感。"
        )
        how_en = (
            f"You can take an 'information synthesis' angle here without being an expert in this space.\n\n"
            f"How to do it: go to the original post's comments, find the 3-5 most-upvoted responses, "
            f"pull the most valuable insights, and add one sentence of your own judgment.\n"
            f"'I went through X comments. The most agreed-upon point: ... The most debated: ... My take: ...'\n"
            f"That structure is a complete piece of content — and far more credible than 1000 words of pure opinion.\n"
            f"Why? Because the people in the comments are real users, not the product's own marketing copy.\n"
            f"'What actual users say' will always be more trusted than 'what the product says about itself.'"
        )

    return what_cn, why_cn, how_cn, what_en, why_en, how_en


# ── 12-copy generation ─────────────────────────────────────────────────────────

def make_12_copies(item, hooks):
    short    = item["title"].split("/")[-1] if "/" in item["title"] else item["title"]
    desc     = (item.get("description") or "").strip()
    pts      = item.get("score_raw", 0)
    p        = item["platform"]
    stars    = item.get("meta", {}).get("stars", "")
    comments = item.get("meta", {}).get("comments", 0)
    score    = min(10, round(item.get("total", 7.5), 1))
    tag_word = short[:8].replace(" ", "").replace("/", "")
    tags_cn  = f"#AI工具 #科技新品 #效率工具 #工具测评 #{tag_word}"
    tags_en  = "#AItools #TechReview #ProductivityTools"

    what_cn, why_cn, how_cn, what_en, why_en, how_en = _build_analysis_body(item)

    if "producthunt" in p:
        source_cn = f"Product Hunt 今日 {pts:,} 票"
        source_en = f"Product Hunt — {pts:,} votes on launch day"
        cta_cn    = "我会继续跟进后续体验，如果你也在关注这个方向，评论区聊聊 👇"
        cta_en    = "Following this closely — drop your thoughts below if you're in this space."
    elif "hackernews" in p:
        source_cn = f"Hacker News 今日 {pts:,} 分 · {comments} 条评论"
        source_en = f"Hacker News — {pts:,} pts today, {comments} comments"
        cta_cn    = "你们对这个问题怎么看？和 HN 评论区的观点一样吗？评论区见 👇"
        cta_en    = "Curious if your take matches the HN community — drop it below."
    elif "github" in p:
        source_cn = f"GitHub Trending 今日 · {stars} Stars"
        source_en = f"GitHub Trending today — {stars} stars"
        cta_cn    = "有在用的朋友吗？踩过什么坑？评论区分享一下 👇"
        cta_en    = "Any devs using this already? What's your experience? Share below."
    else:
        source_cn = "今日热帖"
        source_en = "Trending today"
        cta_cn    = "你们怎么看？评论区聊聊 👇"
        cta_en    = "What's your take? Let me know below."

    copies = {}

    # ════════════════════════════════════════════════════
    # Version A · Suspense
    # ════════════════════════════════════════════════════
    a_cover = hooks["A"]["title"]
    copies["A"] = {

        "xiaohongshu": f"""{a_cover} 🤯
【首图建议：产品截图或 logo，叠加大字「{short[:12]} 今天为什么突然火了？」】

来源：{source_cn}

我认真研究了一下，发现大多数人关注的方向根本不对。

━━━━━━━━━━━━━━━━━━
它是什么
━━━━━━━━━━━━━━━━━━

{what_cn}

━━━━━━━━━━━━━━━━━━
为什么现在火
━━━━━━━━━━━━━━━━━━

{why_cn}

━━━━━━━━━━━━━━━━━━
我的判断
━━━━━━━━━━━━━━━━━━

{how_cn}

最后说一句：不是每个热门工具都值得你花时间了解。但这个是例外——不是因为它完美，而是因为它出现的时机很关键，理解它能帮你看清楚一个正在形成的趋势。

{cta_cn}

{tags_cn}""",

        "x": f"""{a_cover}

I spent time digging into why this is actually blowing up. The real reason isn't what most people think 🧵

━━━

1/ WHAT IT IS

{what_en}

━━━

2/ WHY IT'S TRENDING NOW

{why_en}

━━━

3/ MY TAKE

{how_en}

━━━

Source: {source_en}

{cta_en}""",

        "threads": f"""{a_cover}

认真研究了一下，说说我的看法。

{what_cn}

{why_cn}

{how_cn}

来源：{source_cn}

{cta_cn}""",

        "instagram": f"""{a_cover}

I went deep on why this is actually trending. Most people are focusing on the wrong thing 👇

━━━

{what_en}

━━━

{why_en}

━━━

{how_en}

━━━

Source: {source_en}

{cta_en}

{tags_en}""",
    }

    # ════════════════════════════════════════════════════
    # Version B · Number
    # ════════════════════════════════════════════════════
    b_cover = hooks["B"]["title"]
    copies["B"] = {

        "xiaohongshu": f"""{b_cover} 📊
【首图建议：数据卡片设计，「{pts:,}」这个数字要占满画面，副标题「为什么这个数字很重要」】

数据来源：{source_cn}

我不喜欢废话，直接说数字，再说数字背后是什么。

━━━━━━━━━━━━━━━━━━
它是什么
━━━━━━━━━━━━━━━━━━

{what_cn}

━━━━━━━━━━━━━━━━━━
这个数字说明什么
━━━━━━━━━━━━━━━━━━

{why_cn}

━━━━━━━━━━━━━━━━━━
你现在该怎么用这条信息
━━━━━━━━━━━━━━━━━━

{how_cn}

总结一句话：热度会消退，但信息差的价值是真实的。今天了解，比三个月后被动接受，至少早了一个身位。

{cta_cn}

{tags_cn.replace('#AI工具', '#AI工具测评').replace('#科技新品', '#数据说话')}""",

        "x": f"""{b_cover}

Numbers first, opinions second. Let me show you what the data actually says 📊

━━━

1/ WHAT IT IS

{what_en}

━━━

2/ WHY THESE NUMBERS MATTER

{why_en}

━━━

3/ WHAT TO DO WITH THIS

{how_en}

━━━

Source: {source_en} | Score: {score}/10

{cta_en}""",

        "threads": f"""{b_cover}

数字先行，然后说为什么。

{what_cn}

{why_cn}

{how_cn}

来源：{source_cn}，综合评分 {score}/10。

{cta_cn}""",

        "instagram": f"""{b_cover}

Numbers don't lie. Here's what they're actually telling us 📊

━━━

{what_en}

━━━

{why_en}

━━━

{how_en}

━━━

Score: {score}/10 | Source: {source_en}

{cta_en}

{tags_en.replace('#TechReview', '#DataDriven')}""",
    }

    # ════════════════════════════════════════════════════
    # Version C · Story
    # ════════════════════════════════════════════════════
    c_cover = hooks["C"]["title"]
    copies["C"] = {

        "xiaohongshu": f"""{c_cover} 😮‍💨
【首图建议：对比图「之前 vs 之后」，或者「我以为 vs 实际上」的视觉反差】

不是广告，说说我认真看完这件事之后的真实判断。

━━━━━━━━━━━━━━━━━━
先搞清楚它在做什么
━━━━━━━━━━━━━━━━━━

{what_cn}

━━━━━━━━━━━━━━━━━━
为什么它现在火，不是偶然
━━━━━━━━━━━━━━━━━━

{why_cn}

━━━━━━━━━━━━━━━━━━
这件事对你意味着什么
━━━━━━━━━━━━━━━━━━

{how_cn}

我最近发现一件事：每次我问自己「如果三个月后我才知道这个，我会后悔吗」，答案是「会」的内容，往往是最值得现在花时间了解的。这条的答案是——会。

{cta_cn}

{tags_cn.replace('#AI工具', '#真实测评').replace('#科技新品', '#工具分享')}""",

        "x": f"""{c_cover}

Not sponsored. This is just my honest read after spending time on it 🧵

━━━

1/ WHAT IT ACTUALLY IS (not what the marketing says)

{what_en}

━━━

2/ WHY I THINK THE TRACTION IS REAL

{why_en}

━━━

3/ WHAT I'D DO IF I WERE YOU

{how_en}

━━━

Source: {source_en}

{cta_en}""",

        "threads": f"""{c_cover}

不是广告。认真看完之后说说我的真实判断。

{what_cn}

{why_cn}

{how_cn}

来源：{source_cn}

{cta_cn}""",

        "instagram": f"""{c_cover}

No brand deal. Just spent time on this and here's my honest take 👇

━━━

{what_en}

━━━

{why_en}

━━━

{how_en}

━━━

Source: {source_en}

{cta_en}

{tags_en.replace('#TechReview', '#HonestReview')}""",
    }

    return copies


# ── Selection reason ───────────────────────────────────────────────────────────

def pick_reason(item):
    p     = item["platform"]
    pts   = item.get("score_raw", 0)
    title = item["title"]
    desc  = item.get("description") or ""
    stars = item.get("meta", {}).get("stars", "")

    if "producthunt" in p:
        freshness = "今日上线，新鲜度满分"
        audience  = f"{pts} 票，Product Hunt 用户即科技早期采用者，与你的目标受众高度重叠"
        diff      = "国内介绍这个产品的内容极少，信息差优势明显"
    elif "hackernews" in p:
        freshness = "24小时内热帖"
        audience  = f"{pts} 分、高评论量，技术社区强共鸣"
        diff      = "话题争议性强，切「观点型」内容差异化空间大"
    elif "github" in p:
        freshness = "今日 trending"
        audience  = f"{stars} Stars，开发者 + 效率工具用户"
        diff      = "大多数科普账号不看 GitHub，你先做就是信息差"
    else:
        freshness = "今日热门"
        audience  = "泛科技受众"
        diff      = "结合自身视角切入，差异化空间充足"

    return freshness, audience, diff


# ── Top-10 breakdown ───────────────────────────────────────────────────────────

def classify_content_type(item):
    """Classify the post into a content type with explanation."""
    title = item["title"].lower()
    desc  = (item.get("description") or "").lower()
    p     = item["platform"]

    if any(w in title for w in ["why", "为什么", "what happened", "secret", "nobody", "没人"]):
        return "🔴 悬念/好奇缺口型", "标题制造了信息缺口，读者必须点进去才能得到答案"
    if any(w in title for w in ["ask hn", "show hn", "tell hn"]):
        return "💬 社区讨论/观点型", "以问题或观点发起讨论，评论区本身就是内容"
    if any(w in title for w in ["rules", "principles", "lessons", "tips", "ways", "things"]):
        return "📋 列表/方法论型", "用经验提炼成规则，权威感强，适合收藏传播"
    if any(c.isdigit() for c in title[:10]):
        return "🔵 数字型", "标题开头有具体数字，量化结果，信任感强"
    if any(w in title for w in ["i built", "i made", "show hn", "quit", "founder", "mrr", "revenue"]):
        return "🟢 个人故事/创业型", "第一人称真实经历，共鸣感强，转发率高"
    if any(w in title for w in ["launch", "release", "announce", "new ", "introducing", "v2", "2.0"]):
        return "🟡 产品发布/新品型", "新产品上线，时效性强，抢先报道有信息差"
    if any(w in title for w in ["vs", "versus", "better than", "replace", "alternative"]):
        return "⚔️ 对比/竞争型", "直接对比两个选项，读者天然有站队欲望"
    if "producthunt" in p:
        return "🟡 产品发布/新品型", "Product Hunt 上线新品，时效性强，适合第一时间评测"
    if "github" in p:
        return "⚙️ 开源工具型", "开发者社区热门项目，适合做「工具介绍 + 使用场景」内容"
    return "📰 资讯/新闻型", "直接陈述事实，适合做信息整合和观点解读"


def analyze_hook_position(item):
    """Find where the hook is and explain it."""
    title = item["title"]
    p     = item["platform"]
    pts   = item.get("score_raw", 0)
    stars = item.get("meta", {}).get("stars", "")

    # Detect hook pattern
    if title[:1].isdigit() or title[:2].replace(" ", "").isdigit():
        hook_pos  = "开头数字"
        hook_text = title.split()[0] if title.split() else title[:5]
        hook_why  = f"「{hook_text}」放在最前，具体数字瞬间建立可信度"
    elif "?" in title or "？" in title:
        hook_pos  = "问句标题"
        hook_text = title
        hook_why  = "整个标题是一个问题，天然制造悬念，读者想知道答案"
    elif "——" in title or " – " in title or " - " in title:
        idx = max(title.find("——"), title.find(" – "), title.find(" - "))
        before = title[:idx].strip()
        after  = title[idx:].strip("—– ")
        hook_pos  = "破折号反转"
        hook_text = f"「{before[:20]}」→「{after[:20]}」"
        hook_why  = "前半句铺垫，破折号后是反转或结论，制造阅读惯性"
    elif any(w in title.lower() for w in ["why", "how", "what", "when"]):
        hook_pos  = "疑问词开头"
        hook_text = title[:30]
        hook_why  = "Why/How/What 开头天然触发好奇心，读者想知道答案"
    elif stars and int(str(stars).replace(",", "") or "0") > 0:
        hook_pos  = "平台背书数字"
        hook_text = f"{stars} Stars"
        hook_why  = f"「{stars} Stars」作为社会证明，热度本身就是钩子"
    elif pts > 0:
        hook_pos  = "热度背书"
        hook_text = f"{pts:,} 分/票"
        hook_why  = f"「{pts:,}」热度数字放在标题里，暗示「很多人觉得值得看」"
    else:
        hook_pos  = "标题即钩子"
        hook_text = title[:40]
        hook_why  = "标题本身描述了一个有争议或反常识的现象"

    return hook_pos, hook_text, hook_why


def make_reusable_template(item, content_type_label):
    """Generate a reusable title template from this post."""
    t = content_type_label
    title = item["title"]
    p     = item["platform"]
    pts   = item.get("score_raw", 0)
    stars = item.get("meta", {}).get("stars", "")

    if "悬念" in t or "好奇" in t:
        return "为什么 [工具/产品名] 突然爆火？我研究了评论区，答案很意外"
    elif "数字" in t:
        num = stars if stars else (str(pts) if pts else "X")
        return f"[数字] [单位]：[产品名] 实测值不值这个热度？"
    elif "列表" in t or "方法论" in t:
        return "[数字] 个 [领域] 原则，[权威来源]，[年份] 年了还在用"
    elif "个人故事" in t or "创业" in t:
        return "我 [做了某件事] 之后，发现自己之前白费了太多时间"
    elif "产品发布" in t or "新品" in t:
        return "Product Hunt 今日第一：[产品名]，[一句话描述]，能取代 [竞品] 吗？"
    elif "对比" in t or "竞争" in t:
        return "我用 [新工具] 替代了 [旧工具]，每周省了 [时间]"
    elif "社区讨论" in t or "观点" in t:
        return "[数字] 位工程师在讨论同一个问题，最高赞答案只有一句话"
    elif "开源" in t:
        return "GitHub [Stars] Stars 的 [工具名]：[一句话解决什么问题]"
    else:
        return "[平台] 热帖：[原标题核心词]，[你的独特视角]"


def format_top10_breakdown(scored):
    """Format the TOP 10 posts with full content analysis."""
    # Filter clean titles and sort by score
    clean = [x for x in scored if _is_cjk_or_latin(x["title"])]
    top10 = sorted(clean, key=lambda x: -x["total"])[:10]

    lines = [
        "",
        "=" * 60,
        "",
        "## 📖 TOP 10 热帖原文拆解",
        "（学习爆款结构，理解为什么它能火）",
        "",
    ]

    for i, item in enumerate(top10, 1):
        title    = item["title"]
        desc     = item.get("description") or "（暂无描述）"
        p        = item["platform"].upper()
        pts      = item.get("score_raw", 0)
        url      = item["url"]
        stars    = item.get("meta", {}).get("stars", "")
        comments = item.get("meta", {}).get("comments", 0)

        ctype, ctype_why    = classify_content_type(item)
        hook_pos, hook_text, hook_why = analyze_hook_position(item)
        template            = make_reusable_template(item, ctype)

        # Heat indicator
        if "hackernews" in item["platform"] and pts > 0:
            heat = f"HN {pts:,} 分 · {comments} 评论"
        elif "producthunt" in item["platform"] and pts > 0:
            heat = f"Product Hunt {pts:,} 票"
        elif "github" in item["platform"] and stars:
            heat = f"GitHub {stars} Stars"
        else:
            heat = f"热度 {pts:,}"

        lines += [
            f"### #{i}  [{p}]  {heat}",
            f"**原标题**：{title}",
            f"**链接**：{url}",
            f"**一句话描述**：{desc[:80]}",
            "",
            f"**内容类型**：{ctype}",
            f"└ {ctype_why}",
            "",
            f"**钩子在哪**：{hook_pos}",
            f"└ 钩子内容：{hook_text}",
            f"└ 为什么有效：{hook_why}",
            "",
            f"**可复用模板**：",
            f"└ `{template}`",
            "",
            "-" * 52,
            "",
        ]

    return "\n".join(lines)


# ── Format full report ─────────────────────────────────────────────────────────

def format_report(scored):
    best   = pick_best(scored)
    hooks  = make_hooks(best)
    copies = make_12_copies(best, hooks)
    freshness, audience, diff = pick_reason(best)
    short  = best["title"].split("/")[-1] if "/" in best["title"] else best["title"]
    pts    = best.get("score_raw", 0)
    stars  = best.get("meta", {}).get("stars", "")
    comments = best.get("meta", {}).get("comments", 0)
    topics = best.get("meta", {}).get("topics", [])

    lines = [
        f"# 今日内容创作简报  ·  {DATE}",
        f"共分析 {len(scored)} 条热帖  ·  为你选出今日最佳选题",
        "",
        "=" * 60,
        "",

        # ── SECTION 0: AB测试说明 ──────────────────────────────────────────────
        "## ❓ 什么是 ABC 测试？",
        "",
        "ABC 测试 = 用同一个选题，写三种不同的「开头钩子风格」，分别发到不同平台，",
        "48小时后对比数据，找出你的受众最吃哪一种。",
        "",
        "**测试的不是「内容好不好」，测试的是「你的受众对哪种开头方式更买账」。**",
        "",
        "三个版本的核心内容（分析、观点、结论）完全一样，",
        "唯一不同的是第一句话和整体语气：",
        "",
        "- **版本A · 悬念型**：制造好奇缺口，让人因为「想知道答案」而点进来",
        "  示例句式：「为什么 XX 突然爆火？答案和你想的不一样」",
        "",
        "- **版本B · 数字型**：用具体数字开头，让人因为「相信数据」而停下来",
        "  示例句式：「XX 票 / XX Stars：实测值不值这个热度？」",
        "",
        "- **版本C · 故事型**：用第一人称经历开头，让人因为「共鸣」而继续读",
        "  示例句式：「用了 XX 一周之后，我把它从工具箱里删掉了」",
        "",
        "48小时后，哪个版本的互动率（点赞+评论）÷ 播放 最高，",
        "那就是你的受众偏好的钩子风格，下周开始所有内容默认用这个风格。",
        "",
        "=" * 60,
        "",

        # ── SECTION 1: 原文完整展示 ───────────────────────────────────────────
        "## 📄 今日选题原文",
        "",
        f"**标题**：{best['title']}",
        f"**来源平台**：{best['platform'].upper()}",
        f"**链接**：{best['url']}",
    ]

    # Show all available metadata
    if pts:
        lines.append(f"**热度数据**：{pts:,} {'票' if 'producthunt' in best['platform'] else '分'}")
    if stars:
        lines.append(f"**Stars**：{stars}")
    if comments:
        lines.append(f"**评论数**：{comments:,} 条")
    if topics:
        lines.append(f"**话题标签**：{' / '.join(topics)}")

    desc_full = (best.get("description") or "").strip()
    lines += [
        "",
        f"**原文描述**：",
        desc_full if desc_full else "（该平台 API 未返回正文，请点击链接查看原文）",
        "",
        "**选这条的理由**：",
        f"- 新鲜度：{freshness}",
        f"- 受众匹配：{audience}",
        f"- 差异化空间：{diff}",
        "",
        "=" * 60,
        "",

        # ── SECTION 2: 钩子方向 ───────────────────────────────────────────────
        "## 🪝 三版钩子方向",
        "（同一内容，三种开头，测试你的受众偏好哪种）",
        "",
        "**版本A · 悬念型** — 钩子：制造好奇缺口，让人想知道答案",
        f"核心角度：{hooks['A']['angle']}",
        f"封面标题：{hooks['A']['title']}",
        "",
        "**版本B · 数字型** — 钩子：具体数字建立可信度，量化结果",
        f"核心角度：{hooks['B']['angle']}",
        f"封面标题：{hooks['B']['title']}",
        "",
        "**版本C · 故事/痛点型** — 钩子：第一人称经历，制造共鸣",
        f"核心角度：{hooks['C']['angle']}",
        f"封面标题：{hooks['C']['title']}",
        "",
        "=" * 60,
        "",

        # ── SECTION 3: 12条文案 ───────────────────────────────────────────────
        "## 📱 12条完整文案",
        "（每条都包含：封面钩子 + 完整正文分析 + CTA + 话题标签）",
        "",
    ]

    platform_labels = {
        "xiaohongshu": "小红书",
        "x":           "X (Twitter)",
        "threads":     "Threads",
        "instagram":   "INS",
    }
    platform_notes = {
        "xiaohongshu": "小红书：首行=封面标题，括号内=首图建议，正文约400字",
        "x":           "X：Thread格式，每段约140字，可拆成多条推文发布",
        "threads":     "Threads：中文，口语化，与小红书同结构但更简洁",
        "instagram":   "INS：英文，同X结构，适合海外受众",
    }

    for ver, label in [
        ("A", "版本A · 悬念型  →  建议首发小红书"),
        ("B", "版本B · 数字型  →  建议首发 X / INS"),
        ("C", "版本C · 故事型  →  建议首发 Threads / INS"),
    ]:
        lines += [f"### {label}", ""]
        for pl in ["xiaohongshu", "x", "threads", "instagram"]:
            lines += [
                f"**{platform_labels[pl]}**",
                f"*{platform_notes[pl]}*",
                "",
                copies[ver][pl],
                "",
                "- - -",
                "",
            ]
        lines += ["=" * 60, ""]

    # ── SECTION 4: 发布分配 + ABC看板 ────────────────────────────────────────
    lines += [
        "## 🚀 发布分配方案",
        "",
        "| 平台    | 发哪版        | 为什么这么分                         |",
        "|---------|--------------|--------------------------------------|",
        "| 小红书  | 版本A（悬念）| 封面悬念钩子 + 算法偏好强标题          |",
        "| X       | 版本B（数字）| 英文受众相信数据，thread格式天然适配   |",
        "| Threads | 版本C（故事）| 用户偏好真实感，第一人称共鸣效果最好   |",
        "| INS     | 版本C（故事）| 海外受众同样偏好真实体验分享           |",
        "",
        "⏰ 建议30分钟内完成四平台发布，热度集中期互动率最高",
        "",
        "=" * 60,
        "",
        "## 📊 ABC测试看板（48小时后填写，复制到 Google Sheet）",
        "",
        "**填写说明**：发布后1小时记录初始数据，48小时后填写完整数据",
        "**互动率公式**：(点赞 + 评论) ÷ 播放 × 100%",
        "**判断标准**：互动率最高的版本 = 你的受众最吃哪种钩子，下周主推这个风格",
        "",
        "版本    | 平台    | 封面标题（前30字）                  | 发布时间 | 1h互动 | 24h播放 | 24h点赞 | 24h评论 | 24h涨粉 | 互动率 | 结论",
        "--------|---------|-------------------------------------|----------|--------|---------|---------|---------|---------|--------|-----",
        f"A-悬念  | 小红书  | {hooks['A']['title'][:35]} | | | | | | | |",
        f"B-数字  | X       | {hooks['B']['title'][:35]} | | | | | | | |",
        f"C-故事  | Threads | {hooks['C']['title'][:35]} | | | | | | | |",
        f"C-故事  | INS     | {hooks['C']['title'][:35]} | | | | | | | |",
        "",
        f"*生成时间：{DATE}  |  trending-scraper v2.0*",
    ]

    # ── SECTION 5: TOP 10 原文拆解 ───────────────────────────────────────────
    lines.append(format_top10_breakdown(scored))

    return "\n".join(lines)


# ── 3-sentence breakdown ───────────────────────────────────────────────────────

def make_3line_breakdown(item):
    """
    Return 3 short sentences specific to this item's actual title/description:
    1. s1 — 是什么: explain what this product/post actually does in plain Chinese
    2. s2 — 为什么火: varies by platform + engagement numbers + actual content
    3. s3 — 内容角度: specific angle derived from THIS title/description, not generic
    """
    title    = item["title"]
    desc     = (item.get("description") or "").strip()
    p        = item["platform"]
    pts      = item.get("score_raw", 0)
    stars    = item.get("meta", {}).get("stars", "")
    comments = item.get("meta", {}).get("comments", 0)
    topics   = item.get("meta", {}).get("topics", [])
    lang     = item.get("meta", {}).get("language", "")
    channel  = item.get("meta", {}).get("channel", "")
    short    = title.split("/")[-1] if "/" in title else title
    tlower   = title.lower()
    desc_l   = desc.lower()

    # ── 是什么 (s1): explain what it actually does, not just repeat description ──
    if "producthunt" in p:
        # Derive what it does from title keywords + description
        core = desc[:80] if desc else title
        # Detect category for richer explanation
        if any(w in tlower or w in desc_l for w in ["xcode", "ios", "swift", "android", "mobile app"]):
            s1 = f"**是什么**：{short} 是一个移动端开发工具，让开发者可以不打开 Xcode 或 Android Studio 就完成 app 构建——{core[:60]}。"
        elif any(w in tlower or w in desc_l for w in ["presentation", "slide", "deck"]):
            s1 = f"**是什么**：{short} 是一个 AI 演示文稿工具，{core[:70]}——定位是让幻灯片看起来不像 AI 做的。"
        elif any(w in tlower or w in desc_l for w in ["memory", "import", "chatgpt", "switch", "migrate"]):
            s1 = f"**是什么**：{short} 解决的是 AI 工具之间的记忆迁移问题，{core[:70]}——让你从一个 AI 换到另一个时不用从零开始。"
        elif any(w in tlower or w in desc_l for w in ["napkin", "sketch", "ui", "figma", "design"]):
            s1 = f"**是什么**：{short} 把手绘草图直接转成可用的 UI 界面，{core[:60]}——省去从灵感到原型的中间步骤。"
        elif any(w in tlower or w in desc_l for w in ["voice", "speech", "audio", "podcast", "transcri"]):
            s1 = f"**是什么**：{short} 是一个语音/音频处理工具，{core[:70]}。"
        elif any(w in tlower or w in desc_l for w in ["database", "sql", "data", "analytics", "query"]):
            s1 = f"**是什么**：{short} 处理的是数据查询或分析场景，{core[:70]}。"
        elif any(w in tlower or w in desc_l for w in ["agent", "automat", "workflow", "pipeline"]):
            s1 = f"**是什么**：{short} 是一个 AI 自动化工具，{core[:70]}——让重复性任务交给 agent 来跑。"
        elif any(w in tlower or w in desc_l for w in ["code", "developer", "api", "sdk", "cli", "terminal"]):
            s1 = f"**是什么**：{short} 面向开发者，{core[:70]}。"
        elif any(w in tlower or w in desc_l for w in ["write", "edit", "content", "copy", "blog", "article"]):
            s1 = f"**是什么**：{short} 是一个写作/内容生产工具，{core[:70]}。"
        else:
            topic_str = topics[0] if topics else "生产力"
            s1 = f"**是什么**：{short} 今天在 Product Hunt 上线，核心是{core[:70]}，主打 {topic_str} 方向。"

    elif "hackernews" in p:
        # Explain what the HN discussion is actually about
        if "ask hn" in tlower:
            question = title.replace("Ask HN:", "").replace("Ask HN :", "").strip()
            s1 = f"**是什么**：HN 上有人问「{question}」，这是一个向社区征集经验的开放问题，评论区的真实回答才是内容核心。"
        elif "show hn" in tlower:
            project = title.replace("Show HN:", "").replace("Show HN :", "").strip()
            s1 = f"**是什么**：一位开发者在 HN 展示自己做的项目「{project}」，{desc[:70] if desc else '社区正在评测和讨论它'}。"
        elif any(w in tlower for w in ["rules", "principles", "lessons", "programming"]):
            s1 = f"**是什么**：这是一篇关于编程/工程原则的文章——「{title[:60]}」，讨论的是那些经过时间检验的开发理念。"
        elif any(w in tlower for w in ["why", "how", "what is", "explained"]):
            core = desc[:80] if desc else title
            s1 = f"**是什么**：HN 热帖，标题是「{title[:60]}」——这是一篇试图解释或质疑某个技术现象的文章，{core[:60]}。"
        else:
            core = desc[:80] if desc else "该帖内容引发了技术社区的广泛讨论"
            s1 = f"**是什么**：HN 今日热帖「{title[:60]}」——{core[:70]}。"

    elif "github" in p:
        lang_str = f"（{lang} 项目）" if lang else ""
        core = desc[:70] if desc else "开源工具"
        if any(w in tlower or w in desc_l for w in ["terminal", "cli", "shell", "command"]):
            s1 = f"**是什么**：{short}{lang_str} 是一个命令行/终端工具，{core[:70]}——面向开发者日常工作流。"
        elif any(w in tlower or w in desc_l for w in ["llm", "ai", "gpt", "model", "inference"]):
            s1 = f"**是什么**：{short}{lang_str} 是一个 AI/LLM 相关的开源项目，{core[:70]}。"
        elif any(w in tlower or w in desc_l for w in ["kubernetes", "docker", "deploy", "devops", "infra"]):
            s1 = f"**是什么**：{short}{lang_str} 解决的是部署和基础设施问题，{core[:70]}。"
        elif any(w in tlower or w in desc_l for w in ["security", "crypto", "auth", "vulnerab"]):
            s1 = f"**是什么**：{short}{lang_str} 是一个安全/加密方向的开源项目，{core[:70]}。"
        else:
            s1 = f"**是什么**：{short}{lang_str} 今日上 GitHub Trending，{core[:70]}。"

    elif "youtube" in p:
        ch_str = f"（{channel}）" if channel else ""
        if any(w in tlower for w in ["vs", "versus", "compared", "comparison"]):
            s1 = f"**是什么**：YouTube 视频{ch_str}「{title[:60]}」——做的是两个工具或方案的横向对比，有具体测试数据。"
        elif any(w in tlower for w in ["tutorial", "how to", "beginner", "learn", "course"]):
            s1 = f"**是什么**：YouTube 教程视频{ch_str}「{title[:60]}」——面向新手，手把手讲解某个工具或技能。"
        elif any(w in tlower for w in ["review", "tested", "honest", "worth"]):
            s1 = f"**是什么**：YouTube 测评视频{ch_str}「{title[:60]}」——创作者实测了某个产品并给出使用结论。"
        elif any(w in tlower for w in ["build", "i made", "i created", "project"]):
            s1 = f"**是什么**：YouTube 项目展示视频{ch_str}「{title[:60]}」——创作者展示自己用 AI 或开源工具做了什么。"
        else:
            s1 = f"**是什么**：YouTube 热门视频{ch_str}「{title[:60]}」。"
    else:
        core = desc[:80] if desc else title[:70]
        s1 = f"**是什么**：{core}。"

    # ── 为什么火 (s2): specific to engagement numbers + what it actually does ──
    if "producthunt" in p:
        if pts > 1000:
            # Derive a specific reason based on what the product does
            if any(w in tlower or w in desc_l for w in ["xcode", "ios", "swift", "mobile"]):
                reason = "AI 替代 Xcode 是开发者长期以来的痛点，一旦有产品敢做这个方向就会成为焦点"
            elif any(w in tlower or w in desc_l for w in ["presentation", "slide", "ai slop", "anti-ai"]):
                reason = "「反 AI 味」的定位戳中了用户审美疲劳——大家都厌倦了一看就知道是 AI 生成的幻灯片"
            elif any(w in tlower or w in desc_l for w in ["memory", "import", "chatgpt"]):
                reason = "记忆迁移是 AI 工具切换的最大障碍，解决这个问题的产品天然自带口碑传播动机"
            elif any(w in tlower or w in desc_l for w in ["napkin", "sketch", "ui", "figma"]):
                reason = "「草图变界面」这个工作流打通了产品经理和设计师之间最低效的环节，刚需明显"
            else:
                reason = f"今日 PH 票王，说明它精准踩中了科技早期用户的一个真实需求点"
            s2 = f"**为什么火**：今日票王 {pts:,} 票——{reason}。"
        elif pts >= 500:
            if any(w in tlower or w in desc_l for w in ["ai", "gpt", "llm", "agent", "claude", "gemini"]):
                category = "AI 工具"
            elif any(w in tlower or w in desc_l for w in ["developer", "code", "api", "sdk"]):
                category = "开发者工具"
            else:
                category = "生产力工具"
            s2 = f"**为什么火**：上线当天 {pts:,} 票，处于今日 PH 头部区间——说明 {category} 这个赛道需求依然旺盛，早期用户愿意主动背书。"
        else:
            # Niche product
            if topics:
                niche = topics[0]
            elif any(w in tlower or w in desc_l for w in ["creator", "content", "social"]):
                niche = "内容创作者"
            elif any(w in tlower or w in desc_l for w in ["startup", "saas", "founder"]):
                niche = "独立开发者/创业者"
            elif any(w in tlower or w in desc_l for w in ["student", "learn", "education"]):
                niche = "学习/教育"
            else:
                niche = "特定垂直场景"
            s2 = f"**为什么火**：{pts:,} 票，体量不大但精准——它服务的是 {niche} 这个细分群体，主流大工具不照顾的那部分需求。"

    elif "hackernews" in p:
        comment_str = f"{comments:,} 条评论" if comments else "活跃评论"
        if comments > 300:
            debate_hint = ""
            if any(w in tlower for w in ["rules", "principles", "programming"]):
                debate_hint = "，开发者们在争「这些原则在 AI 时代还成立吗」"
            elif any(w in tlower for w in ["ask hn"]):
                debate_hint = "，各路工程师都在分享自己的真实经验"
            elif any(w in tlower for w in ["why", "how"]):
                debate_hint = "，讨论的核心是「这个结论成立吗」——正反方都有高质量论据"
            s2 = f"**为什么火**：HN {pts:,} 分 · {comment_str}{debate_hint}——这个体量说明话题触动了真实争议，不是一边倒的共识。"
        elif pts > 200:
            s2 = f"**为什么火**：HN {pts:,} 分 · {comment_str}，技术圈主动投票意味着踩中了一个大家都有感受但没人说清楚的问题。"
        else:
            s2 = f"**为什么火**：HN {pts:,} 分，{comment_str}——在 HN 上能被发现本身就说明内容质量过关，HN 用户不捧场营销内容。"

    elif "github" in p:
        star_int = int(str(stars).replace(",", "") or "0") if stars else 0
        if star_int > 5000:
            if any(w in tlower or w in desc_l for w in ["terminal", "cli"]):
                reason = "命令行效率工具在开发者群体里传播速度最快，一个好用的 CLI 会被无数人写进 dotfiles 推荐"
            elif any(w in tlower or w in desc_l for w in ["llm", "ai", "agent"]):
                reason = "AI 基础设施类工具需求激增，能帮开发者少写胶水代码的项目天然有传播动力"
            elif lang in ["rust", "zig"]:
                reason = f"{lang} 社区对高质量项目的传播极其高效，一个好项目两天内会被所有 {lang} 开发者知道"
            else:
                reason = "解决了一个开发者日常反复遇到的具体问题，口碑传播靠的是「真有用」而不是营销"
            s2 = f"**为什么火**：{stars} Stars 上 GitHub Trending——{reason}。"
        elif star_int > 1000:
            s2 = f"**为什么火**：{stars} Stars 进入 Trending，开发者 Star 不是点赞——Star = 「我认为这工具以后用得上」，{stars} 个这样的判断说明它解决的问题是真实的。"
        else:
            s2 = f"**为什么火**：刚上 GitHub Trending，{stars} Stars，正处于传播最快的窗口期——现在做内容等于抢在科技媒体报道之前。"

    elif "youtube" in p:
        if any(w in tlower for w in ["vs", "compared", "comparison"]):
            s2 = "**为什么火**：横向对比类视频自带流量——用户在选工具的时候会主动搜「A vs B」，搜索驱动流量，不靠算法推送。"
        elif any(w in tlower for w in ["tutorial", "how to", "beginner"]):
            s2 = "**为什么火**：教程类视频有长尾搜索价值，新手学某个工具第一反应就是去 YouTube 搜教程，关键词流量稳定持续。"
        elif channel:
            s2 = f"**为什么火**：来自 {channel} 频道，该频道在这个方向有固定受众，发什么都会被这批人第一时间传播。"
        else:
            s2 = "**为什么火**：YouTube 搜索前排说明这个关键词有真实搜索量，内容需求明确，观众带着问题来找答案。"
    else:
        s2 = "**为什么火**：多平台同期出现，话题时机成熟，受众已有认知基础，不需要大量铺垫。"

    # ── 内容角度 (s3): SPECIFIC to this product/post, not generic category ─────
    # First check title-level specifics, then fall back to thematic patterns

    if any(w in tlower for w in ["xcode", "replace xcode", "replaces xcode"]):
        s3 = "**内容角度**：「开发工具颠覆」——AI 是否真的能取代 Xcode？做一个横向对比：哪些流程被替代了，哪些还做不到，给开发者一个诚实的评估。"
    elif any(w in tlower or w in desc_l for w in ["ai slop", "without the ai", "anti-ai", "no ai feel"]):
        s3 = "**内容角度**：「反 AI 味」定位很聪明——为什么用户开始讨厌 AI 感？这个产品的反向思路值得拆解，写一篇「当 AI 工具开始假装自己不是 AI」。"
    elif any(w in tlower or w in desc_l for w in ["import memory", "memory import", "migrate memory", "chatgpt memory"]):
        s3 = "**内容角度**：「迁移门槛」——从 ChatGPT 切换到 Claude 最大的障碍是记忆，这个产品解决的恰好是这个，写「AI 工具换厂的代价」。"
    elif any(w in tlower or w in desc_l for w in ["napkin", "sketch to ui", "drawing to ui", "napkin sketch"]):
        s3 = "**内容角度**：「草图变代码」——Google 出手了，Figma 和 Cursor 们怎么办？做一个「设计工具战局」分析，站在普通用户视角讲清楚谁受益。"
    elif "rob pike" in tlower or ("rules" in tlower and "programming" in tlower and ("1989" in title or "1980" in title)):
        s3 = "**内容角度**：「1989 年的编程原则，2026 年还成立吗？」——拿每条原则对照 AI 时代逐条验证，哪些变了哪些没变，这种「时间检验」角度比直接翻译有价值得多。"
    elif any(w in tlower for w in ["stitch", "napkin"]) and any(w in tlower or w in desc_l for w in ["google", "figma"]):
        s3 = "**内容角度**：「草图变代码」——Google 出手了，Figma 和 Cursor 们怎么办？做一个竞品格局分析，用户视角讲清楚谁受益谁被威胁。"
    elif any(w in tlower for w in ["ask hn"]):
        question_core = title.replace("Ask HN:", "").replace("Ask HN :", "").strip()[:40]
        s3 = f"**内容角度**：「评论区整理」——「{question_core}」这个问题的高赞回答质量极高，整理出 5 个最有代表性的真实工程师答案，比你自己分析有说服力。"
    elif any(w in tlower for w in ["show hn"]):
        project_core = title.replace("Show HN:", "").replace("Show HN :", "").strip()[:40]
        s3 = f"**内容角度**：「独立开发者实战」——「{project_core}」背后的开发者故事，从想法到上线，用 Show HN 评论区反应来验证市场，给做副业的读者看。"
    elif any(w in tlower for w in ["rules", "principles", "lessons"]) and "programming" in tlower:
        s3 = "**内容角度**：「经典原则时间检验」——把这些编程原则放到 AI 辅助编程的今天，逐条验证是否还成立，形成「2026 版更新」，比纯翻译有独立判断。"
    elif any(w in tlower or w in desc_l for w in ["replace", "alternative", "switch", "migrate"]) and not "xcode" in tlower:
        obj = ""
        for pair in [("chatgpt", "ChatGPT"), ("notion", "Notion"), ("slack", "Slack"), ("figma", "Figma"), ("excel", "Excel")]:
            if pair[0] in tlower or pair[0] in desc_l:
                obj = pair[1]
                break
        if obj:
            s3 = f"**内容角度**：「迁移成本」——从 {obj} 切换最大的障碍是什么？这个产品解决的恰好是这个，写「换工具最怕丢什么」，痛点驱动分享。"
        else:
            s3 = f"**内容角度**：「迁移成本」——用户卡在的不是新工具好不好，而是能不能带走历史数据和习惯，这个角度比功能对比更有共鸣。"
    elif any(w in tlower or w in desc_l for w in ["v2", "2.0", "rewrite", "rebuilt", "redesign"]):
        s3 = f"**内容角度**：「版本进化拆解」——{short[:30]} 的这次大更新改了什么、为什么改、用户真的需要吗？做一个「升级值不值」的诚实评估。"
    elif any(w in tlower or w in desc_l for w in ["open source", "free", "self-host", "selfhost"]):
        s3 = f"**内容角度**：「开源替代」——{short[:30]} 能替代掉哪个付费 SaaS？列出具体对比，给愿意自己部署的用户一个清单，这类内容收藏率极高。"
    elif "github" in p and lang in ["rust", "zig", "go"]:
        s3 = f"**内容角度**：「{lang} 为什么重要」——用 {short[:25]} 作为引子，解释 {lang} 在当下工具链里解决的真实问题，给非开发者也能看懂的科普角度。"
    elif "youtube" in p and any(w in tlower for w in ["vs", "comparison", "compared"]):
        s3 = f"**内容角度**：「选边站」——把这个对比视频的核心结论提炼出来，加上你自己的一票「我选谁」，观众天然有参与感，评论率高。"
    elif "youtube" in p and any(w in tlower for w in ["tutorial", "how to"]):
        s3 = f"**内容角度**：「更快版」——把这个教程的核心步骤提炼成「5 分钟版」，给没时间看完整视频的人，文字版教程比视频更容易被收藏分享。"
    elif "producthunt" in p and any(w in tlower or w in desc_l for w in ["ai", "gpt", "llm", "claude", "gemini"]):
        topic_hint = ""
        if any(w in tlower or w in desc_l for w in ["write", "content", "copy", "blog"]):
            topic_hint = "写作/内容生产"
        elif any(w in tlower or w in desc_l for w in ["code", "developer", "api"]):
            topic_hint = "开发者效率"
        elif any(w in tlower or w in desc_l for w in ["design", "ui", "figma"]):
            topic_hint = "设计工作流"
        elif any(w in tlower or w in desc_l for w in ["sales", "marketing", "crm"]):
            topic_hint = "销售/营销"
        else:
            topic_hint = "AI 工具"
        s3 = f"**内容角度**：「{topic_hint} 新选手」——{short[:25]} 进入这个赛道，和已有工具比多了什么、少了什么，给这个场景的实际用户一个「要不要试试」的判断依据。"
    elif "producthunt" in p:
        s3 = f"**内容角度**：「产品逻辑拆解」——{short[:25]} 为什么选这个切入点？它在解决的问题有哪些现有工具没做好？从产品思路角度分析，比功能介绍更有深度。"
    else:
        s3 = "**内容角度**：「信息整合」——去原帖评论区找最高赞回复，整理成「我帮你看完了」的结构，门槛低、可信度高，适合快速出内容。"

    return s1, s2, s3


# ── Scores report ──────────────────────────────────────────────────────────────

def format_scores_report(scored):
    """
    5-section report:
      1. PH TOP 10
      2. HN TOP 10 + developer-focus analysis block
      3. GitHub TOP 10
      4. YouTube ALL + content-structure template block
      5. Hook formula library (extracted from today's actual titles)
    Followed by the full ranked table.
    """
    clean = [x for x in scored if _is_cjk_or_latin(x["title"])]

    # Split by platform
    ph_items  = sorted([x for x in clean if "producthunt" in x["platform"]],
                       key=lambda x: -x["score_raw"])[:10]
    hn_items  = sorted([x for x in clean if "hackernews" in x["platform"]],
                       key=lambda x: -x["score_raw"])[:10]
    gh_items  = sorted([x for x in clean if "github" in x["platform"]],
                       key=lambda x: -x["score_raw"])[:10]
    yt_items  = [x for x in clean if "youtube" in x["platform"]]  # keep scraped order, show all

    lines = [
        f"## 今日热帖评分表 · {DATE}",
        f"共分析 {len(scored)} 条",
        "",
        "---",
        "",
    ]

    # ══════════════════════════════════════════════════════════════════════════
    # SECTION 1 — Product Hunt TOP 10
    # ══════════════════════════════════════════════════════════════════════════
    lines += [
        "## 🛍️ Product Hunt TOP 10（今日新品）",
        "",
    ]
    for i, item in enumerate(ph_items, 1):
        title = item["title"]
        pts   = item.get("score_raw", 0)
        score = item["total"]
        url   = item["url"]
        dims  = item.get("dims", {})
        dim_str = "  ".join(f"{k} {v}" for k, v in dims.items()) if dims else ""
        s1, s2, s3 = make_3line_breakdown(item)
        lines += [
            f"### #{i}  {title}",
            f"票数：{pts:,}票  ·  综合评分 {score}/10  ·  {url}",
            f"评分明细：{dim_str}",
            "",
            s1,
            s2,
            s3,
            "",
            "─" * 52,
            "",
        ]

    lines += ["---", ""]

    # ══════════════════════════════════════════════════════════════════════════
    # SECTION 2 — Hacker News TOP 10
    # ══════════════════════════════════════════════════════════════════════════
    lines += [
        "## 💬 Hacker News TOP 10（开发者社区）",
        "",
    ]
    for i, item in enumerate(hn_items, 1):
        title    = item["title"]
        pts      = item.get("score_raw", 0)
        comments = item.get("meta", {}).get("comments", 0)
        score    = item["total"]
        url      = item["url"]
        dims     = item.get("dims", {})
        dim_str  = "  ".join(f"{k} {v}" for k, v in dims.items()) if dims else ""
        s1, s2, s3 = make_3line_breakdown(item)
        lines += [
            f"### #{i}  {title}",
            f"分数：{pts:,}  ·  评论：{comments}条  ·  综合评分 {score}/10  ·  {url}",
            f"评分明细：{dim_str}",
            "",
            s1,
            s2,
            s3,
            "",
            "─" * 52,
            "",
        ]

    # HN analysis block — summarise developer focus from the 10 items
    # Derive 3 directions by scanning the actual HN titles
    hn_titles_lower = [x["title"].lower() for x in hn_items]

    dir_counts = {
        "AI / LLM 应用与反思": sum(1 for t in hn_titles_lower if any(w in t for w in ["ai", "llm", "gpt", "model", "agent", "claude", "gemini"])),
        "工程实践与开发工具":   sum(1 for t in hn_titles_lower if any(w in t for w in ["programming", "code", "developer", "tool", "compiler", "terminal", "cli", "sdk", "api"])),
        "创业 / 独立开发":      sum(1 for t in hn_titles_lower if any(w in t for w in ["startup", "saas", "mrr", "founder", "indie", "side project", "quit", "revenue", "show hn"])),
        "安全 / 隐私":          sum(1 for t in hn_titles_lower if any(w in t for w in ["security", "privacy", "crypto", "vulnerab", "breach", "hack"])),
        "系统 / 基础设施":      sum(1 for t in hn_titles_lower if any(w in t for w in ["kernel", "linux", "distributed", "database", "kubernetes", "docker", "rust", "zig"])),
        "行业趋势 / 观点":      sum(1 for t in hn_titles_lower if any(w in t for w in ["why", "how", "future", "dead", "decline", "rise", "era", "age"])),
    }
    top3_dirs = sorted(dir_counts.items(), key=lambda x: -x[1])[:3]
    # Filter to dirs with at least 1 match; if all zero just take top 3 names
    top3_dirs = [d for d in top3_dirs if d[1] > 0] or list(dir_counts.items())[:3]

    # Identify items with popular-science (普通人能看懂) angle
    accessible_items = []
    for item in hn_items:
        t = item["title"].lower()
        # Ask HN / Show HN / opinion / story type = accessible
        if any(w in t for w in ["ask hn", "show hn", "why", "how to", "what is",
                                  "rules", "principles", "lessons", "tips",
                                  "quit", "founder", "mrr", "indie"]):
            accessible_items.append(item["title"])

    # Pick 2-3 for content suggestions
    content_picks = hn_items[:3]

    lines += [
        "### 🔍 HN本周开发者关注什么",
        "",
        "**从这10条里总结开发者最关注的3个方向：**",
        "",
    ]
    for rank, (direction, count) in enumerate(top3_dirs, 1):
        lines.append(f"{rank}. **{direction}**（本次 {count} 条相关）")
    lines += [""]

    if accessible_items:
        lines += [
            "**哪些话题有普通人能看懂的科普角度：**",
            "",
        ]
        for t in accessible_items[:5]:
            lines.append(f"- {t}")
        lines += [""]

    lines += [
        "**内容选题建议（2-3条转化）：**",
        "",
    ]
    for pick in content_picks:
        t      = pick["title"]
        tlower = t.lower()
        pts    = pick.get("score_raw", 0)
        if "ask hn" in tlower:
            q = t.replace("Ask HN:", "").replace("Ask HN :", "").strip()[:50]
            hook = f"「{q}」——工程师在问，普通人也想知道，整理高赞答案做一期"
        elif "show hn" in tlower:
            proj = t.replace("Show HN:", "").replace("Show HN :", "").strip()[:50]
            hook = f"「{proj}」——独立开发者真实上线案例，读者想看「怎么做到的」"
        elif any(w in tlower for w in ["rules", "principles"]):
            hook = f"「{t[:50]}」——把经典原则放到今天验证，「还成立吗」是最强钩子"
        elif any(w in tlower for w in ["why", "how"]):
            hook = f"「{t[:50]}」——把这个技术问题翻译成非技术人能看懂的语言"
        else:
            hook = f"「{t[:50]}」——提炼高赞评论，做「我帮你看完了」结构"
        lines.append(f"- {hook}")
    lines += ["", "---", ""]

    # ══════════════════════════════════════════════════════════════════════════
    # SECTION 3 — GitHub TOP 10
    # ══════════════════════════════════════════════════════════════════════════
    lines += [
        "## ⚙️ GitHub Trending TOP 10（开源项目）",
        "",
    ]
    for i, item in enumerate(gh_items, 1):
        title = item["title"]
        stars = item.get("meta", {}).get("stars", "")
        lang  = item.get("meta", {}).get("language", "—")
        score = item["total"]
        url   = item["url"]
        dims  = item.get("dims", {})
        dim_str = "  ".join(f"{k} {v}" for k, v in dims.items()) if dims else ""
        s1, s2, s3 = make_3line_breakdown(item)
        lines += [
            f"### #{i}  {title}",
            f"Stars：{stars}  ·  语言：{lang}  ·  综合评分 {score}/10  ·  {url}",
            f"评分明细：{dim_str}",
            "",
            s1,
            s2,
            s3,
            "",
            "─" * 52,
            "",
        ]

    lines += ["---", ""]

    # ══════════════════════════════════════════════════════════════════════════
    # SECTION 4 — YouTube (all items, scraped order)
    # ══════════════════════════════════════════════════════════════════════════
    lines += [
        "## 🎬 YouTube TOP 10（热门视频）",
        "",
    ]
    for i, item in enumerate(yt_items, 1):
        title   = item["title"]
        channel = item.get("meta", {}).get("channel", "")
        url     = item["url"]
        s1, s2, s3 = make_3line_breakdown(item)
        ch_str = f"  ·  频道：{channel}" if channel else ""
        lines += [
            f"### #{i}  {title}",
            f"来源：YouTube{ch_str}  ·  {url}",
            "",
            s1,
            s2,
            s3,
            "",
            "─" * 52,
            "",
        ]

    # YouTube content structure templates
    lines += [
        "### 📐 YouTube内容结构模板",
        "",
        "**1. 工具测评模板**",
        "- 00:00–00:30  开头钩子：提出用户最想知道的一个问题（「它真的能取代XX吗？」）",
        "- 00:30–02:00  产品是什么：30秒背景 + 核心功能截图演示",
        "- 02:00–05:00  实测核心场景：选1-2个最典型用例，录屏操作，说出感受",
        "- 05:00–07:00  与竞品对比：只比最关键的1个维度，不要列表格",
        "- 07:00–08:00  适合谁 / 不适合谁：帮观众做决策，越具体越好",
        "- 08:00–08:30  结论 + CTA：一句话判断 + 引导评论「你们用的是哪个？」",
        "- **钩子设计**：封面用「VS」或数字，标题用疑问句，缩略图展示产品界面截图",
        "",
        "**2. 行业深度模板**",
        "- 00:00–00:45  开头钩子：一个让人意外的数据或现象（「过去6个月，XX发生了……」）",
        "- 00:45–03:00  背景：这个行业/领域发生了什么，为什么现在值得讲",
        "- 03:00–06:00  核心分析：3个关键变化或趋势，每个配具体案例",
        "- 06:00–08:00  影响：对普通用户/开发者/创业者意味着什么",
        "- 08:00–09:00  预判：接下来会发生什么，给观众一个前瞻",
        "- 09:00–09:30  结论 + 讨论引导：「你觉得这个方向能走多远？」",
        "- **钩子设计**：标题用「正在发生……」或「为什么……」，封面用对比图或时间线",
        "",
        "**3. 新手教程模板**",
        "- 00:00–00:30  开头钩子：「如果你想学XX，这是最快的路径」",
        "- 00:30–01:30  为什么学这个：具体说它能解决什么问题，不要讲大道理",
        "- 01:30–06:00  核心教程：3-5个步骤，每步都有操作演示，语速慢一点",
        "- 06:00–07:30  常见错误：说出新手最容易踩的1-2个坑",
        "- 07:30–08:00  下一步：告诉观众学完这个之后该做什么",
        "- **钩子设计**：标题用「X分钟学会」或「零基础」，封面用「Before/After」",
        "",
        "---",
        "",
    ]

    # ══════════════════════════════════════════════════════════════════════════
    # SECTION 5 — Hook formula library from today's actual titles
    # ══════════════════════════════════════════════════════════════════════════
    lines += [
        "## 📐 钩子公式库（从今日热帖归纳）",
        "",
    ]

    all_titles = [x["title"] for x in clean]

    # ── 悬念型: titles with "why", "?", "secret", "nobody", "quietly" etc.
    suspense_examples = [t for t in all_titles if
                         any(w in t.lower() for w in ["why", "secret", "nobody", "quietly",
                                                       "surprising", "unexpected", "you don't", "didn't know"]) or
                         "?" in t or "？" in t][:2]
    if len(suspense_examples) < 2:
        # Fill from any title containing a question-like structure
        suspense_examples += [t for t in all_titles if t not in suspense_examples
                               and any(w in t.lower() for w in ["how", "what"])][:2 - len(suspense_examples)]

    # ── 数字型: titles starting with or containing numbers
    import re
    number_examples = [t for t in all_titles if re.search(r'\b\d[\d,]*\b', t)][:2]
    # Also catch stars/votes numbers from metadata
    if len(number_examples) < 2:
        for x in clean:
            if len(number_examples) >= 2:
                break
            stars = x.get("meta", {}).get("stars", "")
            pts   = x.get("score_raw", 0)
            if (stars or pts) and x["title"] not in number_examples:
                number_examples.append(x["title"])

    # ── 对比型: "vs", "versus", "vs.", "alternative", "better than", "replace"
    contrast_examples = [t for t in all_titles if
                         any(w in t.lower() for w in ["vs", "versus", "better than",
                                                       "replace", "alternative", "compared"])][:2]

    # ── 痛点型: titles with pain-point language
    pain_examples = [t for t in all_titles if
                     any(w in t.lower() for w in ["quit", "tired", "sick of", "hate", "annoying",
                                                    "without", "no more", "stop", "never again",
                                                    "slop", "migration", "problem", "issue"])][:2]

    # ── 权威背书型: names, numbers of stars/votes, "google", "openai", company names
    authority_examples = [t for t in all_titles if
                          any(w in t.lower() for w in ["google", "openai", "anthropic", "microsoft",
                                                        "github", "apple", "meta", "amazon",
                                                        "show hn", "ask hn"]) or
                          re.search(r'\b\d{3,}[\d,]* stars?\b', t.lower()) or
                          re.search(r'\b\d{3,}[\d,]* votes?\b', t.lower())][:2]

    def fmt_examples(examples, fallback="（今日无典型例子）"):
        if not examples:
            return [f"  - {fallback}"]
        return [f"  - 「{e[:70]}」" for e in examples[:2]]

    lines += [
        "**悬念型**",
        "  适用场景：让读者因为「想知道答案」而点进来",
    ] + fmt_examples(suspense_examples) + [
        "  模板：「为什么 [产品/现象] 突然爆火？我研究了评论区，答案很意外」",
        "",
        "**数字型**",
        "  适用场景：用具体数字建立可信度，量化结果",
    ] + fmt_examples(number_examples) + [
        "  模板：「[数字] [单位]：[产品名] 实测值不值这个热度？」",
        "",
        "**对比型**",
        "  适用场景：让读者天然产生站队欲望，评论率高",
    ] + fmt_examples(contrast_examples) + [
        "  模板：「我用 [新工具] 替代了 [旧工具]，每周省了 [时间]——结论在最后」",
        "",
        "**痛点型**",
        "  适用场景：精准戳中特定人群的已有痛苦，转发动力强",
    ] + fmt_examples(pain_examples) + [
        "  模板：「用 [工具] 最让人抓狂的一件事，终于有人解决了」",
        "",
        "**权威背书型**",
        "  适用场景：借助品牌/数据/社区背书快速建立信任",
    ] + fmt_examples(authority_examples) + [
        "  模板：「[Google/HN/GitHub 等权威来源] 今天推荐了这个——[简短结论]」",
        "",
        "**最有效类型结论**：在科技内容里，**数字型 + 悬念型组合**效果最强——"
        "开头给数字建立可信度，结尾留一个悬念让读者想往下看；"
        "纯悬念型在标题上吸引点击，但正文需要真实数据支撑，否则读者会觉得被骗。",
        "",
        "---",
        "",
    ]

    # ── Full ranking table (kept from original) ────────────────────────────────
    ranked = sorted(clean, key=lambda x: -x["total"])
    lines += [
        "### 📋 全部条目排名",
        "",
        f"{'#':<3}  {'综合':<5}  {'新鲜':>4}  {'受众':>4}  {'差异':>4}  {'难度':>4}  {'热度':<10}  {'平台':<16}  标题",
        "─" * 100,
    ]

    for i, item in enumerate(ranked, 1):
        title  = item["title"][:45]
        p      = item["platform"][:16]
        score  = item["total"]
        dims   = item.get("dims", {})
        pts    = item.get("score_raw", 0)
        stars  = item.get("meta", {}).get("stars", "")
        heat   = str(stars) if stars else (str(pts) if pts else "—")
        d      = dims if dims else {}
        lines.append(
            f"#{i:<2}  {score:<5}  "
            f"{d.get('新鲜度', '-'):>4}  "
            f"{d.get('受众规模', '-'):>4}  "
            f"{d.get('差异化', '-'):>4}  "
            f"{d.get('制作难度', '-'):>4}  "
            f"{heat:<10}  {p:<16}  {title}"
        )

    lines += ["", f"*生成时间：{DATE}  |  trending-scraper*"]
    return "\n".join(lines)


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input",  default="output/today.json")
    parser.add_argument("--format", choices=["briefing", "json", "scores"], default="briefing")
    parser.add_argument("--output", default=None)
    args = parser.parse_args()

    with open(args.input) as f:
        data = json.load(f)

    scored = []
    for item in data["items"]:
        total, dims = score_item(item)
        scored.append({
            **item,
            "total": total,
            "dims": dims,
        })

    if args.format == "briefing":
        out = format_report(scored)
    elif args.format == "scores":
        out = format_scores_report(scored)
    else:
        out = json.dumps(scored, ensure_ascii=False, indent=2)

    if args.output:
        Path(args.output).write_text(out, encoding="utf-8")
        print(f"✓ Report → {args.output}")
    else:
        print(out)


if __name__ == "__main__":
    main()
