"""Offline tests for read-only JARVIS diagnostics."""

import os
import tempfile
import unittest

from skills import system_diagnostics


class TestSystemDiagnostics(unittest.TestCase):
    def test_reports_missing_key_without_exposing_values(self):
        with tempfile.TemporaryDirectory() as root_dir:
            checks = system_diagnostics.gather_diagnostics(
                environ={"GEMINI_API_KEY": "super-secret-key"},
                root_dir=root_dir,
            )
        rendered = system_diagnostics.format_diagnostics(checks)
        self.assertNotIn("super-secret-key", rendered)
        self.assertIn("Financial access", rendered)
        self.assertIn("blocked by design", rendered)

    def test_reports_missing_dashboard_and_workspace(self):
        with tempfile.TemporaryDirectory() as root_dir:
            checks = system_diagnostics.gather_diagnostics(
                environ={},
                root_dir=root_dir,
            )
        by_name = {check["name"]: check for check in checks}
        self.assertEqual(by_name["Dashboard"]["status"], "WARN")
        self.assertEqual(by_name["workspace"]["status"], "WARN")
        self.assertEqual(by_name["External actions"]["detail"], "approval-gated")

    def test_dashboard_check_passes_when_file_exists(self):
        with tempfile.TemporaryDirectory() as root_dir:
            os.makedirs(os.path.join(root_dir, "web"))
            with open(os.path.join(root_dir, "web", "index.html"), "w", encoding="utf-8") as f:
                f.write("<html></html>")
            checks = system_diagnostics.gather_diagnostics(
                environ={"GEMINI_API_KEY": "configured"},
                root_dir=root_dir,
            )
        dashboard = next(check for check in checks if check["name"] == "Dashboard")
        self.assertEqual(dashboard["status"], "OK")


if __name__ == "__main__":
    unittest.main()
