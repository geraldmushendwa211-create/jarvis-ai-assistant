"""Research agent: free, keyless fact gathering.

- Wikipedia search + article summaries (stable public API)
- DuckDuckGo instant answers (free, no key — sparse but sometimes perfect)

research_topic() returns {"summary", "facts", "sources", "note"} and never
raises for network issues — worst case is an empty brief with a note saying
the plan is AI-only. The parse_* helpers are pure (unit-tested, no network).
"""

import json
import re
import urllib.parse
import urllib.request

USER_AGENT = "JARVIS-Assistant/1.0 (personal learning project)"
TIMEOUT = 12

WIKI_SEARCH = ("https://en.wikipedia.org/w/api.php?action=query&list=search"
               "&srlimit=5&format=json&srsearch={q}")
WIKI_SUMMARY = "https://en.wikipedia.org/api/rest_v1/page/summary/{title}"
DDG_API = "https://api.duckduckgo.com/?format=json&no_html=1&skip_disambig=1&q={q}"


def _fetch_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        return json.loads(resp.read().decode("utf-8", "replace"))


def parse_wiki_search(payload):
    """Search payload -> [article titles]."""
    if not isinstance(payload, dict):
        return []
    titles = []
    for item in payload.get("query", {}).get("search", []):
        title = item.get("title", "")
        if title:
            titles.append(title)
    return titles


def parse_wiki_summary(payload):
    """Article-summary payload -> {title, summary, url} or None."""
    if not isinstance(payload, dict) or payload.get("type") == "disambiguation":
        return None
    extract = (payload.get("extract") or "").strip()
    if not extract:
        return None
    desktop = (payload.get("content_urls", {}).get("desktop", {}) or {})
    return {
        "title": payload.get("title", ""),
        "summary": extract,
        "url": desktop.get("page", ""),
    }


def parse_ddg(payload):
    """DuckDuckGo payload -> {title, summary, url} or None."""
    if not isinstance(payload, dict):
        return None
    abstract = (payload.get("AbstractText") or "").strip()
    if not abstract:
        return None
    return {
        "title": payload.get("Heading") or "DuckDuckGo",
        "summary": abstract,
        "url": payload.get("AbstractURL") or "",
    }


def _sentences(text, limit=6):
    parts = re.split(r"(?<=[.!?])\s+", (text or "").strip())
    return [p.strip() for p in parts if len(p.strip()) > 40][:limit]


def research_topic(topic, max_sources=3):
    brief = {"topic": topic, "summary": "", "facts": [], "sources": [], "note": ""}
    # 1) Wikipedia: search, then read the top article summary.
    try:
        titles = parse_wiki_search(
            _fetch_json(WIKI_SEARCH.format(q=urllib.parse.quote(topic))))
        if titles:
            url_title = urllib.parse.quote(titles[0].replace(" ", "_"))
            article = parse_wiki_summary(
                _fetch_json(WIKI_SUMMARY.format(title=url_title)))
            if article:
                brief["summary"] = article["summary"][:1200]
                brief["facts"].extend(_sentences(article["summary"]))
                brief["sources"].append(
                    {"title": f"Wikipedia: {article['title']}", "url": article["url"]})
    except Exception as e:
        print(f"[research] Wikipedia unavailable ({e})")
    # 2) DuckDuckGo instant answer as a second source.
    try:
        ddg = parse_ddg(_fetch_json(DDG_API.format(q=urllib.parse.quote(topic))))
        if ddg:
            if not brief["summary"]:
                brief["summary"] = ddg["summary"][:1200]
            brief["facts"].extend(_sentences(ddg["summary"], limit=3))
            brief["sources"].append({"title": ddg["title"], "url": ddg["url"]})
    except Exception as e:
        print(f"[research] DuckDuckGo unavailable ({e})")
    brief["sources"] = brief["sources"][:max_sources]
    if not brief["facts"]:
        brief["note"] = ("No free sources returned facts — the plan is AI-only; "
                         "verify before publishing.")
    return brief
