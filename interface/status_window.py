import tkinter as tk
import threading
import queue

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


def set_state(state, task_text=""):
    """Call this from anywhere in main.py to update the window."""
    _command_queue.put((state, task_text))


def _apply_update():
    try:
        while True:
            state, task_text = _command_queue.get_nowait()
            color = STATE_COLORS.get(state, "#444444")
            _status_label.config(text=state, bg=color)
            _task_label.config(text=task_text)
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


def start():
    """Call this once at the top of main.py to open the window in the background."""
    thread = threading.Thread(target=_run_window, daemon=True)
    thread.start()


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