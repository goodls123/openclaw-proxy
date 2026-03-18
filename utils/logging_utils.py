"""
日志工具函数
"""

import os
import sys
import logging
from datetime import datetime
from typing import Optional


def setup_logging(
    log_level: str = "INFO",
    log_dir: str = "logs",
    logger_name: str = "openclaw_proxy",
) -> logging.Logger:
    """
    配置日志系统

    Args:
        log_level: 日志级别 (DEBUG, INFO, WARNING, ERROR)
        log_dir: 日志目录
        logger_name: Logger名称

    Returns:
        配置好的Logger实例
    """
    # 创建日志目录
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    # 创建logger
    logger = logging.getLogger(logger_name)
    logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))

    # 清除已有的handlers
    logger.handlers.clear()

    # 日志格式
    formatter = logging.Formatter(
        "%(asctime)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # 控制台handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # 文件handler - 按日期命名
    log_file = os.path.join(
        log_dir,
        f"openclaw_proxy_{datetime.now().strftime('%Y%m%d')}.log"
    )
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger


def get_logger(name: str = "openclaw_proxy") -> logging.Logger:
    """
    获取Logger实例

    Args:
        name: Logger名称

    Returns:
        Logger实例
    """
    return logging.getLogger(name)


def sanitize_log_message(message: str) -> str:
    """
    清理日志消息中的敏感信息

    Args:
        message: 原始消息

    Returns:
        清理后的消息
    """
    # 不记录密码相关信息
    sensitive_keywords = ["password", "passphrase", "secret", "token"]
    for keyword in sensitive_keywords:
        if keyword in message.lower():
            return f"[敏感信息已隐藏]"
    return message
