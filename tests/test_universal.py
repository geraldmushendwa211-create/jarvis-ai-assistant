"""Tests for the universal-agent foundations: niche profiles + project tickets.

Run from the repo root:  python -m unittest discover tests
"""

import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core import niches  # noqa: E402
from core import project as project_mod  # noqa: E402
from core.project import VideoProject  # noqa: E402


class TestNiches(unittest.TestCase):
    def test_detect_specific_niches(self):
        self.assertEqual(
            niches.detect_niche("make a minecraft short about diamonds").key,
            "minecraft")
        self.assertEqual(
            niches.detect_niche("make a roblox video about admins").key,
            "roblox")
        self.assertEqual(
            niches.detect_niche("create a gym workout video").key, "fitness")
        self.assertEqual(
            niches.detect_niche("make a horror short about ghosts").key, "horror")

    def test_ai_keyword_needs_word_boundary(self):
        # "training" contains "ai" but must NOT detect the tech niche.
        self.assertEqual(
            niches.detect_niche("make a fitness video about training").key,
            "fitness")
        self.assertEqual(
            niches.detect_niche("make a video about AI news").key, "tech")

    def test_unknown_falls_back_to_generic(self):
        self.assertEqual(
            niches.detect_niche("make a video about cooking pasta").key,
            "generic")

    def test_registry_lists_defaults(self):
        for key in ("roblox", "minecraft", "gaming", "fitness", "horror",
                    "tech", "education", "motivation", "generic"):
            self.assertIn(key, niches.list_niches())

    def test_custom_niche_registration(self):
        profile = niches.NicheProfile(
            key="testcooking",
            label="Cooking",
            keywords=("sourdough",),
            script_style="Cozy recipe narration.",
            default_tone="warm",
        )
        niches.register_niche(profile)
        try:
            self.assertEqual(
                niches.detect_niche("make a sourdough video").key, "testcooking")
        finally:
            del niches._profiles["testcooking"]
            niches._order.remove("testcooking")


class TestVideoProject(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self._orig = project_mod.PROJECTS_DIR
        project_mod.PROJECTS_DIR = self._tmp.name

    def tearDown(self):
        project_mod.PROJECTS_DIR = self._orig
        self._tmp.cleanup()

    def test_save_load_roundtrip(self):
        ticket = VideoProject.new("Admin abusers", niche="roblox", format="short")
        ticket.mark("scripted", "426 words")
        loaded = VideoProject.load(ticket.id)
        self.assertEqual(loaded.topic, "Admin abusers")
        self.assertEqual(loaded.niche, "roblox")
        self.assertEqual(loaded.status, "scripted")
        self.assertEqual(len(loaded.stages), 1)
        self.assertEqual(loaded.stages[0]["stage"], "scripted")

    def test_fail_records_error(self):
        ticket = VideoProject.new("X")
        ticket.fail("boom")
        loaded = VideoProject.load(ticket.id)
        self.assertEqual(loaded.status, "failed")
        self.assertEqual(loaded.error, "boom")

    def test_list_recent(self):
        VideoProject.new("one").save()
        VideoProject.new("two").save()
        recent = VideoProject.list_recent(limit=5)
        self.assertEqual(len(recent), 2)

    def test_list_recent_ignores_garbage(self):
        with open(os.path.join(self._tmp.name, "nope.json"), "w") as f:
            f.write("{not valid json")
        self.assertEqual(VideoProject.list_recent(), [])


if __name__ == "__main__":
    unittest.main()
