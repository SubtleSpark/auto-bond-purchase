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

        self._open_new_stock_bond_menu(page)
        self._open_bond_batch_purchase_page(page)

        if not self._has_purchasable_rows(page):
            return "当前没有可申购的债券"

        if not self._select_all(page):
            # 这里不要降级成“无可申购”，否则会把页面结构变化误报成无债。
            raise RuntimeError("检测到可申购列表但全选失败，可能页面结构变化")

        self._click_batch_buy(page)

        dialog_message = self._wait_dialog_message(page, timeout_ms=2200)
        if dialog_message:
            normalized = normalize_text(dialog_message)
            if "请选择需申购的新债" in normalized:
                # 页面偶发“点了全选但实际没勾上”，这里做一次自动重试。
                self._safe_click(page.locator("#btnCxcConfirm"), timeout_ms=2000)
                if self._retry_select_and_batch_buy(page):
                    dialog_message = self._wait_dialog_message(page, timeout_ms=1800)
                    if dialog_message:
                        normalized = normalize_text(dialog_message)
                        self._safe_click(page.locator("#btnCxcConfirm"), timeout_ms=2000)
                        if "请选择需申购的新债" in normalized:
                            raise RuntimeError("检测到可申购列表但未成功勾选，可能页面结构变化")
                        if is_no_purchase_message(normalized):
                            return "当前没有可申购的债券"
                        return clean_dialog_text(normalized)
                else:
                    raise RuntimeError("检测到可申购列表但未成功勾选，可能页面结构变化")
            else:
                self._safe_click(page.locator("#btnCxcConfirm"), timeout_ms=2000)
                if is_no_purchase_message(normalized):
                    return "当前没有可申购的债券"
                return clean_dialog_text(normalized)

        confirm = page.locator("#btnConfirm:visible").first
        try:
            confirm.wait_for(state="visible", timeout=3000)
        except PlaywrightTimeoutError:
            dialog_message = self._read_dialog_message(page)
            if dialog_message:
                normalized = normalize_text(dialog_message)
                if "请选择需申购的新债" in normalized:
                    self._safe_click(page.locator("#btnCxcConfirm"), timeout_ms=2000)
                    if self._retry_select_and_batch_buy(page):
                        confirm.wait_for(state="visible", timeout=3000)
                        confirm.click(timeout=self.config.timeout_ms)
                        dialog_text = page.locator("#Cxc_Dialog").inner_text(timeout=self.config.timeout_ms)
                        return clean_dialog_text(dialog_text)
                    raise RuntimeError("检测到可申购列表但未成功勾选，可能页面结构变化")

                self._safe_click(page.locator("#btnCxcConfirm"), timeout_ms=2000)
                if is_no_purchase_message(normalized):
                    return "当前没有可申购的债券"
                return clean_dialog_text(normalized)
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

    def _open_new_stock_bond_menu(self, page: Page) -> None:
        menu = page.locator("li.top_item[href='/Trade/NewBuy'] > a.top_a").first
        menu.click(timeout=self.config.timeout_ms)
        page.locator("li.top_item[href='/Trade/NewBuy'] ul.sub").first.wait_for(
            state="visible", timeout=self.config.timeout_ms
        )

    def _open_bond_batch_purchase_page(self, page: Page) -> None:
        link = page.locator(
            "li.top_item[href='/Trade/NewBuy'] li.sub_item[data-value='trade/xzsgbatpurchase'] > a"
        ).first
        link.click(timeout=self.config.timeout_ms)
        page.wait_for_url("**/Trade/XzsgBatPurchase", timeout=self.config.timeout_ms)

    def _click_batch_buy(self, page: Page) -> None:
        page.locator("#btnBatBuy:visible").first.click(timeout=self.config.timeout_ms)

    def _select_all(self, page: Page) -> bool:
        checkboxes = page.locator("#tableBody input[name='chkitem']")
        if checkboxes.count() == 0:
            return False

        try:
            select_all = page.locator("#chk_all")
            select_all.scroll_into_view_if_needed(timeout=self.config.timeout_ms)
            select_all.click(timeout=self.config.timeout_ms)
        except Exception:
            pass

        page.wait_for_timeout(300)
        if self._has_checked_rows(page):
            return True

        # 无头环境里 #chk_all 偶发失效，回退到逐行勾选，避免误报“未勾选”。
        for i in range(checkboxes.count()):
            checkbox = checkboxes.nth(i)
            try:
                if checkbox.is_enabled() and not checkbox.is_checked():
                    checkbox.scroll_into_view_if_needed(timeout=self.config.timeout_ms)
                    checkbox.click(timeout=self.config.timeout_ms)
            except Exception:
                continue

        page.wait_for_timeout(300)
        return self._has_checked_rows(page)

    def _has_checked_rows(self, page: Page) -> bool:
        try:
            return page.locator("#tableBody input[name='chkitem']:checked").count() > 0
        except Exception:
            return False

    def _retry_select_and_batch_buy(self, page: Page) -> bool:
        if not self._select_all(page):
            return False
        self._click_batch_buy(page)
        return True

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

        deadline = datetime.now().timestamp() + 6
        while datetime.now().timestamp() < deadline:
            rows = table_body.locator("tr")
            if rows.count() == 0:
                page.wait_for_timeout(300)
                continue

            first_text = normalize_text(rows.first.inner_text())
            if "暂无数据" in first_text:
                page.wait_for_timeout(500)
                continue

            checkbox_count = table_body.locator("input[name='chkitem']").count()
            if checkbox_count == 0:
                # 有些时段会出现“表格框架已渲染，但可选项未挂载”的短暂状态。
                # 不能直接判定为有可申购，否则后续会触发全选失败误报。
                page.wait_for_timeout(500)
                continue

            return True

        return False

    def _wait_dialog_message(self, page: Page, timeout_ms: int) -> str:
        dialog = page.locator("#Cxc_Dialog:visible").first
        try:
            dialog.wait_for(state="visible", timeout=timeout_ms)
            return dialog.inner_text(timeout=1200)
        except Exception:
            return ""

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


def normalize_text(text: str) -> str:
    return " ".join(text.replace("\r", " ").replace("\n", " ").split())


def is_no_purchase_message(message: str) -> bool:
    text = normalize_text(message)
    return any(
        keyword in text
        for keyword in (
            "当前没有可申购的债券",
            "暂无可申购",
            "可申购数量为0",
        )
    )


def clean_dialog_text(text: str) -> str:
    cleaned = normalize_text(text)
    if cleaned.startswith("x "):
        cleaned = cleaned[2:]
    if cleaned.endswith("确定"):
        cleaned = cleaned[:-2]
    return cleaned.strip()
