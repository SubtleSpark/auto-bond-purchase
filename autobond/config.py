import os
from dataclasses import dataclass


@dataclass(frozen=True)
class UserCredential:
    account: str
    password: str


@dataclass(frozen=True)
class AppConfig:
    users: list[UserCredential]
    pushplus_token: str
    headless: bool
    browser: str
    captcha_retries: int
    flow_retries: int
    timeout_ms: int
    screenshot_dir: str


def parse_users(users_str: str) -> list[UserCredential]:
    if not users_str:
        raise ValueError("环境变量 USERS 未设置，格式: 账号1:密码1,账号2:密码2")

    users: list[UserCredential] = []
    for pair in users_str.split(","):
        pair = pair.strip()
        if not pair:
            continue
        if ":" not in pair:
            raise ValueError(f"用户格式错误: {pair}，应为 账号:密码")
        account, password = pair.split(":", 1)
        users.append(UserCredential(account=account.strip(), password=password.strip()))

    if not users:
        raise ValueError("环境变量 USERS 为空，至少需要一个账号")
    return users


def parse_bool(value: str, default: bool = False) -> bool:
    if value is None:
        return default
    value = value.strip().lower()
    if value in {"1", "true", "yes", "on"}:
        return True
    if value in {"0", "false", "no", "off"}:
        return False
    return default


def parse_int(value: str, default: int, minimum: int = 1) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = default
    return max(parsed, minimum)


def load_config() -> AppConfig:
    users = parse_users(os.environ.get("USERS", ""))

    return AppConfig(
        users=users,
        pushplus_token=os.environ.get("PUSHPLUS_TOKEN", "").strip(),
        headless=parse_bool(os.environ.get("HEADLESS"), default=False),
        browser=os.environ.get("BROWSER", "chromium").strip().lower(),
        captcha_retries=parse_int(os.environ.get("CAPTCHA_RETRIES"), default=3),
        flow_retries=parse_int(os.environ.get("FLOW_RETRIES"), default=2),
        timeout_ms=parse_int(os.environ.get("TIMEOUT_MS"), default=30000, minimum=3000),
        screenshot_dir=os.environ.get("SCREENSHOT_DIR", "artifacts/screenshots").strip(),
    )
