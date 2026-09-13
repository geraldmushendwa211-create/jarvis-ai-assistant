"""Central registry for JARVIS skills.

A skill is a voice-triggered capability: a name, a list of trigger phrases,
a handler function, and a permission level (see core.permissions).

Skills self-register on import by calling :func:`register_skill` at the
bottom of their module, and :func:`load_all_skills` imports every module in
the ``skills/`` package so ``brain/main.py`` never needs to know each skill
by name.
"""

import importlib
import inspect
import pkgutil

import skills

_skills = []


def register_skill(name, triggers, handler, permission_level="approval_required"):
    """
    name: short skill name, e.g. "roblox_creator"
    triggers: list of phrases that activate this skill, e.g. ["make a roblox rant"]
    handler: function to call. May accept either ``(user_input)`` or
        ``(user_input, gemini_client=...)`` — see :func:`call_skill`.
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


def call_skill(skill, user_input, gemini_client=None):
    """Invoke a skill handler, tolerating both supported signatures.

    Handlers that need the AI model declare ``(user_input, gemini_client=None)``;
    simple handlers just declare ``(user_input)``. This helper inspects the
    signature and only passes what the handler accepts, so neither style crashes.
    """
    handler = skill["handler"]
    try:
        params = inspect.signature(handler).parameters
    except (TypeError, ValueError):
        # Un-inspectable callable — fall back to the simple one-arg call.
        return handler(user_input)
    if "gemini_client" in params:
        return handler(user_input, gemini_client=gemini_client)
    return handler(user_input)


def load_all_skills():
    """Import every module in the ``skills/`` package so each one registers.

    A skill whose third-party dependencies aren't installed (e.g. the video
    skills on a machine without moviepy) is skipped with a warning instead of
    crashing JARVIS at startup. Returns the list of loaded skill names.
    """
    loaded = []
    for module_info in pkgutil.iter_modules(skills.__path__):
        module_name = module_info.name
        if module_name.startswith("_"):
            continue
        try:
            importlib.import_module(f"skills.{module_name}")
            loaded.append(module_name)
        except ImportError as e:
            print(f"[JARVIS] Skipping skill module 'skills.{module_name}': "
                  f"missing dependency ({e}). Run: pip install -r requirements.txt")
    return loaded
