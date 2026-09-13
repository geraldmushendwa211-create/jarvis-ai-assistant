"""YouTube publisher tests — fully offline.

Google API imports inside the publisher are lazy, so registration, title
parsing, privacy handling, and latest-video lookup all test without the
upload dependencies (or network) installed.
"""

import os
import sys
import tempfile
import time
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from skills import youtube_publisher as pub  # noqa: E402 (lazy google imports)
from core import project as project_mod  # noqa: E402
from core.project import VideoProject  # noqa: E402


class TestPrivacy(unittest.TestCase):
    def test_normalize(self):
        self.assertEqual(pub.normalize_privacy("PUBLIC"), "public")
        self.assertEqual(pub.normalize_privacy("unlisted"), "unlisted")
        self.assertEqual(pub.normalize_privacy(""), "private")
        self.assertEqual(pub.normalize_privacy("pubic"), "private")  # typo-safe


class TestExtractTitle(unittest.TestCase):
    def test_quoted(self):
        self.assertEqual(
            pub.extract_title('upload it titled "My Epic Rant"', "x.mp4"),
            "My Epic Rant")

    def test_as(self):
        self.assertEqual(
            pub.extract_title("upload my video as gym day", "x.mp4"),
            "gym day")

    def test_filename_fallback(self):
        title = pub.extract_title(
            "upload my latest video",
            "output_final_2026-09-09_10-00-00_admin-abusers.mp4")
        self.assertIn("Admin", title)
        self.assertNotIn("output_final", title)


class TestFindLatest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self._orig_out, self._orig_latest = pub.OUTPUT_DIR, pub.LATEST_FILE
        pub.OUTPUT_DIR = self._tmp.name
        pub.LATEST_FILE = os.path.join(self._tmp.name, "latest.txt")

    def tearDown(self):
        pub.OUTPUT_DIR, pub.LATEST_FILE = self._orig_out, self._orig_latest

    def _touch(self, name, age=0):
        path = os.path.join(self._tmp.name, name)
        with open(path, "w"):
            pass
        stamp = time.time() - age
        os.utime(path, (stamp, stamp))
        return path

    def test_none_when_empty(self):
        self.assertIsNone(pub.find_latest_video())

    def test_prefers_final_renders(self):
        self._touch("output_captioned_x.mp4", age=1)   # newer, but intermediate
        final = self._touch("output_final_x.mp4", age=100)
        self.assertEqual(pub.find_latest_video(), final)

    def test_latest_txt_wins(self):
        self._touch("output_final_x.mp4")
        other = self._touch("random.mp4")
        with open(pub.LATEST_FILE, "w") as f:
            f.write(other)
        self.assertEqual(pub.find_latest_video(), other)


class TestRecordUpload(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self._orig = project_mod.PROJECTS_DIR
        project_mod.PROJECTS_DIR = self._tmp.name

    def tearDown(self):
        project_mod.PROJECTS_DIR = self._orig

    def test_records_url_on_matching_ticket(self):
        ticket = VideoProject.new("X")
        ticket.output_path = os.path.join("workspace", "output", "v.mp4")
        ticket.save()
        found = pub.record_upload(ticket.output_path, "abc123")
        self.assertIsNotNone(found)
        self.assertEqual(VideoProject.load(ticket.id).youtube_url,
                         "https://youtu.be/abc123")

    def test_no_ticket_returns_none(self):
        self.assertIsNone(pub.record_upload("whatever.mp4", "abc123"))


class TestRegistration(unittest.TestCase):
    def test_skill_registered_and_matches(self):
        from core import skill_manager
        from core.skill_manager import find_matching_skill
        names = [s["name"] for s in skill_manager._skills]
        self.assertIn("youtube_publisher", names)
        skill = find_matching_skill("please upload my video to youtube")
        self.assertIsNotNone(skill)
        self.assertEqual(skill["permission_level"], "approval_required")


if __name__ == "__main__":
    unittest.main()
