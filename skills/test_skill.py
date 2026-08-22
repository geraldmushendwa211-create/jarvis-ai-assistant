from core.skill_manager import register_skill


def handle_test(user_input):
    return "Test skill activated successfully, Sir Gerald."


register_skill(
    name="test_skill",
    triggers=["activate test skill"],
    handler=handle_test,
    permission_level="safe",
)