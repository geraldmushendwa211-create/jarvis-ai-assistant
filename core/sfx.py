"""SFX auto-placement: match punchy words to meme sounds.

pick_moments() is pure (word timings + a folder listing in, timed events
out), so it's unit-tested offline. Triggers: mapped punch words ("boom",
"bruh", "but"...) plus ALL-CAPS shouts. A minimum gap keeps videos from
turning into a soundboard, and events are capped per video.
"""

import os
import re

# trigger words -> filename hints (matched against workspace/sfx/ files)
TRIGGER_MAP = (
    (("boom", "explode", "explodes", "explosion", "crash", "bang"), ("boom",)),
    (("bruh", "lol", "haha", "lmao", "funny", "ndalaaa"), ("bruh", "ndalaa")),
    (("but", "however", "suddenly", "wait", "plot", "twist", "meanwhile"),
     ("whoosh",)),
)

AUDIO_EXTENSIONS = (".mp3", ".wav", ".ogg", ".m4a")


def _clean(word):
    return re.sub(r"[^a-z]", "", (word or "").lower())


def _sfx_files(sfx_dir):
    if not sfx_dir or not os.path.isdir(sfx_dir):
        return []
    return sorted(f for f in os.listdir(sfx_dir)
                  if f.lower().endswith(AUDIO_EXTENSIONS))


def _match_file(files, hints):
    for hint in hints:
        for f in files:
            if hint in f.lower():
                return f
    return None


def pick_moments(words, sfx_dir, max_events=6, min_gap=2.0):
    """Choose SFX placements. Returns [(seconds, filepath)] sorted + capped."""
    files = _sfx_files(sfx_dir)
    if not files or not words:
        return []
    trigger_to_file = {}
    for triggers, hints in TRIGGER_MAP:
        matched = _match_file(files, hints)
        if matched:
            for trigger in triggers:
                trigger_to_file[trigger] = matched
    fallback = files[0]
    moments = []
    last_time = None
    for w in words:
        raw = (w.get("word") or "").strip()
        clean = _clean(raw)
        if not clean:
            continue
        is_shout = raw.isupper() and len(clean) >= 3
        filename = trigger_to_file.get(clean)
        if filename is None and not is_shout:
            continue
        start = float(w.get("start", 0))
        if last_time is not None and start - last_time < min_gap:
            continue
        moments.append((start, os.path.join(sfx_dir, filename or fallback)))
        last_time = start
        if len(moments) >= max_events:
            break
    return moments
