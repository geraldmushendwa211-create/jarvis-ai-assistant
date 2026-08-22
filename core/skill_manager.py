_skills = []


def register_skill(name, triggers, handler, permission_level="approval_required"):
    """
    name: short skill name, e.g. "roblox_creator"
    triggers: list of phrases that activate this skill, e.g. ["make a roblox rant"]
    handler: function to call, receives (user_input) and returns a spoken reply string
    permission_level: from core.permissions (safe / approval_required / restricted)
    """
    _skills.append({
        "name": name,
        "triggers": [t.lower() for t in triggers],
        "handler": handler,
        "permission_level": permission_level,
    })


def find_matching_skill(user_input):
    text = user_input.lower()
    for skill in _skills:
        for trigger in skill["triggers"]:
            if trigger in text:
                return skill
    return None


def list_skills():
    return [s["name"] for s in _skills]