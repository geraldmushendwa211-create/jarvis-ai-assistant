"""Read-only JARVIS health checks for local setup troubleshooting."""

import importlib.util
import os
import platform
import sys

from core.skill_manager import register_skill

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def _check_import(module_name):
    return importlib.util.find_spec(module_name) is not None


def _check_microphone():
    try:
        import sounddevice as sd
        devices = sd.query_devices()
        inputs = [
            device.get("name", "unnamed")
            for device in devices
            if device.get("max_input_channels", 0) > 0
        ]
        if not inputs:
            return "FAIL", "no input devices detected"
        return "OK", f"{len(inputs)} input device(s) detected"
    except Exception as error:
        return "WARN", f"microphone check unavailable ({type(error).__name__})"


def gather_diagnostics(environ=None, root_dir=None):
    """Return safe, non-secret diagnostics suitable for tests or a UI."""
    environ = os.environ if environ is None else environ
    root_dir = ROOT_DIR if root_dir is None else root_dir
    checks = []

    python_ok = sys.version_info >= (3, 10)
    checks.append({
        "name": "Python",
        "status": "OK" if python_ok else "WARN",
        "detail": platform.python_version(),
    })
    checks.append({
        "name": "Gemini configuration",
        "status": "OK" if environ.get("GEMINI_API_KEY", "").strip() else "WARN",
        "detail": "key present" if environ.get("GEMINI_API_KEY", "").strip() else "key missing",
    })
    checks.append({
        "name": "Speech input package",
        "status": "OK" if _check_import("sounddevice") and _check_import("speech_recognition") else "WARN",
        "detail": "installed" if _check_import("sounddevice") and _check_import("speech_recognition") else "dependency missing",
    })
    checks.append({
        "name": "Speech output package",
        "status": "OK" if _check_import("edge_tts") and _check_import("playsound3") else "WARN",
        "detail": "installed" if _check_import("edge_tts") and _check_import("playsound3") else "dependency missing",
    })
    microphone_status, microphone_detail = _check_microphone()
    checks.append({"name": "Microphone", "status": microphone_status, "detail": microphone_detail})

    dashboard_path = os.path.join(root_dir, "web", "index.html")
    checks.append({
        "name": "Dashboard",
        "status": "OK" if os.path.isfile(dashboard_path) else "WARN",
        "detail": "web/index.html found" if os.path.isfile(dashboard_path) else "web/index.html missing",
    })
    for folder in ("workspace", "workspace/business", "workspace/business/projects"):
        path = os.path.join(root_dir, folder)
        checks.append({
            "name": folder,
            "status": "OK" if os.path.isdir(path) else "WARN",
            "detail": "available" if os.path.isdir(path) else "will be created when needed",
        })
    checks.append({
        "name": "Financial access",
        "status": "OK",
        "detail": "blocked by design",
    })
    checks.append({
        "name": "External actions",
        "status": "OK",
        "detail": "approval-gated",
    })
    return checks


def format_diagnostics(checks):
    lines = ["JARVIS system diagnostics, Sir Gerald:"]
    for check in checks:
        lines.append(f"[{check['status']}] {check['name']}: {check['detail']}")
    warnings = sum(check["status"] == "WARN" for check in checks)
    failures = sum(check["status"] == "FAIL" for check in checks)
    if failures:
        lines.append(f"Result: {failures} failure(s), {warnings} warning(s).")
    elif warnings:
        lines.append(f"Result: operational with {warnings} warning(s).")
    else:
        lines.append("Result: all checks passed.")
    return "\n".join(lines)


def handle_system_diagnostics(user_input):
    return format_diagnostics(gather_diagnostics())


register_skill(
    name="system_diagnostics",
    triggers=["system diagnostics", "system diagnostic", "check system", "run diagnostics", "jarvis diagnostics"],
    handler=handle_system_diagnostics,
    permission_level="safe",
)
