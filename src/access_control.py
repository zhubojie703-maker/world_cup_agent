from __future__ import annotations


PUBLIC_TABS = ["Agent", "Privacy"]
ADMIN_TABS = ["Agent", "Dashboard", "DataAgent", "Privacy"]


def is_admin_authenticated(input_passcode: str, expected_passcode: str) -> bool:
    if not expected_passcode:
        return False
    return input_passcode.strip() == expected_passcode


def visible_tabs(is_admin: bool) -> list[str]:
    return ADMIN_TABS if is_admin else PUBLIC_TABS


def should_show_admin_gate(query_params: dict) -> bool:
    value = query_params.get("admin", "")
    if isinstance(value, list):
        value = value[0] if value else ""
    return str(value) == "1"
