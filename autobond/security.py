from collections.abc import Iterable


def account_label(index: int) -> str:
    return f"账户#{index}"


def redact_secrets(text: str, secrets: Iterable[str]) -> str:
    redacted = text
    values = {value for value in secrets if value}
    for value in sorted(values, key=len, reverse=True):
        redacted = redacted.replace(value, "<redacted>")
    return redacted
