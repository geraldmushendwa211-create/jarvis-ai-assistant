"""Niche profiles: new content verticals via configuration, not code.

The universal video skill (skills/video_creator.py) detects which niche a
command belongs to and tunes the script style, tone, and footage search
accordingly. Adding a niche = one register_niche(...) call — no pipeline
changes needed.

Keyword matching uses word boundaries, so the "ai" keyword matches
"AI news" but NOT "training".
"""

import re
from dataclasses import dataclass


@dataclass
class NicheProfile:
    key: str                      # "roblox" — used in commands, folders, tickets
    label: str                    # "Roblox" — human-readable
    keywords: tuple = ()          # words/phrases that detect this niche
    script_style: str = ""        # style block appended to the script prompt
    default_tone: str = ""        # one-line tone description
    hook_hints: tuple = ()        # example hook patterns for this niche
    footage_hints: tuple = ()     # filename substrings preferred for footage


_profiles = {}
_order = []  # registration order; earlier profiles win detection ties


def register_niche(profile):
    _profiles[profile.key] = profile
    if profile.key not in _order:
        _order.append(profile.key)


def get_niche(key):
    return _profiles.get(key)


def list_niches():
    return list(_order)


def _keyword_hit(text, keyword):
    return re.search(r"\b" + re.escape(keyword) + r"\b", text) is not None


def detect_niche(text):
    """Return the best-matching NicheProfile for a command, else GENERIC."""
    lower = text.lower()
    best, best_hits = None, 0
    for key in _order:
        if key == "generic":
            continue
        profile = _profiles[key]
        hits = sum(1 for kw in profile.keywords if _keyword_hit(lower, kw))
        if hits > best_hits:
            best, best_hits = profile, hits
    return best or _profiles["generic"]


# ----------------------------------------------------------------------------
# Built-in niche profiles (specific niches first — they win detection ties)
# ----------------------------------------------------------------------------

register_niche(NicheProfile(
    key="roblox",
    label="Roblox",
    keywords=("roblox", "blox fruits", "brookhaven", "bedwars", "tower of hell",
              "obby", "adopt me", "doors"),
    script_style=(
        "Style rules:\n"
        "- Strong hook in the first line\n"
        "- Fast pacing, short sentences\n"
        "- Humor, exaggeration, relatability\n"
        "- Gaming slang used naturally (noob, grind, clutch, pay-to-win)\n"
        "- Punchy, memorable ending"
    ),
    default_tone="funny, high-energy gaming rant",
    hook_hints=("POV: ...", "Nobody talks about...", "This Roblox update ruined..."),
    footage_hints=("roblox",),
))

register_niche(NicheProfile(
    key="minecraft",
    label="Minecraft",
    keywords=("minecraft", "creeper", "redstone", "speedrun", "herobrine",
              "enderman", "nether", "diamond"),
    script_style=(
        "Style rules:\n"
        "- Sense of adventure and discovery\n"
        "- Short punchy sentences, building excitement\n"
        "- Reference iconic game elements (mobs, biomes, items)\n"
        "- End with a challenge or question to the viewer"
    ),
    default_tone="adventurous, playful explorer",
    hook_hints=("I found something impossible...", "Never do this in Minecraft..."),
    footage_hints=("minecraft", "mc"),
))

register_niche(NicheProfile(
    key="gaming",
    label="Gaming",
    keywords=("gta", "fortnite", "valorant", "warzone", "gaming", "gameplay",
              "video game", "cod", "elden ring"),
    script_style=(
        "Style rules:\n"
        "- Strong hook in the first line\n"
        "- Fast pacing, short sentences\n"
        "- Confident gamer energy with humor\n"
        "- Punchy, memorable ending"
    ),
    default_tone="confident, hype gamer commentary",
    hook_hints=("This game broke me...", "Rank #1 mistake..."),
    footage_hints=("gta", "gameplay", "fortnite"),
))

register_niche(NicheProfile(
    key="fitness",
    label="Fitness",
    keywords=("gym", "workout", "fitness", "muscle", "leg day", "pushup",
              "push-up", "exercise", "training", "gains"),
    script_style=(
        "Style rules:\n"
        "- Direct second-person coaching voice\n"
        "- Short motivational bursts mixed with one practical tip\n"
        "- No medical claims; keep advice general and safe\n"
        "- End with a call to action (today's workout)"
    ),
    default_tone="tough-love coach",
    hook_hints=("Stop skipping...", "Do this every morning...", "Your only competition..."),
    footage_hints=("gym", "workout", "fitness"),
))

register_niche(NicheProfile(
    key="horror",
    label="Horror",
    keywords=("horror", "scary", "creepypasta", "true crime", "mystery",
              "unsolved", "ghost", "haunted", "dark", "abandoned"),
    script_style=(
        "Style rules:\n"
        "- Slow-burn dread: unsettling hook, escalating details\n"
        "- Short sentences. Long pauses implied by line breaks\n"
        "- Never gory for shock value; psychological over graphic\n"
        "- End on an unresolved, chilling note"
    ),
    default_tone="ominous storyteller",
    hook_hints=("Nobody goes there anymore...", "The last recording...", "What happened next..."),
    footage_hints=("horror", "dark", "abandoned"),
))

register_niche(NicheProfile(
    key="tech",
    label="Tech & AI",
    keywords=("ai", "tech", "technology", "iphone", "gadget", "software",
              "coding", "programming", "robot", "chatgpt", "nvidia"),
    script_style=(
        "Style rules:\n"
        "- Explain like the viewer is smart but busy\n"
        "- One surprising fact or demo moment up front\n"
        "- Concrete details (names, numbers) over hype\n"
        "- End with what to watch next"
    ),
    default_tone="sharp, curious explainer",
    hook_hints=("This changes everything...", "Nobody expected...", "In 30 seconds you'll understand..."),
    footage_hints=("tech", "screen", "ai"),
))

register_niche(NicheProfile(
    key="education",
    label="Education",
    keywords=("physics", "science", "history", "math", "explain", "learn",
              "school", "facts", "documentary", "educational", "space",
              "psychology"),
    script_style=(
        "Style rules:\n"
        "- Simple words, big ideas (ELI5 energy, adult respect)\n"
        "- One clear concept per video, built step by step\n"
        "- Use an everyday analogy for the core idea\n"
        "- End with a one-sentence takeaway"
    ),
    default_tone="friendly expert teacher",
    hook_hints=("You've been lied to about...", "Here's why... actually works"),
    footage_hints=("documentary", "science", "space"),
))

register_niche(NicheProfile(
    key="motivation",
    label="Motivation",
    keywords=("motivation", "motivational", "mindset", "discipline", "success",
              "grind", "hustle"),
    script_style=(
        "Style rules:\n"
        "- Direct second-person, no fluff\n"
        "- Short rhythmic lines that hit like punches\n"
        "- One vivid metaphor or story, not platitudes\n"
        "- End with a single command for today"
    ),
    default_tone="relentless locker-room speech",
    hook_hints=("Nobody is coming to save you...", "You don't need more time..."),
    footage_hints=("gym", "running", "city"),
))

register_niche(NicheProfile(
    key="generic",
    label="General",
    keywords=(),
    script_style=(
        "Style rules:\n"
        "- Strong hook in the first line\n"
        "- Fast pacing, short sentences\n"
        "- Conversational and engaging\n"
        "- Punchy, memorable ending"
    ),
    default_tone="upbeat narrator",
    hook_hints=("Here's what nobody tells you...",),
    footage_hints=(),
))
