SAFE = "safe"
APPROVAL_REQUIRED = "approval_required"
RESTRICTED = "restricted"


def request_permission(action, reason, level=APPROVAL_REQUIRED):
    """
    Checks whether an action is allowed to run.
    Returns True if JARVIS may proceed, False if not.
    """
    if level == SAFE:
        return True

    if level == RESTRICTED:
        print(f"[JARVIS] This action is restricted and cannot be performed: {action}")
        return False

    # APPROVAL_REQUIRED
    print("\nJARVIS PERMISSION REQUEST")
    print(f"Action: {action}")
    print(f"Reason: {reason}")
    answer = input("Approve? (yes/no): ").strip().lower()
    return answer in ("yes", "y")


if __name__ == "__main__":
    allowed = request_permission(
        action="Upload roblox_rant_07.mp4 to YouTube",
        reason="You asked me to publish the finished video.",
        level=APPROVAL_REQUIRED,
    )
    print("Allowed:", allowed)