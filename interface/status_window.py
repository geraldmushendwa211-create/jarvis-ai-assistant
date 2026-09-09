import tkinter as tk
import threading
import queue
import json
from http.server import BaseHTTPRequestHandler, HTTPServer

_command_queue = queue.Queue()
_window = None
_status_label = None
_task_label = None

STATE_COLORS = {
    "IDLE": "#444444",
    "LISTENING": "#2ecc71",
    "THINKING": "#f1c40f",
    "EXECUTING": "#3498db",
    "SUCCESS": "#27ae60",
    "ERROR": "#e74c3c",
}

# Shared with the local state server below, so the 3D reactor interface
# (running in a browser) can read JARVIS's live state.
_current_state = {"state": "IDLE", "task_text": ""}


def set_state(state, task_text=""):
    """Call this from anywhere in main.py to update the window."""
    _command_queue.put((state, task_text))


def _apply_update():
    global _current_state
    try:
        while True:
            state, task_text = _command_queue.get_nowait()
            color = STATE_COLORS.get(state, "#444444")
            _status_label.config(text=state, bg=color)
            _task_label.config(text=task_text)
            _current_state = {"state": state, "task_text": task_text}
    except queue.Empty:
        pass
    _window.after(100, _apply_update)


def _run_window():
    global _window, _status_label, _task_label
    _window = tk.Tk()
    _window.title("J.A.R.V.I.S")
    _window.geometry("400x200")
    _window.configure(bg="#111111")

    title = tk.Label(_window, text="J.A.R.V.I.S", font=("Consolas", 20, "bold"), fg="white", bg="#111111")
    title.pack(pady=10)

    _status_label = tk.Label(_window, text="IDLE", font=("Consolas", 16, "bold"), fg="white", bg="#444444", width=20, height=2)
    _status_label.pack(pady=10)

    _task_label = tk.Label(_window, text="", font=("Consolas", 11), fg="#aaaaaa", bg="#111111", wraplength=360)
    _task_label.pack(pady=10)

    _window.after(100, _apply_update)
    _window.mainloop()


class _StateHandler(BaseHTTPRequestHandler):
    """Tiny local server so a browser page can read JARVIS's current state."""
    def do_GET(self):
        if self.path == "/state":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(_current_state).encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        pass  # keep the terminal quiet — don't log every poll request


def _run_state_server():
    server = HTTPServer(("localhost", 8765), _StateHandler)
    server.serve_forever()


def start():
    """Call this once at the top of main.py: opens the status window AND
    starts the local state server the 3D reactor interface reads from."""
    threading.Thread(target=_run_window, daemon=True).start()
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