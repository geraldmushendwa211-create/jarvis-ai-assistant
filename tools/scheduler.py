import json
import os
from datetime import datetime

TASKS_FILE = os.path.join(os.path.dirname(__file__), "..", "memory", "tasks.json")

DUE_FORMAT = "%Y-%m-%d %H:%M"


def load_tasks():
    if not os.path.exists(TASKS_FILE):
        return []
    with open(TASKS_FILE, "r") as f:
        return json.load(f)


def save_tasks(tasks):
    with open(TASKS_FILE, "w") as f:
        json.dump(tasks, f, indent=2)


def add_task(text, due_time):
    """due_time format: 'YYYY-MM-DD HH:MM' e.g. '2026-08-14 15:00'

    Raises ValueError if due_time doesn't match, so a bad reminder fails
    loudly here — at creation time — instead of silently never firing later.
    """
    datetime.strptime(due_time, DUE_FORMAT)
    tasks = load_tasks()
    new_id = (max([t["id"] for t in tasks]) + 1) if tasks else 1
    tasks.append({"id": new_id, "text": text, "due": due_time, "notified": False})
    save_tasks(tasks)
    return new_id


def get_due_tasks():
    """Tasks whose time has arrived and haven't been announced yet"""
    tasks = load_tasks()
    now = datetime.now()
    due = []
    for t in tasks:
        if not t["notified"]:
            try:
                due_dt = datetime.strptime(t["due"], DUE_FORMAT)
                if due_dt <= now:
                    due.append(t)
            except (ValueError, KeyError):
                # Corrupt/legacy row — skip it rather than crashing the
                # reminder checker on every poll.
                continue
    return due


def mark_notified(task_id):
    tasks = load_tasks()
    for t in tasks:
        if t["id"] == task_id:
            t["notified"] = True
    save_tasks(tasks)
