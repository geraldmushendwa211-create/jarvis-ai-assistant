"""Caption helpers: word chunking, karaoke events, trim time-remapping.

All pure functions (no heavy deps) so they're unit-tested offline.

Why remapping matters: the voiceover is transcribed ONCE (from the original
audio), then dead air is cut — which shifts every later timestamp. remap_words
translates original timings into trimmed-audio timings so captions and SFX
stay in sync without a second Whisper pass.
"""

KARAOKE_ACTIVE = "&H0000D7FF"  # gold
KARAOKE_BASE = "&H00FFFFFF"    # white


def format_ass_time(seconds):
    seconds = max(0.0, float(seconds))
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    cs = int((seconds - int(seconds)) * 100)
    return f"{h:01}:{m:02}:{s:02}.{cs:02}"


def chunk_words(words, max_words=4, max_gap=1.2):
    """Group word timings into karaoke caption lines."""
    chunks, current = [], []
    prev_end = None
    for w in words:
        gap = (w["start"] - prev_end) if prev_end is not None else 0.0
        if current and (len(current) >= max_words or gap > max_gap):
            chunks.append(current)
            current = []
        current.append(w)
        prev_end = w["end"]
    if current:
        chunks.append(current)
    return chunks


def karaoke_events(chunks):
    """Render chunks as ASS events with the active word highlighted.

    Each word gets one event showing its whole line, with the spoken word in
    the active color. Returns a list of Dialogue lines (no header).
    """
    events = []
    for chunk in chunks:
        for i, word in enumerate(chunk):
            parts = []
            for j, other in enumerate(chunk):
                text = other["word"].strip().upper()
                if j == i:
                    parts.append(f"{{\\c{KARAOKE_ACTIVE}&}}{text}{{\\c{KARAOKE_BASE}&}}")
                else:
                    parts.append(text)
            events.append(
                f"Dialogue: 0,{format_ass_time(word['start'])},"
                f"{format_ass_time(word['end'])},Caption,,0,0,0,,{' '.join(parts)}"
            )
    return events


def compute_keep_segments(words, total_ms, max_gap=0.4, padding=0.05):
    """Plan a silence trim: [(keep_from_sec, keep_to_sec), ...]."""
    keep_segments = []
    cursor = 0.0
    for i in range(len(words) - 1):
        gap_start = words[i]["end"]
        gap_end = words[i + 1]["start"]
        if gap_end - gap_start > max_gap:
            keep_segments.append((cursor, gap_start + padding))
            cursor = gap_end - padding
    keep_segments.append((cursor, total_ms / 1000))
    return keep_segments


def _remap_time(t, keep_segments):
    """Map original-audio seconds -> trimmed-audio seconds."""
    out = 0.0
    for start, end in keep_segments:
        if t <= start:
            return out  # inside a removed gap — clamp to the cut point
        out += min(t, end) - start
        if t <= end:
            return out
    return out


def remap_words(words, keep_segments):
    """Translate word timings through a trim plan (see compute_keep_segments)."""
    remapped = []
    for w in words:
        remapped.append({
            "word": w["word"],
            "start": _remap_time(w["start"], keep_segments),
            "end": _remap_time(w["end"], keep_segments),
        })
    return remapped
