from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException
import os
import logging


def setup_browser_options(headless: bool = True) -> Options:
    options = webdriver.ChromeOptions()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-infobars")
    options.add_argument("--disable-logging")
    options.add_argument("--disable-default-apps")
    options.add_argument("--disable-popup-blocking")
    options.add_argument("--disable-notifications")
    options.add_argument("--disable-application-cache")
    options.add_argument("--disable-web-security")
    options.add_argument("--disk-cache-size=1")
    options.add_argument("--media-cache-size=1")
    options.add_experimental_option(
        "excludeSwitches", ["enable-automation", "enable-logging"]
    )
    options.add_experimental_option("useAutomationExtension", False)
    if headless:
        options.add_argument("--headless")
    return options


def create_browser_driver(options: Options) -> webdriver.Chrome:
    service = Service(log_output=os.devnull)
    return webdriver.Chrome(options=options, service=service)


def check_captcha_error(driver):
    """检查是否为验证码错误"""
    try:
        # 检查页面中是否包含验证码错误的文本
        error_texts = ["验证码错误", "验证码不正确", "验证码输入有误", "验证码失效"]
        page_source = driver.page_source.lower()
        return any(text.lower() in page_source for text in error_texts)
    except Exception as e:
        logging.warning(f"验证码错误检查出现异常: {str(e)}")
        return False


def refresh_captcha(driver, xpath: str):
    try:
        captcha_img = driver.find_element(By.XPATH, xpath)
        driver.execute_script("arguments[0].click();", captcha_img)
        return True
    except Exception:
        try:
            driver.refresh()
            return True
        except Exception as e:
            logging.error(f"刷新验证码失败: {str(e)}")
            return False


def check_login_success(driver, login_url: str, username_xpath: str) -> bool:
    try:
        if driver.current_url != login_url:
            return True
        if "错误" in driver.page_source:
            return False
        possible_xpaths = [
            "//div[contains(text(), '欢迎')]",
            "//div[contains(text(), '成功')]",
            "//div[contains(@class, 'logged-in')]",
        ]
        for xpath in possible_xpaths:
            try:
                elem = driver.find_element(By.XPATH, xpath)
                if elem.is_displayed():
                    return True
            except NoSuchElementException:
                continue
        try:
            login_form = driver.find_element(By.XPATH, username_xpath)
            return not login_form.is_displayed()
        except NoSuchElementException:
            return True
    except Exception as e:
        logging.warning(f"登录状态检查异常: {str(e)}")
        return False
