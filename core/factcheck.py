"""Fact-check pass: heuristic claim scanner (no AI, instant, free).

Flags superlatives, absolutes, and bare numbers so risky lines get a human
look before publishing. These are warnings, not verdicts — JARVIS never
claims a script is "verified".

Used on research-backed scripts for factual niches (education, tech), both
in the strategy skill (plan stage) and inside video_creator (script stage).
"""

import re

SUPERLATIVES = ("biggest", "smallest", "first", "only", "best", "worst",
                "greatest", "fastest", "richest", "deadliest", "proves",
                "proven", "guaranteed", "miracle")
ABSOLUTES = ("always", "never", "everyone", "nobody")
NUMBER_RE = re.compile(
    r"\b\d+(\.\d+)?\s*(%|percent|million|billion|dollars|years|deaths|views)\b",
    re.IGNORECASE)


def check_text(text):
    """Scan text line by line. Returns [{line, flag, detail}]; [] = clean."""
    flags = []
    for lineno, line in enumerate((text or "").splitlines(), start=1):
        low = line.lower()
        for word in SUPERLATIVES:
            if re.search(r"\b" + re.escape(word) + r"\b", low):
                flags.append({"line": lineno, "flag": word,
                              "detail": f"superlative '{word}' — verify against a source"})
                break
        for word in ABSOLUTES:
            if re.search(r"\b" + re.escape(word) + r"\b", low):
                flags.append({"line": lineno, "flag": word,
                              "detail": f"absolute '{word}' — rarely literally true"})
                break
        if NUMBER_RE.search(line):
            flags.append({"line": lineno, "flag": "number",
                          "detail": "concrete number — confirm it has a source"})
    return flags


def summarize(flags):
    if not flags:
        return "No risky claims spotted."
    shown = "; ".join(f"L{f['line']}: {f['detail']}" for f in flags[:5])
    extra = f" (+{len(flags) - 5} more)" if len(flags) > 5 else ""
    return f"{len(flags)} line(s) need a human look: {shown}{extra}"
