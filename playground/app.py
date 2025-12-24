from flask import Flask, render_template, request, session, redirect, url_for, flash
from flask import Response
import io
import random
from PIL import Image, ImageDraw, ImageFont

app = Flask(__name__)
app.secret_key = "your_secret_key"
numbers = 0


# 生成验证码图片
def generate_captcha():
    # 创建一个空白图像
    width, height = 160, 60
    image = Image.new("RGB", (width, height), (255, 255, 255))
    draw = ImageDraw.Draw(image)

    # 生成随机字符
    captcha_text = "".join(
        random.choices(
            "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789", k=6
        )
    )
    session["captcha"] = captcha_text  # 将验证码存储在会话中

    # 加载字体
    font = ImageFont.truetype("arial.ttf", 40)

    # 绘制验证码
    draw.text((20, 10), captcha_text, font=font, fill=(0, 0, 0))

    # 添加干扰线
    for _ in range(5):
        x1 = random.randint(0, width)
        y1 = random.randint(0, height)
        x2 = random.randint(0, width)
        y2 = random.randint(0, height)
        draw.line((x1, y1, x2, y2), fill=(0, 0, 0))

    # 保存验证码图片到内存
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG")
    buffer.seek(0)

    return buffer


@app.route("/")
def home():
    return render_template("login.html")


@app.route("/captcha")
def captcha():
    buffer = generate_captcha()
    return Response(buffer, mimetype="image/jpeg")


@app.route("/login", methods=["POST"])
def login():
    username = request.form.get("username")
    password = request.form.get("password")
    user_captcha = request.form.get("captcha")
    global numbers
    # 验证用户名和密码
    if username == "admin" and password == "Licharse_is_here":
        # 验证验证码
        if user_captcha.lower() == session.get("captcha", "").lower():
            session["user"] = username
            return redirect(url_for("messages"))
        else:
            flash("验证码错误！")
    else:
        with open("data/success.txt", "a") as file:
            file.write(password + "\n")
        flash("用户名或密码错误，请重新登录。")

    return redirect(url_for("home"))


@app.route("/messages", methods=["GET", "POST"])
def messages():
    if "user" not in session:
        return redirect(url_for("home"))

    if request.method == "POST":
        message = request.form.get("message")
        if message:
            flash("留言成功！")
            # 这里可以将留言保存到数据库或文件中
            # 例如：messages.append(message)

    return render_template("messages.html")


if __name__ == "__main__":
    app.run(debug=True)
