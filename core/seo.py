"""SEO pack: title, description, hashtags for a finished video.

build_hashtags() is pure (unit-tested); generate_seo() makes one Gemini call
for the description and assembles the pack; write_seo_file() saves a readable
markdown copy next to the scripts.
"""

import os
import re

SCRIPTS_DIR = "workspace/scripts"

STOPWORDS = frozenset("""
a an the and or but for nor with are was were been being have has had do does
did will would can could should this that these those from into over after you
your they their them its it of off out about
""".split())


def build_hashtags(topic, niche_label, limit=8):
    tags, seen = [], set()

    def add(tag):
        clean = re.sub(r"[^a-z0-9]", "", (tag or "").lower())
        if len(clean) >= 3 and clean not in seen and clean not in STOPWORDS:
            seen.add(clean)
            tags.append("#" + clean)

    add(niche_label)
    add("shorts")
    add("viral")
    for word in re.findall(r"[a-z0-9']+", (topic or "").lower()):
        add(word.strip("'"))
    return tags[:limit]


def generate_seo(topic, niche_label, gemini_client, model=None):
    prompt = (
        f"Write a YouTube Short description for a {niche_label} video about: {topic}\n"
        "Rules: 2-3 punchy sentences, one line inviting comments, no hashtags, "
        "no quotes. Just the description."
    )
    response = gemini_client.models.generate_content(
        model=model or os.getenv("GEMINI_MODEL", "gemini-3.5-flash"),
        contents=prompt,
    )
    description = response.text.strip().strip("\"'")
    return {
        "title": (topic or "").strip().rstrip("."),
        "description": description,
        "hashtags": build_hashtags(topic, niche_label),
    }


def write_seo_file(ticket_id, topic, seo):
    os.makedirs(SCRIPTS_DIR, exist_ok=True)
    path = os.path.join(SCRIPTS_DIR, f"seo_{ticket_id}.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write(f"# SEO pack: {topic}\n\n"
                f"## Title\n{seo['title']}\n\n"
                f"## Description\n{seo['description']}\n\n"
                f"## Hashtags\n{' '.join(seo['hashtags'])}\n")
    return path
