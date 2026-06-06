"""
时区配置和工具函数
"""
from zoneinfo import ZoneInfo
from app.core.config import settings

# 从全局配置获取时区
APP_TIMEZONE = ZoneInfo(settings.TZ)


def get_timezone():
    """获取应用时区"""
    return APP_TIMEZONE


def get_timezone_name():
    """获取应用时区名称"""
    return settings.TZ
