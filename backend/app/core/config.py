"""
应用配置
"""
from pydantic_settings import BaseSettings
from typing import Optional, List
from dotenv import load_dotenv
import os

# 手动加载 .env 文件
load_dotenv()


class Settings(BaseSettings):
    """应用配置类"""
    
    # 应用基本信息
    APP_NAME: str = "自动化运维平台"
    APP_VERSION: str = "1.0.0"

    # 时区配置
    TZ: str = "Asia/Shanghai"
    
    # 数据库配置
    DATABASE_URL: str
    
    # Redis配置
    REDIS_URL: str
    
    # JWT配置
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_HOURS: int = 24
    
    # Prometheus配置
    PROMETHEUS_URL: str
    
    # 加密密钥（用于SSH密码加密）
    ENCRYPTION_KEY: Optional[str] = None

    # SMTP邮件配置
    SMTP_HOST: str = ""
    SMTP_PORT: int = 465
    SMTP_USERNAME: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM: str = ""
    SMTP_USE_TLS: bool = True

    # CORS配置
    CORS_ORIGINS: List[str] = [
        "http://localhost",
        "http://localhost:80",
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1",
        "http://127.0.0.1:80",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000"
    ]
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# 创建全局配置实例
settings = Settings()
