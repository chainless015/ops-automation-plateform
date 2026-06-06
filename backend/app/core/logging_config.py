"""
应用日志配置（按天轮转）
"""
import logging
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path

LOG_DIR = Path("logs")
LOG_FILE = LOG_DIR / "app.log"
# 每天午夜切分，保留最近 30 天（app.log + app.log.YYYY-MM-DD）
BACKUP_COUNT = 30


def setup_logging(level: int = logging.INFO) -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s"
    )

    file_handler = TimedRotatingFileHandler(
        LOG_FILE,
        when="midnight",
        interval=1,
        backupCount=BACKUP_COUNT,
        encoding="utf-8",
        utc=False,
    )
    file_handler.suffix = "%Y-%m-%d"
    file_handler.setFormatter(formatter)

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)

    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(level)
    root.addHandler(file_handler)
    root.addHandler(stream_handler)
