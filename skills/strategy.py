"""Strategy skill: trends, research, and full video planning.

Commands:
    "what's trending in minecraft"   -> live topics for the niche
    "research black holes"           -> fact brief with sources
    "plan a video about black holes" -> research + ranked ideas + scored
        titles + fact-check, saved as a plan file + project ticket

Routing: "trend" -> trends, "plan" -> full plan, otherwise research.
"""

import os
import re
from datetime import datetime

from core import factcheck, hooks, research, trends
from core.niches import detect_niche
from core.project import VideoProject
from core.skill_manager import register_skill

SCRIPTS_DIR = "workspace/scripts"
MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash")

# Niches whose scripts get an automatic fact-check pass.
FACT_NICHES = ("education", "tech")


def _topic_after(text, keywords=("about", " on ")):
    lower = text.lower()
    for keyword in keywords:
        if keyword in lower:
            topic = text[lower.index(keyword) + len(keyword):].strip().strip("?\"'")
            if topic:
                return topic
    return ""


def _trending_reply(user_input):
    niche = detect_niche(user_input)
    topics = trends.discover_trends(niche.key)
    if not topics:
        return ("I couldn't reach any trend sources right now, Sir Gerald — "
                "the networks may be down or rate-limiting me. Try again in a "
                "bit, or name a topic and I'll plan a video around it.")
    lines = []
    for i, t in enumerate(topics[:5], 1):
        lines.append(f"{i}. {t['title']} — {t['comments']} comments on {t['source']}")
    return (f"Here are live {niche.label} topics, Sir Gerald: " + " ".join(lines) + " "
            f"Say 'plan a video about' one of them to turn it into a full plan.")


def _research_reply(user_input):
    topic = _topic_after(user_input) or user_input.strip() or "that"
    brief = research.research_topic(topic)
    if not brief["facts"]:
        return (f"I found no free sources on '{topic}', Sir Gerald. {brief['note']} "
                f"I can still draft from AI knowledge — say 'plan a video about {topic}'.")
    first_fact = brief["facts"][0]
    source = brief["sources"][0]["title"] if brief["sources"] else "unknown source"
    return (f"Here's the short version on {topic}, Sir Gerald: {first_fact} "
            f"Source: {source}. {len(brief['facts'])} facts from "
            f"{len(brief['sources'])} sources in total.")


def _generate_ideas(topic, niche, gemini_client, count=3):
    prompt = (
        f"Brainstorm {count} YouTube Short ideas about: {topic}\n"
        f"Niche: {niche.label}. Tone: {niche.default_tone}.\n"
        "For EACH idea reply in exactly this format:\n"
        "Idea: <title concept>\nHook: <first spoken line>\n"
        "Difficulty: <easy|medium|hard>\nWhy: <one sentence on why it may work>\n"
        "Separate ideas with a line containing only ---"
    )
    response = gemini_client.models.generate_content(model=MODEL, contents=prompt)
    ideas = []
    for block in response.text.strip().split("---"):
        item = {}
        for line in block.strip().splitlines():
            match = re.match(
                r"\s*(?:\d+[\).\:\-]\s*)?(idea|hook|difficulty|why)\s*:\s*(.+)",
                line, re.IGNORECASE)
            if match:
                item[match.group(1).lower()] = match.group(2).strip()
        if item.get("idea"):
            ideas.append({
                "idea": item.get("idea", ""),
                "hook": item.get("hook", ""),
                "difficulty": item.get("difficulty", "medium"),
                "why": item.get("why", ""),
            })
    return ideas[:count]


def _write_plan_file(ticket, niche, brief, ideas, ranked_titles, flags):
    os.makedirs(SCRIPTS_DIR, exist_ok=True)
    path = os.path.join(SCRIPTS_DIR, f"plan_{ticket.id}.md")
    lines = [
        f"# Video plan: {ticket.topic}",
        f"- Niche: {niche.label} | Format: {ticket.format} | Ticket: {ticket.id}",
        f"- Planned: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "",
        "## Research",
        brief.get("summary") or "_No free sources returned facts — AI knowledge only._",
        "",
        "Sources:",
    ]
    for source in brief.get("sources", []):
        lines.append(f"- {source['title']} — {source['url']}")
    lines.append("")
    lines.append("## Ideas")
    for i, idea in enumerate(ideas, 1):
        lines.append(f"{i}. **{idea['idea']}** (difficulty: {idea['difficulty']})")
        lines.append(f"   Hook: _{idea['hook']}_")
        lines.append(f"   Why: {idea['why']}")
    if not ideas:
        lines.append("_Idea generation came back empty — retry the plan._")
    lines.append("")
    lines.append("## Titles (scored)")
    for title, score, _feedback in ranked_titles:
        lines.append(f"- ({score}/100) {title}")
    if flags:
        lines.append("")
        lines.append("## Fact-check flags (human look needed)")
        for flag in flags:
            lines.append(f"- L{flag['line']}: {flag['detail']}")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    return path


def _plan_reply(user_input, gemini_client):
    niche = detect_niche(user_input)
    topic = _topic_after(user_input)
    if not topic:
        return "What should I plan, Sir Gerald? Try: plan a video about black holes."
    if gemini_client is None:
        return "I need the AI model for planning, Sir Gerald. Something's misconfigured."

    ticket = VideoProject.new(topic, niche=niche.key, format="short")
    ticket.mark("planned", f"{niche.label} strategy")

    brief = research.research_topic(topic)
    ticket.research = brief
    ticket.save()  # persist early — research survives even if AI calls fail below

    ideas = _generate_ideas(topic, niche, gemini_client)
    ticket.ideas = ideas

    ranked_titles = hooks.generate_and_pick(topic, niche, gemini_client)
    ticket.titles = [{"title": t, "score": s} for t, s, _ in ranked_titles]

    flags = []
    if niche.key in FACT_NICHES:
        corpus = "\n".join([brief.get("summary", "")]
                           + [i["idea"] for i in ideas])
        flags = factcheck.check_text(corpus)
        ticket.fact_check = {"flags": flags, "note": factcheck.summarize(flags)}
    ticket.save()

    plan_path = _write_plan_file(ticket, niche, brief, ideas, ranked_titles, flags)
    ticket.plan_path = plan_path
    ticket.save()

    best = ranked_titles[0] if ranked_titles else ("(no titles generated)", 0, [])
    top_idea = ideas[0]["idea"] if ideas else "none — retry me"
    warn = f" {factcheck.summarize(flags)}" if niche.key in FACT_NICHES else ""
    return (
        f"Plan ready for '{topic}', Sir Gerald — saved to {plan_path}. "
        f"Top idea: {top_idea}. Best title ({best[1]} out of 100): {best[0]}. "
        f"Research: {len(brief['facts'])} facts from {len(brief['sources'])} sources.{warn}"
    )


def handle_strategy(user_input, gemini_client=None):
    lower = user_input.lower()
    if "trend" in lower:
        return _trending_reply(user_input)
    if "plan" in lower:
        return _plan_reply(user_input, gemini_client)
    return _research_reply(user_input)


register_skill(
    name="strategy",
    triggers=[
        "what's trending", "what is trending", "trending in", "trending",
        "research ",
        "plan a video", "plan me a video", "video plan", "content plan",
    ],
    handler=handle_strategy,
    permission_level="safe",
)
