"""
log.py — 共享日志模块

提供统一日志配置，供 skill-standardization 各脚本使用。
CLI 输出（审计报告、结果）仍用 print，内部状态/调试信息用此模块。

用法:
    from log import get_logger
    logger = get_logger(__name__)
    logger.info("处理文件 %s", path)
    logger.warning("发现异常: %s", err)
    logger.error("操作失败")
"""
import logging
import os
import sys
from datetime import datetime

_LOG_CONFIGURED = False


def setup_logging(level: str = "WARNING", skill_dir: str = None) -> None:
    """配置日志格式，可选写入文件"""
    global _LOG_CONFIGURED
    if _LOG_CONFIGURED:
        return

    fmt = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(fmt)
    root = logging.getLogger()
    root.addHandler(handler)
    root.setLevel(getattr(logging, level.upper(), logging.WARNING))

    if skill_dir:
        log_dir = os.path.join(skill_dir, ".standardization", "skill-standardization", "logs")
        os.makedirs(log_dir, exist_ok=True)
        fh = logging.FileHandler(
            os.path.join(log_dir, f"skill-std-{datetime.now().strftime('%Y%m%d')}.log"),
            encoding="utf-8",
        )
        fh.setFormatter(fmt)
        root.addHandler(fh)

    _LOG_CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    """获取命名 logger，自动初始化一次"""
    if not _LOG_CONFIGURED:
        setup_logging()
    return logging.getLogger(name)
