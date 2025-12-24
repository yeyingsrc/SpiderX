# 在 DEFAULT_CONFIG 中添加验证码相关配置
DEFAULT_CONFIG = {
    "url": "http://127.0.0.1:5000/",
    "name_xpath": '//*[@id="username"]',
    "pass_xpath": '//*[@id="password"]',
    "btn_xpath": "/html/body/form/div[4]/button",
    "success_xpath": '//*[contains(text(),"欢迎")]',  # 新增成功检测元素
    "user_file": "data/username.txt",
    "pass_file": "data/password.txt",
    "threads": 10,  # 根据CPU核心数优化
    "headless": True,
    "timeout": 5,  # 延长超时时间
    "max_retries": 3,  # 最大重试次数
    "min_delay": 0.5,  # 最小延迟（秒）
    "max_delay": 1.5,  # 最大延迟（秒）
    "captcha_xpath": "/html/body/form/div[3]/img",  # 验证码图片元素
    "captcha_input_xpath": '//*[@id="captcha"]',  # 验证码输入框
    "captcha_refresh_xpath": "/html/body/form/div[3]/img",  # 验证码刷新按钮（如果有）
    "has_captcha": True,  # 是否启用验证码识别
    "captcha_retry_limit": 3,  # 验证码识别重试次数
    "captcha_timeout": 1,  # 验证码加载超时时间
}
