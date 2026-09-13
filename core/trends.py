"""Trend discovery: free, keyless sources for what's hot per niche.

Sources (all $0, no API keys):
- Reddit hot listings for niche-mapped subreddits (public JSON)
- Hacker News front page (Algolia API) for the tech niche

Best-effort by design: networks fail and Reddit rate-limits — every fetch is
wrapped so discovery degrades to "no live trends" instead of crashing.
"""

import json
import urllib.parse
import urllib.request

USER_AGENT = "JARVIS-Assistant/1.0 (personal learning project)"
TIMEOUT = 12

SUBREDDITS = {
    "roblox": ["roblox", "RobloxDevelopers"],
    "minecraft": ["Minecraft", "minecraftsuggestions"],
    "gaming": ["gaming", "Games"],
    "fitness": ["Fitness", "GetMotivated"],
    "horror": ["horror", "nosleep"],
    "tech": ["technology", "artificial"],
    "education": ["explainlikeimfive", "todayilearned"],
    "motivation": ["GetMotivated", "selfimprovement"],
    "generic": ["videos", "Documentaries"],
}

HN_API = "https://hn.algolia.com/api/v1/search?tags=front_page"


def _fetch_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        return json.loads(resp.read().decode("utf-8", "replace"))


def parse_reddit_listing(payload, source="reddit"):
    """Pure parser: Reddit listing JSON -> [{title, url, score, comments, source}]."""
    topics = []
    try:
        children = payload["data"]["children"]
    except (KeyError, TypeError, AttributeError):
        return []
    for child in children:
        data = child.get("data", {}) if isinstance(child, dict) else {}
        title = (data.get("title") or "").strip()
        if not title or data.get("stickied"):
            continue
        permalink = data.get("permalink") or ""
        topics.append({
            "title": title,
            "url": f"https://www.reddit.com{permalink}" if permalink else "",
            "score": data.get("score", 0) or 0,
            "comments": data.get("num_comments", 0) or 0,
            "source": f"{source}/r/{data.get('subreddit', '?')}",
        })
    return topics


def fetch_subreddit(subreddit, limit=8):
    url = f"https://www.reddit.com/r/{urllib.parse.quote(subreddit)}/hot.json?limit={limit}"
    try:
        payload = _fetch_json(url)
    except Exception as e:
        print(f"[trends] r/{subreddit} unavailable ({e})")
        return []
    return parse_reddit_listing(payload)[:limit]


def parse_hn(payload):
    """Pure parser: Algolia HN payload -> topic list."""
    topics = []
    hits = payload.get("hits", []) if isinstance(payload, dict) else []
    for hit in hits:
        title = (hit.get("title") or "").strip()
        if not title:
            continue
        topics.append({
            "title": title,
            "url": hit.get("url") or f"https://news.ycombinator.com/item?id={hit.get('objectID')}",
            "score": hit.get("points", 0) or 0,
            "comments": hit.get("num_comments", 0) or 0,
            "source": "hackernews",
        })
    return topics


def fetch_hackernews(limit=8):
    try:
        return parse_hn(_fetch_json(HN_API))[:limit]
    except Exception as e:
        print(f"[trends] Hacker News unavailable ({e})")
        return []


def discover_trends(niche_key, per_source=5):
    """Ranked live topics for a niche. Never raises for network issues."""
    topics = []
    for sub in SUBREDDITS.get(niche_key, SUBREDDITS["generic"]):
        topics.extend(fetch_subreddit(sub, limit=per_source))
        if len(topics) >= per_source * 2:
            break
    if niche_key == "tech":
        topics.extend(fetch_hackernews(limit=per_source))
    # Rank by engagement, dedupe by title.
    seen, ranked = set(), []
    for t in sorted(topics,
                    key=lambda t: (t["score"] or 0) + 2 * (t["comments"] or 0),
                    reverse=True):
        key = t["title"].lower()
        if key not in seen:
            seen.add(key)
            ranked.append(t)
    return ranked
