import os
import time
from typing import Optional
import tkinter.messagebox as tk_messagebox
from tkinter import *

import requests
from selenium import webdriver
from selenium.common.exceptions import *
from selenium.webdriver.common.by import By
from selenium.webdriver.edge.service import Service
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait

import yaml



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


def get_input(title):
    def return_callback(event):
        root.quit()

    def close_callback():
        tk_messagebox.showinfo('message', 'no click...')

    root: Tk = Tk(className=title)
    root.wm_attributes('-topmost', 1)
    screenwidth, screenheight = root.maxsize()
    width = 300
    height = 100
    size = '%dx%d+%d+%d' % (width, height, (screenwidth - width) / 2, (screenheight - height) / 2)
    root.geometry(size)
    root.resizable(0, 0)

    # 显示图片
    img_png = PhotoImage(file='code.png')
    label_img = Label(root, image=img_png)
    label_img.pack()

    # 输入框
    entry = Entry(root)
    entry.bind('<Return>', return_callback)
    entry.pack()
    entry.focus_set()
    root.protocol("WM_DELETE_WINDOW", close_callback)
    root.mainloop()
    str = entry.get()
    root.destroy()
    return str


def send_wechat_info(msg, title='打新债结果'):
    print(msg)
    requests.post("https://www.autodl.com/api/v1/wechat/message/push",
                  json={
                      "token": '3232ab58ff97',
                      "title": title,
                      "content": msg
                  })


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
    elem = driver.find_element(by=By.ID, value='imgValidCode')
    elem.screenshot("code.png")
    code = get_input("请输入验证码")

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


if __name__ == '__main__':
    # 获取yaml文件路径
    curPath = os.path.dirname(os.path.realpath(__file__))
    yamlPath = os.path.join(curPath, "cfg.yml")

    # open方法打开直接读出来
    f = open(yamlPath, 'r', encoding='utf-8')
    cfg = f.read()
    d = yaml.load(cfg, Loader=yaml.FullLoader)

    print(list(d['user']))

    for user in d['user']:
        options = webdriver.EdgeOptions()
        # options.add_argument('--headless')
        driver = webdriver.Edge(options=options)
        try:
            main(driver, user['zjzh'], user['pwd'])
        except Exception as e:
            send_wechat_info("打新债失败，" + str(e).replace('\r', ' ').replace('\n', ' '), user['zjzh'])
        finally:
            driver.quit()
