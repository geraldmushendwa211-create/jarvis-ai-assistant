import os
from datetime import datetime

VAULT_PATH = os.path.join(os.path.dirname(__file__), "..", "JarvisMemory", "Conversations")

def save_to_obsidian(user_input, jarvis_reply):
    os.makedirs(VAULT_PATH, exist_ok=True)
    today = datetime.now().strftime("%Y-%m-%d")
    filepath = os.path.join(VAULT_PATH, f"{today}.md")
    timestamp = datetime.now().strftime("%H:%M")
    entry = f"\n### {timestamp}\n**Sir Gerald:** {user_input}\n\n**JARVIS:** {jarvis_reply}\n"
    with open(filepath, "a", encoding="utf-8") as f:
        f.write(entry)