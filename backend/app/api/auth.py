"""
认证相关API
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import timedelta
from app.core.database import get_db
from app.core.security import verify_password, create_access_token
from app.core.config import settings
from app.core.redis import redis_client
from app.models.user import User
from app.schemas.auth import LoginRequest, TokenResponse, UserInfo
import logging
import random
import string
import io
import base64

# Pillow 图形验证码
from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger(__name__)

router = APIRouter()


def _generate_captcha_image(text: str) -> str:
    """
    生成图形验证码图片，返回 base64 编码的 PNG 字符串。
    不依赖外部字体文件，使用 Pillow 内置的默认位图字体。
    """
    width, height = 120, 40
    bg_color = (15, 20, 30)           # 深色背景，与登录页风格一致

    img = Image.new("RGB", (width, height), color=bg_color)
    draw = ImageDraw.Draw(img)

    # 添加随机干扰线
    for _ in range(5):
        x1 = random.randint(0, width)
        y1 = random.randint(0, height)
        x2 = random.randint(0, width)
        y2 = random.randint(0, height)
        draw.line([(x1, y1), (x2, y2)], fill=(random.randint(30, 80), random.randint(80, 120), random.randint(100, 160)), width=1)

    # 添加随机噪点
    for _ in range(80):
        x = random.randint(0, width - 1)
        y = random.randint(0, height - 1)
        draw.point((x, y), fill=(random.randint(40, 100), random.randint(100, 160), random.randint(140, 200)))

    # 使用 Pillow 内置默认字体绘制字符（逐字符绘制，每个字符随机偏移和颜色）
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 26)
    except Exception:
        font = ImageFont.load_default()

    char_width = (width - 16) // len(text)
    for i, ch in enumerate(text):
        x = 8 + i * char_width + random.randint(0, max(0, char_width - 20))
        y = random.randint(4, 10)
        color = (
            random.randint(0, 100),
            random.randint(180, 255),
            random.randint(180, 255)
        )
        draw.text((x, y), ch, font=font, fill=color)

    # 转为 base64
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()


@router.get("/captcha")
def get_captcha():
    """
    生成图形验证码，返回 base64 图片和对应的 captcha_id。
    验证码存入 Redis，有效期 5 分钟。
    """
    # 生成4位字母+数字混合验证码（去掉易混淆字符 0/O/I/l）
    chars = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    code = ''.join(random.choices(chars, k=4))

    # 生成唯一 ID 存入 Redis
    captcha_id = ''.join(random.choices(string.ascii_lowercase + string.digits, k=16))
    redis_client.setex(f"captcha:{captcha_id}", 300, code.upper())

    image_b64 = _generate_captcha_image(code)

    return {
        "captcha_id": captcha_id,
        "image": f"data:image/png;base64,{image_b64}"
    }


@router.post("/login", response_model=TokenResponse)
def login(
    login_data: LoginRequest,
    db: Session = Depends(get_db)
):
    """用户名 + 密码 + 图形验证码登录"""

    # 校验图形验证码
    captcha_key = f"captcha:{login_data.captcha_id}"
    stored_code = redis_client.get(captcha_key)

    if isinstance(stored_code, bytes):
        stored_code = stored_code.decode()

    if not stored_code or stored_code.upper() != login_data.captcha_code.upper():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="验证码错误或已过期"
        )

    # 验证码一次性使用
    redis_client.delete(captcha_key)

    # 查询用户（支持用户名或邮箱）
    user = db.query(User).filter(
        (User.username == login_data.username) |
        (User.email == login_data.username)
    ).first()

    if not user or not verify_password(login_data.password, user.password_hash):
        logger.warning(f"Failed login attempt for: {login_data.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token_expires = timedelta(hours=settings.ACCESS_TOKEN_EXPIRE_HOURS)
    access_token = create_access_token(
        data={"user_id": user.id, "username": user.username},
        expires_delta=access_token_expires
    )

    logger.info(f"User {user.username} logged in successfully")

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_HOURS * 3600,
        user=UserInfo(id=user.id, username=user.username, email=user.email)
    )
