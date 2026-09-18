"""Business & money-making assistant: research, planning, and safe execution.

Commands:
    "research business idea for X" / "market research on X"
        -> honest brief: what it is, realistic income potential, competition,
           how to get started. Saved to workspace/business/.
    "give me business ideas for X" / "brainstorm business ideas about X"
        -> numbered list of ideas. Saved to workspace/business/.
    "draft a proposal for X" / "write a freelance proposal for X"
        -> a proposal draft for YOU to review and send yourself.
    "execute business idea for X" / "start business X"
        -> creates a reusable business project with safe local tasks completed
           and risky tasks queued for explicit approval.
    "show my business tasks" / "approve business task 2"
        -> reports or updates the latest project's task queue. Approval only
           changes the recorded state; it never performs an outside action.

Design: business execution is capability-neutral. The same workflow can plan
a service, product, content business, shop, or other legal business. JARVIS
may create local files and plans automatically, but it never sends messages,
publishes, creates accounts, exposes private data, signs agreements, or moves
money. Banking, payment, wallet, card, transfer, investment, and financial
account actions are permanently blocked; they cannot be approved by JARVIS.
"""

import os
import json
import re
from datetime import datetime

from core.skill_manager import register_skill
from core.llm_router import generate_text

BUSINESS_DIR = "workspace/business"
PROPOSALS_DIR = "workspace/business/proposals"
PROJECTS_DIR = os.path.join(BUSINESS_DIR, "projects")

HONESTY_RULE = (
    "Be realistic and honest — no guaranteed income claims, no "
    "get-rich-quick framing, no pyramid/MLM-style schemes. Mention real "
    "risks and effort required alongside the upside."
)

FINANCIAL_BLOCKED_TERMS = (
    "bank", "banking", "payment", "pay ", "pay.", "paying", "wallet",
    "credit card", "debit card", "card number", "routing number", "account",
    "password", "pin", "token", "transfer", "wire", "withdraw", "deposit",
    "buy ", "buy.", "purchase", "spend", "checkout", "invest", "loan",
    "crypto", "financial institution",
)


def _classify_task(description):
    lower = description.lower()
    if any(term in lower for term in FINANCIAL_BLOCKED_TERMS):
        return "blocked_financial", "blocked"
    if any(word in lower for word in (
        "send", "contact", "publish", "post", "legal", "contract", "sign",
        "hire", "private", "client data", "personal data",
    )):
        return "approval_required", "pending_approval"
    return "safe", "ready"


def _topic_after(text, keywords=("for", "on", "about")):
    lower = text.lower()
    for keyword in keywords:
        pattern = f" {keyword} "
        if pattern in lower:
            topic = text[lower.index(pattern) + len(pattern):].strip().strip("?\"'")
            if topic:
                return topic
    return ""


def handle_business_research(user_input, gemini_client=None):
    topic = _topic_after(user_input)
    if not topic:
        return "What business idea should I research, Sir Gerald? Try: research business idea for pet photography."

    prompt = (
        f"Write a short, honest market-research brief on this business idea: {topic}\n\n"
        "Cover in plain sentences:\n"
        "1. What it actually involves day-to-day\n"
        "2. Realistic income range and how long it typically takes to get there\n"
        "3. Main competition and what makes it hard\n"
        "4. Concrete first steps to test it cheaply before committing\n"
        f"{HONESTY_RULE}\n"
        "Write it as plain prose, no markdown headers, 150-250 words."
    )
    try:
        brief = generate_text(prompt, gemini_client=gemini_client)
    except RuntimeError as e:
        return f"I can't research that right now, Sir Gerald: {e}"

    os.makedirs(BUSINESS_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    path = os.path.join(BUSINESS_DIR, f"research_{timestamp}.txt")
    with open(path, "w", encoding="utf-8") as f:
        f.write(f"Topic: {topic}\n\n{brief}\n")

    preview = " ".join(brief.split()[:35]) + "..."
    return f"Research done on '{topic}', Sir Gerald — saved to {path}. Quick preview: {preview}"


def handle_business_ideas(user_input, gemini_client=None):
    topic = _topic_after(user_input) or "general online business ideas"
    prompt = (
        f"Brainstorm 5 realistic small-business or freelance ideas related to: {topic}\n"
        "For each: a one-line name, then a one-sentence explanation of how "
        f"someone would actually start and earn from it.\n{HONESTY_RULE}\n"
        "Numbered list, no other text."
    )
    try:
        ideas = generate_text(prompt, gemini_client=gemini_client)
    except RuntimeError as e:
        return f"I can't brainstorm that right now, Sir Gerald: {e}"

    os.makedirs(BUSINESS_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    path = os.path.join(BUSINESS_DIR, f"ideas_{timestamp}.txt")
    with open(path, "w", encoding="utf-8") as f:
        f.write(f"Topic: {topic}\n\n{ideas}\n")

    first_line = ideas.strip().splitlines()[0] if ideas.strip() else ""
    return f"I've brainstormed some ideas around '{topic}', Sir Gerald — saved to {path}. First one: {first_line}"


def handle_business_proposal(user_input, gemini_client=None):
    topic = _topic_after(user_input)
    if not topic:
        return "What's the proposal for, Sir Gerald? Try: draft a proposal for a logo design job."

    prompt = (
        f"Write a short, professional freelance proposal for this job/service: {topic}\n\n"
        "Keep it to 3-4 short paragraphs: a warm opener, why you're a good "
        "fit (keep this generic/placeholder since you don't know the real "
        "freelancer's background), what you'd deliver, and a closing line "
        "inviting a reply. No fake credentials, no invented past clients or "
        "results. Plain text, no markdown."
    )
    try:
        draft = generate_text(prompt, gemini_client=gemini_client)
    except RuntimeError as e:
        return f"I can't draft that right now, Sir Gerald: {e}"

    os.makedirs(PROPOSALS_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    path = os.path.join(PROPOSALS_DIR, f"proposal_{timestamp}.txt")
    with open(path, "w", encoding="utf-8") as f:
        f.write(draft)

    return (f"Proposal draft ready for '{topic}', Sir Gerald — saved to {path}. "
            f"This is just a draft for you to review, personalize, and send "
            f"yourself — I haven't sent anything anywhere.")


def _parse_execution_plan(text):
    """Parse a conservative, line-based plan so malformed model output is safe."""
    tasks = []
    for line in text.splitlines():
        match = re.match(r"\s*(?:[-*]|\d+[.)])\s*(.+)", line)
        if not match:
            continue
        description = match.group(1).strip()
        if not description:
            continue
        risk, status = _classify_task(description)
        tasks.append({
            "description": description,
            "risk": risk,
            "status": status,
        })
    return tasks[:12]


def handle_business_execution(user_input, gemini_client=None):
    """Create a universal business execution project without unsafe side effects."""
    topic = _topic_after(user_input)
    if not topic:
        return ("What business should I execute, Sir Gerald? Try: execute business "
                "idea for a local video editing service.")

    prompt = (
        f"Create a practical first execution plan for this business idea: {topic}\n"
        "Return 8-12 numbered tasks, one task per line. Start with validation, "
        "the first offer, a simple delivery process, and a way to measure the "
        "first result. Include external actions only as clearly worded tasks. "
        "Do not suggest illegal activity, deception, spam, evasion, or unsafe "
        "financial actions. Never access a bank, payment, wallet, card, or "
        "financial account, and never use credentials or move money. If such "
        "a task is relevant, label it BLOCKED instead. Plain text, no headings."
    )
    try:
        plan_text = generate_text(prompt, gemini_client=gemini_client)
    except RuntimeError as e:
        return f"I can't create that execution plan right now, Sir Gerald: {e}"

    tasks = _parse_execution_plan(plan_text)
    if not tasks:
        return (f"I couldn't turn '{topic}' into a safe task list, Sir Gerald. "
                "Please describe the business in more detail.")

    os.makedirs(PROJECTS_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    slug = re.sub(r"[^a-z0-9]+", "-", topic.lower()).strip("-")[:40] or "business"
    project_id = f"{timestamp}_{slug}"
    project = {
        "id": project_id,
        "idea": topic,
        "status": "ready",
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "tasks": tasks,
        "approval_policy": (
            "Banking, payment, wallet, card, transfer, investment, credential, "
            "and financial-account actions are blocked permanently. Approval "
            "is required for other external, private, legal, publishing, or "
            "irreversible actions."
        ),
    }
    path = os.path.join(PROJECTS_DIR, f"{project_id}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(project, f, indent=2, ensure_ascii=False)

    ready = sum(task["status"] == "ready" for task in tasks)
    approvals = len(tasks) - ready
    return (
        f"Business execution project created for '{topic}', Sir Gerald — saved to {path}. "
        f"I prepared {len(tasks)} tasks: {ready} safe local tasks are queued and "
        f"{approvals} require your approval before any outside action."
    )


def _load_business_projects():
    if not os.path.isdir(PROJECTS_DIR):
        return []
    projects = []
    for filename in os.listdir(PROJECTS_DIR):
        if not filename.endswith(".json"):
            continue
        path = os.path.join(PROJECTS_DIR, filename)
        try:
            with open(path, encoding="utf-8") as f:
                project = json.load(f)
            project["_path"] = path
            projects.append(project)
        except (OSError, ValueError):
            continue
    return sorted(projects, key=lambda item: item.get("created_at", ""), reverse=True)


def _latest_business_project():
    projects = _load_business_projects()
    return projects[0] if projects else None


def _save_business_project(project):
    path = project.pop("_path", None)
    if not path:
        path = os.path.join(PROJECTS_DIR, f"{project['id']}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(project, f, indent=2, ensure_ascii=False)
    project["_path"] = path


def _task_number(user_input):
    match = re.search(r"\btask\s+(\d+)\b", user_input.lower())
    return int(match.group(1)) if match else None


def _format_task(task, number):
    return f"{number}. [{task.get('status', 'unknown')}] {task.get('description', '')}"


def handle_business_tasks(user_input):
    project = _latest_business_project()
    if not project:
        return "There are no business projects yet, Sir Gerald. Start one with 'execute business idea for ...'."

    tasks = project.get("tasks", [])
    pending = [
        (index, task) for index, task in enumerate(tasks, 1)
        if task.get("status") in ("blocked_financial", "pending_approval", "approved", "ready")
    ]
    if not pending:
        return f"All tasks for '{project.get('idea', 'the latest business')}' are recorded as complete or rejected, Sir Gerald."
    lines = [_format_task(task, index) for index, task in pending]
    return f"Latest business project: {project.get('idea', 'unknown')}\n" + "\n".join(lines)


def handle_business_task_update(user_input):
    project = _latest_business_project()
    number = _task_number(user_input)
    if not project:
        return "There are no business projects to update, Sir Gerald."
    if number is None:
        return "Which task number should I update, Sir Gerald? Try: approve business task 2."

    tasks = project.get("tasks", [])
    if number < 1 or number > len(tasks):
        return f"Task {number} does not exist in the latest business project, Sir Gerald."
    task = tasks[number - 1]
    lower = user_input.lower()
    if task.get("risk") == "blocked_financial":
        return (f"Task {number} is permanently blocked because it involves money, "
                "banking, payment systems, or financial credentials, Sir Gerald. "
                "JARVIS has no access to those systems.")
    if "approve" in lower:
        if task.get("risk") != "approval_required":
            return f"Task {number} is already safe to perform or record, Sir Gerald."
        task["status"] = "approved"
        task["approved_at"] = datetime.now().isoformat(timespec="seconds")
        _save_business_project(project)
        return (f"Task {number} is approved in the queue, Sir Gerald. "
                "No external action was performed.")
    if "reject" in lower:
        task["status"] = "rejected"
        task["rejected_at"] = datetime.now().isoformat(timespec="seconds")
        _save_business_project(project)
        return f"Task {number} was rejected and will not be performed, Sir Gerald."
    if "complete" in lower or "done" in lower:
        if task.get("risk") == "approval_required" and task.get("status") != "approved":
            return f"Task {number} still requires approval before it can be recorded as complete, Sir Gerald."
        task["status"] = "completed"
        task["completed_at"] = datetime.now().isoformat(timespec="seconds")
        _save_business_project(project)
        return f"Task {number} was recorded as complete, Sir Gerald."
    return "I need approve, reject, or complete with the task number, Sir Gerald."


register_skill(
    name="business_research",
    triggers=["research business idea", "market research on", "market research for"],
    handler=handle_business_research,
    permission_level="safe",
)

register_skill(
    name="business_execution",
    triggers=["execute business idea", "execute business", "start business"],
    handler=handle_business_execution,
    permission_level="safe",
)

register_skill(
    name="business_tasks",
    triggers=[
        "show my business tasks", "business task status", "business tasks",
        "what business tasks", "waiting for approval", "business approvals",
    ],
    handler=handle_business_tasks,
    permission_level="safe",
)

register_skill(
    name="business_task_update",
    triggers=[
        "approve business task", "reject business task", "complete business task", "mark business task",
        "approve task", "reject task", "complete task", "mark task",
    ],
    handler=handle_business_task_update,
    permission_level="safe",
)

register_skill(
    name="business_ideas",
    triggers=["business ideas for", "brainstorm business ideas", "give me business ideas"],
    handler=handle_business_ideas,
    permission_level="safe",
)

register_skill(
    name="business_proposal",
    triggers=["draft a proposal", "write a freelance proposal", "write a proposal for"],
    handler=handle_business_proposal,
    permission_level="safe",
)
