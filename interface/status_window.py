import tkinter as tk
import threading
import queue
import json
import os
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse

_command_queue = queue.Queue()
_window = None
_status_label = None
_task_label = None
_state_code = None
_reactor_canvas = None
_reactor_items = []
_accent = "#1de4f2"
_animation_tick = 0

STATE_COLORS = {
    "IDLE": "#1de4f2",
    "LISTENING": "#66e7a8",
    "THINKING": "#e7b85d",
    "EXECUTING": "#57a7ff",
    "SUCCESS": "#8ce9d2",
    "ERROR": "#e87777",
}

# Shared with the local state server below, so the 3D reactor interface
# (running in a browser) can read JARVIS's live state.
_current_state = {
    "state": "IDLE",
    "task_text": "",
    "updated_at": datetime.now().isoformat(timespec="seconds"),
}


def set_state(state, task_text=""):
    """Call this from anywhere in main.py to update the window."""
    global _current_state
    _current_state = {
        "state": state,
        "task_text": task_text,
        "updated_at": datetime.now().isoformat(timespec="seconds"),
    }
    _command_queue.put((state, task_text))


def _apply_update():
    global _current_state, _accent
    try:
        while True:
            state, task_text = _command_queue.get_nowait()
            color = STATE_COLORS.get(state, "#1de4f2")
            _accent = color
            _status_label.config(text=state, fg=color)
            _state_code.config(text=f"STATE // {state}", fg=color)
            _task_label.config(text=task_text)
            _reactor_canvas.itemconfig(_reactor_items[0], outline=color)
            _reactor_canvas.itemconfig(_reactor_items[1], outline=color)
            _reactor_canvas.itemconfig(_reactor_items[2], fill=color)
            _reactor_canvas.itemconfig(_reactor_items[3], outline=color)
            _current_state.update({
                "state": state,
                "task_text": task_text,
                "updated_at": datetime.now().isoformat(timespec="seconds"),
            })
    except queue.Empty:
        pass
    _window.after(100, _apply_update)


def _animate_reactor():
    global _animation_tick
    if _reactor_canvas is None:
        return
    _animation_tick = (_animation_tick + 3) % 360
    _reactor_canvas.itemconfig(_reactor_items[1], start=_animation_tick)
    _reactor_canvas.itemconfig(_reactor_items[3], start=(-_animation_tick * 2) % 360)
    _window.after(45, _animate_reactor)


def _panel(parent, title, row, column, width=260):
    frame = tk.Frame(parent, bg="#071722", highlightbackground="#164557", highlightthickness=1)
    frame.grid(row=row, column=column, sticky="nsew", padx=8, pady=8)
    frame.grid_propagate(False)
    frame.config(width=width, height=160)
    tk.Label(frame, text=title, font=("Consolas", 9, "bold"), fg="#1de4f2", bg="#071722").pack(anchor="w", padx=14, pady=(12, 5))
    return frame


def _run_window():
    global _window, _status_label, _task_label, _state_code, _reactor_canvas, _reactor_items
    _window = tk.Tk()
    _window.title("J.A.R.V.I.S // Command Deck")
    _window.geometry("1040x700")
    _window.minsize(820, 560)
    _window.configure(bg="#020b16")

    header = tk.Frame(_window, bg="#020b16")
    header.pack(fill="x", padx=28, pady=(22, 8))
    tk.Label(header, text="J", font=("Consolas", 22, "bold"), fg="#1de4f2", bg="#020b16", width=3, height=1, highlightbackground="#1de4f2", highlightthickness=1).pack(side="left")
    brand = tk.Frame(header, bg="#020b16")
    brand.pack(side="left", padx=12)
    tk.Label(brand, text="J.A.R.V.I.S.", font=("Consolas", 24, "bold"), fg="#d8fbff", bg="#020b16").pack(anchor="w")
    tk.Label(brand, text="PERSONAL ARTIFICIAL INTELLIGENCE // LOCAL COMMAND DECK", font=("Consolas", 9), fg="#6996a7", bg="#020b16").pack(anchor="w")
    tk.Label(header, text="● SYSTEM LINKED\nLOCAL OPERATION", font=("Consolas", 9), justify="right", fg="#66e7a8", bg="#020b16").pack(side="right")
    tk.Frame(_window, bg="#164557", height=1).pack(fill="x", padx=28)

    content = tk.Frame(_window, bg="#020b16")
    content.pack(fill="both", expand=True, padx=20, pady=10)
    content.grid_columnconfigure(1, weight=1)
    content.grid_rowconfigure(0, weight=1)

    left = tk.Frame(content, bg="#020b16", width=220)
    left.grid(row=0, column=0, sticky="ns")
    left.grid_propagate(False)
    telemetry = _panel(left, "SYSTEM TELEMETRY", 0, 0, 210)
    for label, value in (("VOICE OUTPUT", "RYAN / EN-GB"), ("INPUT", "REALTEK MIC"), ("NETWORK", "AVAILABLE"), ("MEMORY", "TRIMMED")):
        row = tk.Frame(telemetry, bg="#071722")
        row.pack(fill="x", padx=14, pady=3)
        tk.Label(row, text=label, font=("Consolas", 8), fg="#6996a7", bg="#071722").pack(side="left")
        tk.Label(row, text=value, font=("Consolas", 8), fg="#d8fbff", bg="#071722").pack(side="right")
    safety = _panel(left, "SAFETY PROTOCOL", 1, 0, 210)
    for label, value, color in (("FINANCIAL ACCESS", "BLOCKED", "#e87777"), ("OUTSIDE ACTIONS", "APPROVAL", "#e7b85d"), ("LOCAL WORK", "AVAILABLE", "#66e7a8")):
        tk.Label(safety, text=f"{label}\n{value}", justify="left", font=("Consolas", 8), fg=color, bg="#071722").pack(anchor="w", padx=14, pady=5)

    center = tk.Frame(content, bg="#020b16")
    center.grid(row=0, column=1, sticky="nsew")
    center.grid_rowconfigure(0, weight=1)
    center.grid_columnconfigure(0, weight=1)
    _reactor_canvas = tk.Canvas(center, bg="#020b16", highlightthickness=0)
    _reactor_canvas.grid(row=0, column=0, sticky="nsew")
    _reactor_canvas.update_idletasks()
    cx, cy = 250, 205
    _reactor_items = [
        _reactor_canvas.create_oval(cx - 160, cy - 160, cx + 160, cy + 160, outline="#1de4f2", width=1),
        _reactor_canvas.create_arc(cx - 135, cy - 135, cx + 135, cy + 135, start=0, extent=85, outline="#1de4f2", width=3),
        _reactor_canvas.create_oval(cx - 70, cy - 70, cx + 70, cy + 70, fill="#1de4f2", outline="#d8fbff", width=2),
        _reactor_canvas.create_arc(cx - 100, cy - 100, cx + 100, cy + 100, start=180, extent=120, outline="#1de4f2", width=2),
    ]
    _reactor_canvas.create_text(cx, 35, text="NEURAL CORE // ADAPTIVE", fill="#1de4f2", font=("Consolas", 10, "bold"))
    _reactor_canvas.create_text(cx, 375, text="LOCAL SIGNAL  •  READY FOR INSTRUCTION", fill="#6996a7", font=("Consolas", 9))

    right = tk.Frame(content, bg="#020b16", width=240)
    right.grid(row=0, column=2, sticky="ns")
    right.grid_propagate(False)
    directive = _panel(right, "CURRENT DIRECTIVE", 0, 0, 230)
    _state_code = tk.Label(directive, text="STATE // IDLE", font=("Consolas", 11, "bold"), fg="#1de4f2", bg="#071722")
    _state_code.pack(anchor="w", padx=14, pady=(4, 14))
    _status_label = tk.Label(directive, text="IDLE", font=("Consolas", 20, "bold"), fg="#1de4f2", bg="#071722")
    _status_label.pack(anchor="w", padx=14, pady=4)
    _task_label = tk.Label(directive, text="Standing by for your next instruction.", font=("Consolas", 9), fg="#d8fbff", bg="#071722", wraplength=195, justify="left")
    _task_label.pack(anchor="w", padx=14, pady=(8, 14))
    commands = _panel(right, "COMMAND MEMORY", 1, 0, 230)
    tk.Label(commands, text="CHECK SYSTEM\nSHOW MY BUSINESS TASKS\nWHAT HAVE YOU MADE?\nQUIT", font=("Consolas", 8), fg="#6996a7", bg="#071722", justify="left").pack(anchor="w", padx=14, pady=5)

    footer = tk.Label(_window, text="JARVIS // DESKTOP MODE     |     FINANCIAL ACCESS BLOCKED     |     EXTERNAL ACTIONS REQUIRE APPROVAL", font=("Consolas", 8), fg="#6996a7", bg="#020b16")
    footer.pack(fill="x", padx=28, pady=(4, 16))

    _window.after(100, _apply_update)
    _window.after(100, _animate_reactor)
    _window.mainloop()


class _StateHandler(BaseHTTPRequestHandler):
    """Local read-only dashboard server for JARVIS's current state."""
    def do_GET(self):
        route = urlparse(self.path).path
        if route in ("/", "/index.html"):
            path = os.path.join(os.path.dirname(__file__), "..", "web", "index.html")
            try:
                with open(path, encoding="utf-8") as page:
                    body = page.read().encode("utf-8")
            except OSError:
                self.send_response(404)
                self.end_headers()
                return
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        elif route == "/state":
            body = json.dumps(_current_state).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        pass  # keep the terminal quiet — don't log every poll request


def _run_state_server():
    server = HTTPServer(("localhost", 8765), _StateHandler)
    server.serve_forever()


def start(enable_web=False):
    """Start the native status window and optionally the browser state server."""
    threading.Thread(target=_run_window, daemon=True).start()
    if enable_web:
        threading.Thread(target=_run_state_server, daemon=True).start()


if __name__ == "__main__":
    start()
    import time
    time.sleep(2)
    set_state("LISTENING")
    time.sleep(2)
    set_state("THINKING", "Generating Roblox rant script...")
    time.sleep(2)
    set_state("SUCCESS", "Script complete!")
    time.sleep(5)