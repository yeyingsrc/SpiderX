import base64
from io import BytesIO
import logging
import threading
import ddddocr
from PIL import Image


class CaptchaHandler:
    def __init__(self):
        self.ocr = ddddocr.DdddOcr(show_ad=False)
        self.retry_count = 0
        self.last_captcha = None
        self._lock = threading.Lock()

    def recognize_captcha(self, image_data):
        """识别验证码"""
        with self._lock:
            try:
                # 确保图片数据是字节格式
                if isinstance(image_data, str):
                    if image_data.startswith("data:image"):
                        image_data = base64.b64decode(image_data.split(",")[1])
                    else:
                        # 假设是base64字符串
                        try:
                            image_data = base64.b64decode(image_data)
                        except Exception:
                            raise Exception("Invalid image data format")

                # 使用PIL处理图片
                image = Image.open(BytesIO(image_data))

                # 转换为RGB模式（如果需要）
                if image.mode != "RGB":
                    image = image.convert("RGB")

                # 调整图片大小（如果需要）
                # image = image.resize((100, 30), Image.LANCZOS)

                # 转回字节流
                buffered = BytesIO()
                image.save(buffered, format="PNG")
                image_bytes = buffered.getvalue()

                # 识别验证码
                result = self.ocr.classification(image_bytes)

                # 清理结果
                result = result.strip()
                if not result:
                    raise Exception("OCR result is empty")

                self.last_captcha = result
                return result
            except Exception as e:
                logging.error(f"验证码识别失败: {str(e)}")
                return None

    def verify_captcha(self, driver, captcha_code):
        """验证验证码是否正确"""
        try:
            # 这里添加验证码验证逻辑
            # 可以根据实际情况判断验证码是否正确
            return True
        except Exception as e:
            logging.error(f"验证码验证失败: {str(e)}")
            return False
