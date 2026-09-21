from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

from .config import load_config
from .notifier import send_pushplus
from .purchaser import EastmoneyPurchaser, launch_browser
from .security import account_label, redact_secrets


def run() -> None:
    load_dotenv()
    config = load_config()

    print(f"浏览器: {config.browser}, Headless: {config.headless}")
    print(f"已加载 {len(config.users)} 个账户")

    with sync_playwright() as playwright:
        browser = launch_browser(playwright, config.browser, config.headless)
        purchaser = EastmoneyPurchaser(browser, config)

        try:
            for index, user in enumerate(config.users, start=1):
                label = account_label(index)
                try:
                    result = purchaser.run_for_user(user, label)
                    message = f"[{label}] {result}"
                    send_pushplus(message, f"打新债结果-{label}", config.pushplus_token)
                except Exception as exc:
                    error = redact_secrets(
                        normalize_message(str(exc)),
                        (user.account, user.password, config.pushplus_token),
                    )
                    message = f"[{label}] 打新债失败，{error}"
                    send_pushplus(message, f"打新债结果-{label}", config.pushplus_token)
        finally:
            browser.close()


def normalize_message(text: str) -> str:
    return " ".join(text.replace("\r", " ").replace("\n", " ").split())
