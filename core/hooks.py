"""Title/hook agent: generate N titles with Gemini, score them heuristically.

score_hook() is deterministic (no AI) so it's fast, free, and unit-tested:
questions, numbers, power words, and tight length score up; vagueness and
bloat score down. generate_and_pick() regenerates once if the best title
is weak — the rewrite loop from the roadmap.
"""

import os
import re

MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash")

POWER_WORDS = ("secret", "secrets", "mistake", "mistakes", "free", "proven",
               "insane", "hidden", "truth", "lies", "stop", "why", "how",
               "vs", "ranked", "exposed", "nobody", "everyone")


def score_hook(text):
    """Score a title 0-100. Returns (score, feedback_list). Pure (no AI)."""
    t = (text or "").strip()
    if not t:
        return 0, ["empty title"]
    feedback = []
    score = 50
    words = t.split()

    # Length sweet spot: 5-12 words.
    if 5 <= len(words) <= 12:
        score += 10
    elif len(words) > 14:
        score -= 12
        feedback.append("too long — trim to ~5-12 words")
    elif len(words) < 4:
        score -= 8
        feedback.append("too short to promise anything")

    if "?" in t:
        score += 12
        feedback.append("question hook")

    if re.search(r"\d", t):
        score += 10
        feedback.append("numbered promise")

    found = sorted({w for w in POWER_WORDS
                    if re.search(r"\b" + re.escape(w) + r"\b", t.lower())})
    if found:
        score += min(16, 8 * len(found))
        feedback.append("power words: " + ", ".join(found[:3]))

    if re.search(r"\b(thing|stuff|video|content)\b", t.lower()) and len(words) < 6:
        score -= 8
        feedback.append("vague filler words")

    letters = [c for c in t if c.isalpha()]
    if letters and len(letters) > 10 and \
            sum(1 for c in letters if c.isupper()) / len(letters) > 0.7:
        score -= 10
        feedback.append("all-caps looks spammy")

    return max(0, min(100, score)), feedback


def pick_best(titles):
    """Rank titles best-first. Returns [(title, score, feedback)]."""
    scored = [(title, *score_hook(title)) for title in titles]
    scored.sort(key=lambda item: item[1], reverse=True)
    return scored


def generate_titles(topic, niche_label, tone, gemini_client, count=5):
    prompt = (
        f"Write exactly {count} YouTube Short titles about: {topic}\n"
        f"Niche: {niche_label}. Tone: {tone}.\n"
        "Rules: each title on its own numbered line, 5-12 words, no clickbait "
        "lies, no hashtags, no quotes. Just the numbered list."
    )
    response = gemini_client.models.generate_content(model=MODEL, contents=prompt)
    titles = []
    for line in response.text.strip().splitlines():
        line = re.sub(r"^\s*\d+[\).\:\-]\s*", "", line).strip().strip("\"'")
        if line:
            titles.append(line)
    return titles[:count]


def generate_and_pick(topic, niche, gemini_client, count=5, min_score=70):
    """Generate titles, score them, regenerate once if the best is weak."""
    titles = generate_titles(topic, niche.label, niche.default_tone,
                             gemini_client, count)
    ranked = pick_best(titles)
    if ranked and ranked[0][1] < min_score:
        retry = generate_titles(f"{topic} (stronger hooks: use a question or number)",
                                niche.label, niche.default_tone,
                                gemini_client, count)
        ranked = pick_best(titles + retry)
    return ranked
