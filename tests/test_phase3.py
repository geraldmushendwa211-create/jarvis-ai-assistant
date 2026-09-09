"""Phase-3 post-production tests — fully offline.

SFX picking, caption formatting, trim remapping, ffmpeg-output parsing, and
hashtag building are all pure functions: no network, no ffmpeg, no models.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core import captions, qc, seo, sfx  # noqa: E402


def _words(*items):
    """Build [{word, start, end}] from (word, start, end) tuples."""
    return [{"word": w, "start": s, "end": e} for w, s, e in items]


class TestSfx(unittest.TestCase):
    def setUp(self):
        import tempfile
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        for name in ("vine_boom.mp3", "bruh.mp3", "whoosh.mp3"):
            open(os.path.join(self._tmp.name, name), "w").close()

    def test_picks_mapped_sounds(self):
        words = _words(("hello", 0.0, 0.4), ("boom", 3.0, 3.4), ("lol", 6.0, 6.4))
        moments = sfx.pick_moments(words, self._tmp.name)
        self.assertEqual(len(moments), 2)
        self.assertIn("vine_boom", moments[0][1])
        self.assertIn("bruh", moments[1][1])
        self.assertAlmostEqual(moments[0][0], 3.0)

    def test_min_gap_and_cap(self):
        words = _words(("boom", 1.0, 1.2), ("boom", 1.5, 1.7), ("boom", 9.0, 9.2))
        moments = sfx.pick_moments(words, self._tmp.name, max_events=1)
        self.assertEqual(len(moments), 1)  # capped...
        moments = sfx.pick_moments(words, self._tmp.name, max_events=6)
        self.assertEqual(len(moments), 2)  # ...and gap-merged (1.5s skipped)

    def test_shouts_trigger_fallback(self):
        words = _words(("WHAT", 2.0, 2.5))
        moments = sfx.pick_moments(words, self._tmp.name)
        self.assertEqual(len(moments), 1)

    def test_empty_dir_gives_nothing(self):
        import tempfile
        with tempfile.TemporaryDirectory() as empty:
            self.assertEqual(sfx.pick_moments(_words(("boom", 1.0, 1.5)), empty), [])


class TestCaptions(unittest.TestCase):
    def test_chunking_splits_on_gap_and_size(self):
        words = _words(("a", 0.0, 0.2), ("b", 0.3, 0.5), ("c", 5.0, 5.2))
        chunks = captions.chunk_words(words, max_words=4, max_gap=1.2)
        self.assertEqual(len(chunks), 2)  # gap split
        words = _words(*[(f"w{i}", i * 0.3, i * 0.3 + 0.2) for i in range(6)])
        chunks = captions.chunk_words(words, max_words=4, max_gap=9.0)
        self.assertEqual([len(c) for c in chunks], [4, 2])  # size split

    def test_karaoke_marks_active_word(self):
        chunks = captions.chunk_words(_words(("hello", 0.0, 0.5), ("world", 0.6, 1.0)))
        events = captions.karaoke_events(chunks)
        self.assertEqual(len(events), 2)  # one event per word
        self.assertIn(captions.KARAOKE_ACTIVE, events[0])
        self.assertTrue(all(e.startswith("Dialogue:") for e in events))

    def test_ass_time_format(self):
        self.assertEqual(captions.format_ass_time(61.5), "0:01:01.50")
        self.assertEqual(captions.format_ass_time(-3), "0:00:00.00")


class TestTrimRemap(unittest.TestCase):
    def test_remap_compresses_cut_gaps(self):
        # Words at 0-1s and 10-11s with a 9s gap cut down to ~0.1s of padding.
        words = _words(("hello", 0.0, 1.0), ("world", 10.0, 11.0))
        segments = captions.compute_keep_segments(words, 11000, max_gap=0.4, padding=0.05)
        remapped = captions.remap_words(words, segments)
        self.assertAlmostEqual(remapped[0]["start"], 0.0)
        # 1.05s kept before the cut + 0.05s padding after = world starts ~1.1s
        self.assertAlmostEqual(remapped[1]["start"], 1.1, places=2)
        self.assertLess(remapped[1]["end"], 3.0)

    def test_remap_keeps_dense_speech(self):
        words = _words(("a", 0.0, 0.3), ("b", 0.4, 0.7))
        segments = captions.compute_keep_segments(words, 1000)
        remapped = captions.remap_words(words, segments)
        self.assertAlmostEqual(remapped[1]["start"], 0.4)


class TestQcParse(unittest.TestCase):
    FFMPEG_STDERR = """ffmpeg version 6.0
Input #0, mov,mp4,m4a,3gp,3g2,mj2, from 'out.mp4':
  Duration: 00:01:00.50, start: 0.000000, bitrate: 1200 kb/s
  Stream #0:0(und): Video: h264 (High), yuv420p, 1080x1920 [SAR 1:1 DAR 9:16], 30 fps
  Stream #0:1(und): Audio: aac (LC), 44100 Hz, stereo
"""

    def test_parse_duration_resolution_audio(self):
        info = qc.parse_ffmpeg_info(self.FFMPEG_STDERR)
        self.assertAlmostEqual(info["duration"], 60.5)
        self.assertEqual((info["width"], info["height"]), (1080, 1920))
        self.assertTrue(info["has_audio"])
        self.assertTrue(info["has_video"])

    def test_parse_garbage(self):
        info = qc.parse_ffmpeg_info("not ffmpeg output")
        self.assertEqual(info["duration"], 0.0)
        self.assertFalse(info["has_video"])


class TestSeo(unittest.TestCase):
    def test_hashtags(self):
        tags = seo.build_hashtags("Admin abusers are the worst", "Roblox")
        self.assertIn("#roblox", tags)
        self.assertIn("#shorts", tags)
        self.assertIn("#admin", tags)
        self.assertEqual(len(tags), len(set(tags)))  # deduped
        self.assertLessEqual(len(tags), 8)


if __name__ == "__main__":
    unittest.main()
