"""Automated regression tests for JARVIS. Run from the repo root:

    python -m unittest discover tests

Tests that need heavy third-party packages (moviepy, faster-whisper, edge-tts)
are skipped automatically when those packages aren't installed.
"""

import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def _optional_import(module_name):
    try:
        return __import__(module_name, fromlist=["*"])
    except ImportError:
        return None


roblox_creator = _optional_import("skills.roblox_creator")
video_editor = _optional_import("skills.video_editor")

from core import skill_manager  # noqa: E402
from core.skill_manager import (  # noqa: E402
    register_skill, find_matching_skill, call_skill, load_all_skills,
)
import tools.scheduler as scheduler  # noqa: E402
from skills import idea_generator  # noqa: E402  (stdlib-only, always importable)
from skills import project_status  # noqa: E402  (stdlib-only, always importable)


class TestSkillManager(unittest.TestCase):
    def setUp(self):
        self._before = list(skill_manager._skills)

    def tearDown(self):
        skill_manager._skills[:] = self._before

    def test_trigger_matching_is_case_insensitive(self):
        register_skill("dummy", ["Turn On The Light"], lambda text: "ok", "safe")
        self.assertIsNotNone(find_matching_skill("please turn on the light now"))
        self.assertIsNone(find_matching_skill("something unrelated entirely"))

    def test_call_skill_supports_one_arg_handlers(self):
        register_skill("simple", ["simple"], lambda text: f"got:{text}", "safe")
        skill = find_matching_skill("run simple please")
        self.assertEqual(call_skill(skill, "hello", gemini_client=object()), "got:hello")

    def test_call_skill_supports_gemini_handlers(self):
        def handler(text, gemini_client=None):
            return f"client={gemini_client is not None}"
        register_skill("smart", ["smart"], handler, "safe")
        skill = find_matching_skill("be smart")
        self.assertEqual(call_skill(skill, "hi", gemini_client=object()), "client=True")
        self.assertEqual(call_skill(skill, "hi"), "client=False")

    def test_load_all_skills_never_crashes(self):
        # Even with missing third-party deps, discovery must not raise —
        # unimportable skill modules are skipped with a warning.
        loaded = load_all_skills()
        self.assertIsInstance(loaded, list)
        # Stdlib-only skills must always register.
        for name in ("test_skill", "idea_generator", "project_status", "caption_color"):
            if name == "caption_color" and video_editor is None:
                continue  # lives in the heavy video_editor module
            self.assertIn(name, [s["name"] for s in skill_manager._skills])


class TestScheduler(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".json")
        self._tmp.close()
        os.unlink(self._tmp.name)  # add_task must create it from scratch
        self._orig = scheduler.TASKS_FILE
        scheduler.TASKS_FILE = self._tmp.name

    def tearDown(self):
        scheduler.TASKS_FILE = self._orig
        if os.path.exists(self._tmp.name):
            os.unlink(self._tmp.name)

    def test_add_due_and_notify_roundtrip(self):
        scheduler.add_task("past thing", "2000-01-01 00:00")
        scheduler.add_task("future thing", "2999-01-01 00:00")
        due = scheduler.get_due_tasks()
        self.assertEqual([t["text"] for t in due], ["past thing"])
        scheduler.mark_notified(due[0]["id"])
        self.assertEqual(scheduler.get_due_tasks(), [])

    def test_bad_date_is_ignored(self):
        scheduler.add_task("broken", "not-a-date")
        self.assertEqual(scheduler.get_due_tasks(), [])


class TestIdeaParsing(unittest.TestCase):
    def test_defaults(self):
        count, topic = idea_generator.parse_idea_request("give me video ideas")
        self.assertEqual((count, topic), (5, "roblox"))

    def test_count_and_topic(self):
        count, topic = idea_generator.parse_idea_request(
            "give me 3 video ideas about tycoons")
        self.assertEqual((count, topic), (3, "tycoons"))

    def test_count_is_capped(self):
        count, _ = idea_generator.parse_idea_request("give me 99 ideas")
        self.assertEqual(count, 10)


class TestProjectStatus(unittest.TestCase):
    def test_gather_status_shape(self):
        status = project_status.gather_status()
        for key in ("videos", "scripts", "ideas", "voiceovers", "latest"):
            self.assertIn(key, status)

    def test_handler_always_answers(self):
        reply = project_status.handle_project_status("what have you made?")
        self.assertIsInstance(reply, str)
        self.assertIn("Sir Gerald", reply)


@unittest.skipIf(roblox_creator is None, "requires edge-tts/moviepy (pip install -r requirements.txt)")
class TestRobloxParsing(unittest.TestCase):
    def test_extract_topic_about(self):
        self.assertEqual(
            roblox_creator.extract_topic("make a Roblox rant about admin abusers"),
            "admin abusers")

    def test_extract_topic_strips_footage_request(self):
        self.assertEqual(
            roblox_creator.extract_topic("make a roblox rant about campers, use parkour.mp4"),
            "campers")

    def test_extract_footage_request(self):
        self.assertEqual(
            roblox_creator.extract_footage_request("make a rant about x, use parkour.mp4"),
            "parkour.mp4")
        self.assertIsNone(
            roblox_creator.extract_footage_request("make a rant about x"))


@unittest.skipIf(video_editor is None, "requires moviepy (pip install -r requirements.txt)")
class TestVideoEditor(unittest.TestCase):
    def test_supported_extensions_cover_common_formats(self):
        for ext in (".mp4", ".mov", ".mkv", ".avi"):
            self.assertIn(ext, video_editor.VIDEO_EXTENSIONS)


if __name__ == "__main__":
    unittest.main()
