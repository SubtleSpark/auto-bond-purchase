import re
from datetime import datetime
from pathlib import Path
from typing import Optional

from playwright.sync_api import Browser, Locator, Page, Playwright, TimeoutError as PlaywrightTimeoutError

from captcha import CaptchaRecognizer

from .config import AppConfig, UserCredential

LOGIN_URL = "https://jywg.18.cn/Login?el=1&clear=&returl=%2fTrade%2fBuy"

_recognizer: Optional[CaptchaRecognizer] = None


def get_recognizer() -> CaptchaRecognizer:
    global _recognizer
    if _recognizer is None:
        _recognizer = CaptchaRecognizer()
    return _recognizer


def launch_browser(playwright: Playwright, browser_name: str, headless: bool) -> Browser:
    launch_args = ["--disable-dev-shm-usage"]
    if headless:
        launch_args.append("--no-sandbox")

    if browser_name in {"chromium", ""}:
        return playwright.chromium.launch(headless=headless, args=launch_args)
    if browser_name in {"chrome", "google-chrome"}:
        return playwright.chromium.launch(headless=headless, channel="chrome", args=launch_args)
    if browser_name in {"edge", "msedge"}:
        return playwright.chromium.launch(headless=headless, channel="msedge", args=launch_args)

    raise ValueError("环境变量 BROWSER 仅支持 chromium/chrome/edge")


class EastmoneyPurchaser:
    def __init__(self, browser: Browser, config: AppConfig):
        self.browser = browser
        self.config = config

    def run_for_user(self, user: UserCredential) -> str:
        last_error: Optional[Exception] = None

        for attempt in range(1, self.config.flow_retries + 1):
            context = self.browser.new_context(viewport={"width": 1920, "height": 1080})
            page = context.new_page()
            try:
                print(f"[{user.account}] 开始执行，第 {attempt}/{self.config.flow_retries} 次")
                return self._run_once(page, user)
            except Exception as exc:
                last_error = exc
                self._save_error_screenshot(page, user.account, attempt)
                print(f"[{user.account}] 第 {attempt} 次失败: {exc}")
            finally:
                context.close()

        if last_error is None:
            raise RuntimeError("未知错误")
        raise RuntimeError(str(last_error))

    def _run_once(self, page: Page, user: UserCredential) -> str:
        self._goto_login_with_retry(page)

        if self._is_non_trade_day(page):
            return "目前不能打新债"

        page.locator("#txtZjzh").fill(user.account, timeout=self.config.timeout_ms)
        page.locator("#txtPwd").fill(user.password, timeout=self.config.timeout_ms)

        captcha_code = self._recognize_captcha_with_retry(page)
        page.locator("#txtValidCode").fill(captcha_code, timeout=self.config.timeout_ms)
        page.locator("#btnConfirm").click(timeout=self.config.timeout_ms)

        self._safe_click(page.locator(".vbtn-confirm"), timeout_ms=1500)

        self._click_menu(page, "新股新债")
        self._click_menu(page, "新债批量申购")

        if not self._has_purchasable_rows(page):
            return "当前没有可申购的债券"

        if not self._select_all(page):
            return "当前没有可申购的债券"

        self._click_menu(page, "批量申购")

        if self._has_no_purchase_dialog(page):
            self._safe_click(page.locator("#btnCxcConfirm"), timeout_ms=2000)
            return "当前没有可申购的债券"

        confirm = page.locator("#btnConfirm:visible").first
        try:
            confirm.wait_for(state="visible", timeout=3000)
        except PlaywrightTimeoutError:
            dialog_message = self._read_dialog_message(page)
            if dialog_message:
                self._safe_click(page.locator("#btnCxcConfirm"), timeout_ms=2000)
                if is_no_purchase_message(dialog_message):
                    return "当前没有可申购的债券"
                return clean_dialog_text(dialog_message)
            return "当前没有可申购的债券"

        confirm.click(timeout=self.config.timeout_ms)
        dialog_text = page.locator("#Cxc_Dialog").inner_text(timeout=self.config.timeout_ms)
        return clean_dialog_text(dialog_text)

    def _goto_login_with_retry(self, page: Page) -> None:
        last_error: Optional[Exception] = None
        for attempt in range(1, 4):
            try:
                page.goto(LOGIN_URL, wait_until="domcontentloaded", timeout=self.config.timeout_ms)
                return
            except Exception as exc:
                last_error = exc
                if attempt < 3:
                    page.wait_for_timeout(1000 * attempt)

        if last_error is None:
            raise RuntimeError("登录页加载失败")
        raise last_error

    def _is_non_trade_day(self, page: Page) -> bool:
        try:
            page.locator("button.btn-orange.vbtn-confirm").first.wait_for(state="visible", timeout=1500)
            return True
        except PlaywrightTimeoutError:
            return False

    def _recognize_captcha_with_retry(self, page: Page) -> str:
        recognizer = get_recognizer()
        captcha = page.locator("#imgValidCode")

        for attempt in range(1, self.config.captcha_retries + 1):
            try:
                image_bytes = captcha.screenshot(type="png", timeout=self.config.timeout_ms)
                code = recognizer.recognize_from_bytes(image_bytes)
                print(f"验证码识别结果 (第{attempt}次): {code}")
                if re.fullmatch(r"\d{4}", code):
                    return code
                raise ValueError(f"识别结果格式异常: {code}")
            except Exception as exc:
                print(f"验证码识别失败 (第{attempt}次): {exc}")
                if attempt >= self.config.captcha_retries:
                    break
                captcha.click(timeout=self.config.timeout_ms)
                page.wait_for_timeout(500)

        raise RuntimeError(f"验证码识别失败，已重试 {self.config.captcha_retries} 次")

    def _click_menu(self, page: Page, text: str) -> None:
        page.locator(f"a:has-text('{text}'):visible").first.click(timeout=self.config.timeout_ms)

    def _select_all(self, page: Page) -> bool:
        select_all = page.locator("#chk_all")
        try:
            select_all.scroll_into_view_if_needed(timeout=self.config.timeout_ms)
            select_all.click(timeout=self.config.timeout_ms)
            page.wait_for_timeout(300)
            return select_all.is_checked()
        except Exception:
            return False

    def _read_dialog_message(self, page: Page) -> str:
        dialog = page.locator("#Cxc_Dialog:visible").first
        try:
            return dialog.inner_text(timeout=1500)
        except Exception:
            return ""

    def _has_purchasable_rows(self, page: Page) -> bool:
        table_body = page.locator("#tableBody")
        try:
            table_body.wait_for(state="attached", timeout=3000)
        except PlaywrightTimeoutError:
            return False

        rows = table_body.locator("tr")
        if rows.count() == 0:
            return False

        first_text = " ".join(rows.first.inner_text().split())
        if "暂无数据" in first_text:
            return False

        return True

    def _has_no_purchase_dialog(self, page: Page) -> bool:
        try:
            page.locator("#Cxc_Dialog:visible").first.wait_for(state="visible", timeout=2000)
        except PlaywrightTimeoutError:
            return False

        message = self._read_dialog_message(page)
        return is_no_purchase_message(message)

    def _safe_click(self, locator: Locator, timeout_ms: int) -> bool:
        try:
            locator.first.click(timeout=timeout_ms)
            return True
        except Exception:
            return False

    def _save_error_screenshot(self, page: Page, account: str, attempt: int) -> None:
        screenshot_dir = Path(self.config.screenshot_dir)
        screenshot_dir.mkdir(parents=True, exist_ok=True)

        suffix = re.sub(r"[^0-9A-Za-z_-]", "_", account[-4:] if len(account) >= 4 else account)
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        screenshot_path = screenshot_dir / f"{timestamp}-{suffix}-attempt{attempt}.png"

        try:
            page.screenshot(path=str(screenshot_path), full_page=True)
            print(f"异常截图已保存: {screenshot_path}")
        except Exception:
            pass


def is_no_purchase_message(message: str) -> bool:
    text = " ".join(message.replace("\r", " ").replace("\n", " ").split())
    return any(
        keyword in text
        for keyword in (
            "请选择需申购的新债",
            "当前没有可申购的债券",
            "委托数量不能",
            "申购数量不能",
            "可申购数量为0",
            "请输入",
        )
    )


def clean_dialog_text(text: str) -> str:
    cleaned = " ".join(text.replace("\r", " ").replace("\n", " ").split())
    if cleaned.startswith("x "):
        cleaned = cleaned[2:]
    if cleaned.endswith("确定"):
        cleaned = cleaned[:-2]
    return cleaned.strip()
