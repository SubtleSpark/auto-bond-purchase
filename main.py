import os
import time
from typing import Optional

import requests
from dotenv import load_dotenv
from selenium import webdriver
from selenium.common.exceptions import *
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait

from captcha import CaptchaRecognizer

# 全局验证码识别器（懒加载模型）
_recognizer = None


def get_recognizer() -> CaptchaRecognizer:
    """获取验证码识别器单例"""
    global _recognizer
    if _recognizer is None:
        _recognizer = CaptchaRecognizer()
    return _recognizer



def purchase_support(driver: WebDriver) -> bool:
    # 如果能获取公告，则代表当天非交易日，不能打新债
    try:
        elem = try_find_element(driver=driver,
                                by=By.XPATH,
                                value="//button[@class='btn-orange vbtn-confirm']",
                                max_try_num=1,
                                interval=1)
        if elem is not None:
            return False
    except NoSuchElementException:
        return True


def try_find_element(driver: WebDriver, by=By.ID, value: Optional[str] = None, max_try_num=5, interval=5) -> WebElement:
    try_num = max_try_num
    while try_num > 0:
        try:
            return driver.find_element(by=by, value=value)
        except NoSuchElementException as e:
            time.sleep(interval)
            try_num -= 1
    raise NoSuchElementException("没有找到元素 by={} value={}".format(by, value))


def refresh_captcha(driver: WebDriver) -> None:
    """点击验证码图片刷新"""
    elem = driver.find_element(by=By.ID, value='imgValidCode')
    elem.click()
    time.sleep(0.5)  # 等待新验证码加载


def recognize_captcha_with_retry(driver: WebDriver, max_retries: int = 3) -> str:
    """
    识别验证码，失败时自动刷新重试

    Args:
        driver: WebDriver 实例
        max_retries: 最大重试次数

    Returns:
        识别出的验证码
    """
    recognizer = get_recognizer()
    captcha_path = os.path.join(os.path.dirname(__file__), "code.png")

    for attempt in range(max_retries):
        # 截图验证码
        elem = driver.find_element(by=By.ID, value='imgValidCode')
        elem.screenshot(captcha_path)

        # 识别
        try:
            code = recognizer.recognize(captcha_path)
            print(f"验证码识别结果 (第{attempt + 1}次): {code}")
            return code
        except Exception as e:
            print(f"验证码识别失败 (第{attempt + 1}次): {e}")
            if attempt < max_retries - 1:
                refresh_captcha(driver)

    raise RuntimeError(f"验证码识别失败，已重试 {max_retries} 次")


def send_wechat_info(msg, title='打新债结果'):
    """通过 pushplus 发送消息推送"""
    print(msg)
    token = os.environ.get('PUSHPLUS_TOKEN', '')
    if not token:
        return

    try:
        response = requests.post(
            "https://www.pushplus.plus/send",
            json={
                "token": token,
                "title": title,
                "content": msg,
                "template": "txt"  # 纯文本模板
            },
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        result = response.json()
        if result.get('code') == 200:
            print(f"推送成功: {result.get('data')}")
        else:
            print(f"推送失败: [{result.get('code')}] {result.get('msg')}")
    except Exception as e:
        print(f"推送异常: {e}")


def main(driver: WebDriver, zjzh, pwd):
    driver.maximize_window()  # 全屏，防止元素被遮挡无法点击
    driver.get('https://jywg.18.cn/Login?el=1&clear=&returl=%2fTrade%2fBuy')

    # 无法打新债则退出
    if not purchase_support(driver):
        send_wechat_info("目前不能打新债", zjzh)
        return
    else:
        print("目前可以打新债")

    try_find_element(driver=driver, by=By.ID, value='txtZjzh', max_try_num=1, interval=1).send_keys(zjzh)
    try_find_element(driver=driver, by=By.ID, value='txtPwd').send_keys(pwd)

    # 自动识别验证码（失败自动重试）
    code = recognize_captcha_with_retry(driver, max_retries=3)

    try_find_element(driver=driver, by=By.ID, value='txtValidCode').send_keys(code)
    try_find_element(driver=driver, by=By.ID, value='btnConfirm').click()

    try:
        btn = driver.find_element(by=By.CLASS_NAME, value='vbtn-confirm')
        btn.click()
    except NoSuchElementException:
        pass

    try_find_element(driver=driver, by=By.PARTIAL_LINK_TEXT, value='新股新债').click()
    try_find_element(driver=driver, by=By.PARTIAL_LINK_TEXT, value='新债批量申购').click()

    # 查看是否有可申购的债券,如果没有则退出
    elem = try_find_element(driver=driver, by=By.ID, value='tableBody')
    if elem.text == '' or elem.text == '暂无数据' or elem.text.isspace():
        send_wechat_info("当前没有可申购的债券", zjzh)
        return

    # 选择全部债券，点击申购
    WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.ID, 'chk_all'))).click()
    WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.LINK_TEXT, '批量申购'))).click()
    WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.LINK_TEXT, '确定申购'))).click()

    # 获取申购结果
    result = try_find_element(driver=driver, by=By.XPATH, value='//*[@id="Cxc_Dialog"]').text
    send_wechat_info(result.replace('\r', ' ').replace('\n', ' ').removeprefix('x ').removesuffix('确定'), zjzh)
    return


def create_driver(headless: bool = False, browser: str = None) -> WebDriver:
    """
    创建浏览器驱动

    Args:
        headless: 是否使用无头模式
        browser: 浏览器类型 ('chrome' 或 'edge')，默认根据环境自动选择

    Returns:
        WebDriver 实例
    """
    if browser is None:
        # 环境变量指定，或默认使用 Chrome（Linux 兼容性更好）
        browser = os.environ.get('BROWSER', 'chrome').lower()

    if browser == 'chrome':
        options = webdriver.ChromeOptions()
        if headless:
            options.add_argument('--headless=new')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-gpu')
        options.add_argument('--window-size=1920,1080')
        return webdriver.Chrome(options=options)
    else:
        options = webdriver.EdgeOptions()
        if headless:
            options.add_argument('--headless=new')
        return webdriver.Edge(options=options)


def parse_users() -> list[dict]:
    """
    从环境变量 USERS 解析用户列表

    格式: "账号1:密码1,账号2:密码2"
    """
    users_str = os.environ.get('USERS', '')
    if not users_str:
        raise ValueError("环境变量 USERS 未设置，格式: 账号1:密码1,账号2:密码2")

    users = []
    for pair in users_str.split(','):
        pair = pair.strip()
        if ':' not in pair:
            raise ValueError(f"用户格式错误: {pair}，应为 账号:密码")
        zjzh, pwd = pair.split(':', 1)
        users.append({'zjzh': zjzh.strip(), 'pwd': pwd.strip()})
    return users


if __name__ == '__main__':
    # 加载 .env 文件（不覆盖已有环境变量）
    load_dotenv()

    # 从环境变量读取配置
    users = parse_users()

    headless = os.environ.get('HEADLESS', 'false').lower() == 'true'
    browser = os.environ.get('BROWSER', None)

    print(f"浏览器: {browser or 'chrome'}, Headless: {headless}")
    print(f"用户列表: {[u['zjzh'] for u in users]}")

    for user in users:
        driver = create_driver(headless=headless, browser=browser)
        try:
            main(driver, user['zjzh'], user['pwd'])
        except Exception as e:
            send_wechat_info("打新债失败，" + str(e).replace('\r', ' ').replace('\n', ' '), user['zjzh'])
        finally:
            driver.quit()
