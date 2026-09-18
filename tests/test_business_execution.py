"""Offline tests for universal business execution planning."""

import json
import os
import tempfile
import unittest
from unittest.mock import patch

from skills import business_assistant


class TestBusinessExecution(unittest.TestCase):
    def _write_project(self, directory):
        path = os.path.join(directory, "project.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump({
                "id": "project",
                "idea": "custom furniture",
                "created_at": "2026-09-18T10:00:00",
                "tasks": [
                    {"description": "Validate the offer", "risk": "safe", "status": "ready"},
                    {"description": "Contact customers", "risk": "approval_required", "status": "pending_approval"},
                ],
            }, f)

    def test_task_status_lists_latest_project(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            self._write_project(temp_dir)
            with patch.object(business_assistant, "PROJECTS_DIR", temp_dir):
                response = business_assistant.handle_business_tasks("show my business tasks")
            self.assertIn("pending_approval", response)
            self.assertIn("Contact customers", response)

    def test_risky_task_needs_approval_before_completion(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            self._write_project(temp_dir)
            with patch.object(business_assistant, "PROJECTS_DIR", temp_dir):
                blocked = business_assistant.handle_business_task_update(
                    "complete business task 2"
                )
                approved = business_assistant.handle_business_task_update(
                    "approve business task 2"
                )
                completed = business_assistant.handle_business_task_update(
                    "complete business task 2"
                )
            self.assertIn("requires approval", blocked)
            self.assertIn("approved", approved)
            self.assertIn("recorded as complete", completed)

    def test_plan_parser_requires_approval_for_risky_tasks(self):
        tasks = business_assistant._parse_execution_plan(
            "1. Validate the offer locally\n"
            "2. Contact ten potential customers\n"
            "3. Publish the landing page\n"
        )
        self.assertEqual(tasks[0]["status"], "ready")
        self.assertEqual(tasks[1]["status"], "pending_approval")
        self.assertEqual(tasks[2]["risk"], "approval_required")

    def test_financial_tasks_are_permanently_blocked(self):
        tasks = business_assistant._parse_execution_plan(
            "1. Open a bank account for the business\n"
            "2. Send a payment request\n"
        )
        self.assertEqual(tasks[0]["risk"], "blocked_financial")
        self.assertEqual(tasks[0]["status"], "blocked")
        self.assertEqual(tasks[1]["status"], "blocked")

    def test_blocked_financial_task_cannot_be_approved(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = os.path.join(temp_dir, "project.json")
            with open(path, "w", encoding="utf-8") as f:
                json.dump({
                    "id": "project",
                    "idea": "test",
                    "created_at": "2026-09-18T10:00:00",
                    "tasks": [{
                        "description": "Use a bank account",
                        "risk": "blocked_financial",
                        "status": "blocked",
                    }],
                }, f)
            with patch.object(business_assistant, "PROJECTS_DIR", temp_dir):
                response = business_assistant.handle_business_task_update(
                    "approve task 1"
                )
            self.assertIn("permanently blocked", response)

    def test_execution_supports_arbitrary_business_topic(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch.object(business_assistant, "PROJECTS_DIR", temp_dir), \
                    patch.object(
                        business_assistant,
                        "generate_text",
                        return_value=(
                            "1. Validate the offer\n"
                            "2. Send an outreach email\n"
                        ),
                    ):
                response = business_assistant.handle_business_execution(
                    "execute business idea for custom furniture"
                )

            files = os.listdir(temp_dir)
            self.assertEqual(len(files), 1)
            with open(os.path.join(temp_dir, files[0]), encoding="utf-8") as f:
                project = json.load(f)
            self.assertEqual(project["idea"], "custom furniture")
            self.assertEqual(project["tasks"][0]["status"], "ready")
            self.assertEqual(project["tasks"][1]["status"], "pending_approval")
            self.assertIn("approval", response.lower())


if __name__ == "__main__":
    unittest.main()
