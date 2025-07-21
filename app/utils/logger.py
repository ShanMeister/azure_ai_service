from loguru import logger
from pathlib import Path
import sys
import os

def init_logger(log_file_path="logs/app.log", log_level=None):
    """
        初始化同時輸出到控制台和檔案的 logger

        Args:
            log_file_path (str): 日誌檔案路徑 (預設: "logs/app.log")
            log_level (str): 日誌等級 (預設: 從 LOG_LEVEL 環境變數或 "INFO")
        """
    # 移除預設的 logger
    logger.remove()

    # 從參數或環境變數取得日誌等級
    if log_level is None:
        log_level = os.getenv("LOG_LEVEL", "INFO")

    # 確保日誌目錄存在
    log_path = Path(log_file_path)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    logger.add(
        sys.stdout,
        level=log_level,
        format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        enqueue=True
    )

    logger.add(
        log_file_path,
        level=log_level,
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{line} - {message}",
        rotation="10 MB",  # 檔案達到 10MB 時輪轉
        retention="30 days",  # 保存 30 天的日誌
        compression="zip",  # 壓縮輪轉的檔案
        enqueue=True,
        encoding="utf-8"
    )

    return logger
