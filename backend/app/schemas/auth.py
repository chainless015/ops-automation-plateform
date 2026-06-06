"""
认证相关的Pydantic模型
"""
from pydantic import BaseModel, Field
from typing import Optional


class LoginRequest(BaseModel):
    """登录请求（用户名/邮箱 + 密码 + 图形验证码）"""
    username: str = Field(..., min_length=1, description="用户名或邮箱")
    password: str = Field(..., min_length=1, description="密码")
    captcha_id: str = Field(..., description="验证码ID")
    captcha_code: str = Field(..., min_length=1, max_length=10, description="验证码")


class UserInfo(BaseModel):
    """用户信息"""
    id: int
    username: str
    email: Optional[str] = None

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    """Token响应"""
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserInfo
