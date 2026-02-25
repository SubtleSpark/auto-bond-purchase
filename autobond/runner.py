from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

from .config import load_config
from .notifier import send_pushplus
from .purchaser import EastmoneyPurchaser, launch_browser


def run() -> None:
    load_dotenv()
    config = load_config()

    print(f"浏览器: {config.browser}, Headless: {config.headless}")
    print(f"用户列表: {[user.account for user in config.users]}")

    with sync_playwright() as playwright:
        browser = launch_browser(playwright, config.browser, config.headless)
        purchaser = EastmoneyPurchaser(browser, config)

        try:
            for user in config.users:
                try:
                    result = purchaser.run_for_user(user)
                    send_pushplus(result, user.account, config.pushplus_token)
                except Exception as exc:
                    message = f"打新债失败，{normalize_message(str(exc))}"
                    send_pushplus(message, user.account, config.pushplus_token)
        finally:
            browser.close()


def normalize_message(text: str) -> str:
    return " ".join(text.replace("\r", " ").replace("\n", " ").split())
