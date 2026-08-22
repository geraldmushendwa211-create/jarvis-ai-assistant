import os
from datetime import datetime
from core.skill_manager import register_skill

SCRIPTS_DIR = "workspace/scripts"


def generate_script(topic, gemini_client):
    prompt = (
        f"Write a Roblox rant script for a YouTube Short about: {topic}\n\n"
        "Style rules:\n"
        "- Strong hook in the first line\n"
        "- Fast pacing, short sentences\n"
        "- Humor, exaggeration, relatability\n"
        "- Punchy, memorable ending\n"
        "- Target length: 30-60 seconds spoken aloud\n"
        "- Write ONLY the spoken narration text, no stage directions, no headers"
    )
    response = gemini_client.models.generate_content(
        model="gemini-3.5-flash-lite",
        contents=prompt,
    )
    return response.text.strip()


def handle_roblox_creator(user_input, gemini_client=None):
    lower = user_input.lower()
    if "about" in lower:
        topic = user_input[lower.index("about") + len("about"):].strip()
    else:
        topic = user_input

    if gemini_client is None:
        return "I need access to the AI model to write that script, Sir Gerald. Something's misconfigured."

    script_text = generate_script(topic, gemini_client)

    os.makedirs(SCRIPTS_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    filepath = os.path.join(SCRIPTS_DIR, f"script_{timestamp}.txt")
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(script_text)

    return f"Script complete, Sir Gerald. Here it is: {script_text}"


register_skill(
    name="roblox_creator",
    triggers=["make a roblox rant", "create a roblox rant", "roblox rant about"],
    handler=handle_roblox_creator,
    permission_level="safe",
)