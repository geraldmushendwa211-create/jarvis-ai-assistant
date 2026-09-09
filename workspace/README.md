# workspace/

Working folders for JARVIS. Generated and user-supplied media lives here and is
**not committed to git** (see `.gitignore`) — only this structure and a few
example scripts are tracked.

| Folder | Purpose |
|---|---|
| `footage/` | Drop gameplay recordings here (`.mp4`, `.mov`, `.mkv`, `.avi`). The `roblox_creator` skill picks one automatically, or say `use <filename>` to choose. |
| `music/` | Background music. `background_music.mp3` is used by default and auto-leveled under the voiceover. Music is optional — the pipeline still succeeds without it. |
| `sfx/` | Sound effects for future skills (memes, transitions). Not wired into the pipeline yet. |
| `audio/` | Generated voiceovers (`voiceover_*.mp3`) and trimmed versions. Safe to delete. |
| `scripts/` | Generated rant scripts (`script_*.txt`) and video ideas (`ideas_*.txt`). A few examples are tracked in git. |
| `output/` | Finished videos (`output_final_*.mp4`), captions (`.ass`), and `latest.txt` pointing at the newest render. Safe to delete. |
| `projects/` | One JSON job ticket per video attempt (topic, niche, stage history, paths). The seed of the content library. Safe to delete. |

Typical flow: say **"make a Roblox rant about admin abusers"** → script lands in
`scripts/`, voiceover in `audio/`, final vertical video in `output/`.
