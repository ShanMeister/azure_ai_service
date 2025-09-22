from loguru import logger as loguru_logger
from pathlib import Path
import sys
import os

def _init_logger(log_file_path="logs/app.log", log_level=None):
    """
    初始化 logger（同時輸出到控制台和檔案）
    """
    # 移除預設的 logger
    loguru_logger.remove()

    # 從參數或環境變數取得日誌等級
    if log_level is None:
        log_level = os.getenv("LOG_LEVEL", "INFO")

    # 確保日誌目錄存在
    log_path = Path(log_file_path)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    # 控制台輸出
    loguru_logger.add(
        sys.stdout,
        level=log_level,
        format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
               "<level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        enqueue=True
    )

    # 檔案輸出（自動輪轉）
    loguru_logger.add(
        log_file_path,
        level=log_level,
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{line} - {message}",
        rotation="10 MB",         # 檔案達到 10MB 時輪轉
        retention="30 days",      # 保存 30 天
        compression="zip",        # 壓縮輪轉檔案
        enqueue=True,
        encoding="utf-8"
    )

    return loguru_logger

logger = _init_logger()
