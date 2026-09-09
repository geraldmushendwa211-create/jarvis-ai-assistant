"""Video idea brainstormer: "give me 5 Roblox video ideas about pets".

Generates numbered, hook-first YouTube Short ideas via Gemini, saves them to
workspace/scripts/ideas_<timestamp>.txt, and reads back a short summary.
"""

import os
import re
from datetime import datetime
from core.skill_manager import register_skill

SCRIPTS_DIR = "workspace/scripts"
MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash")

DEFAULT_COUNT = 5
MAX_COUNT = 10


def parse_idea_request(user_input):
    """Extract (count, topic) from commands like 'give me 3 ideas about tycoons'."""
    lower = user_input.lower()
    count = DEFAULT_COUNT
    match = re.search(r"(\d+)\s*(video\s*)?ideas?", lower)
    if match:
        count = max(1, min(int(match.group(1)), MAX_COUNT))
    topic = "roblox"
    for keyword in ("ideas about", "ideas on", "idea about", "idea on"):
        if keyword in lower:
            topic = user_input[lower.index(keyword) + len(keyword):].strip()
            break
    return count, topic or "roblox"


def handle_idea_generator(user_input, gemini_client=None):
    count, topic = parse_idea_request(user_input)
    if gemini_client is None:
        return "I need access to the AI model to brainstorm, Sir Gerald. Something's misconfigured."

    prompt = (
        f"Brainstorm {count} YouTube Short video ideas about Roblox, "
        f"focused on: {topic}\n\n"
        "Rules:\n"
        f"- Exactly {count} numbered ideas\n"
        "- Each idea is one punchy line: a title plus a one-sentence hook\n"
        "- Optimized for rants, humor, and relatability (30-60 second Shorts)\n"
        "- No introductions, no conclusions, just the numbered list"
    )
    response = gemini_client.models.generate_content(model=MODEL, contents=prompt)
    ideas_text = response.text.strip()

    os.makedirs(SCRIPTS_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    ideas_path = os.path.join(SCRIPTS_DIR, f"ideas_{timestamp}.txt")
    with open(ideas_path, "w", encoding="utf-8") as f:
        f.write(f"Topic: {topic}\n\n{ideas_text}\n")

    # Speak a compact version: first two ideas + pointer to the file.
    lines = [line.strip() for line in ideas_text.splitlines() if line.strip()][:2]
    preview = " ".join(lines)
    return (
        f"I've brainstormed {count} ideas about {topic}, Sir Gerald — "
        f"saved to {ideas_path}. Here's a taste: {preview}"
    )


register_skill(
    name="idea_generator",
    triggers=[
        "video ideas", "video idea", "give me ideas", "brainstorm",
        "content ideas", "rant ideas",
    ],
    handler=handle_idea_generator,
    permission_level="safe",
)
