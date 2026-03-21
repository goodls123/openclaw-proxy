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


class TkinterLogHandler(logging.Handler):
    """
    Tkinter日志处理器

    将日志消息发送到Tkinter Text组件显示
    """

    def __init__(self, max_lines: int = 100):
        super().__init__()
        self._text_widget = None
        self._max_lines = max_lines
        self._pending_logs = []  # 在Text组件设置前暂存日志

        # 简化的日志格式（只显示时间和消息）
        self.setFormatter(logging.Formatter(
            "%(asctime)s %(levelname)s: %(message)s",
            datefmt="%H:%M:%S"
        ))

    def set_text_widget(self, text_widget) -> None:
        """设置Text组件"""
        self._text_widget = text_widget
        # 输出暂存的日志
        if text_widget and self._pending_logs:
            for level, log_msg in self._pending_logs:
                self._append_to_widget(level, log_msg)
            self._pending_logs.clear()

    def emit(self, record: logging.LogRecord) -> None:
        """处理日志记录"""
        try:
            msg = self.format(record)
            level = record.levelname
            if self._text_widget:
                # 确保在主线程中更新UI
                try:
                    self._text_widget.after(0, lambda l=level, m=msg: self._append_to_widget(l, m))
                except Exception:
                    self._append_to_widget(level, msg)
            else:
                # 暂存日志 (级别, 消息)
                self._pending_logs.append((level, msg))
                if len(self._pending_logs) > self._max_lines:
                    self._pending_logs.pop(0)
        except Exception:
            self.handleError(record)

    def _append_to_widget(self, level: str, msg: str) -> None:
        """将日志追加到Text组件"""
        if not self._text_widget:
            return

        try:
            # 添加日志行
            self._text_widget.configure(state='normal')
            self._text_widget.insert('end', msg + '\n', level)
            self._text_widget.see('end')  # 滚动到底部

            # 限制行数
            line_count = int(self._text_widget.index('end-1c').split('.')[0])
            if line_count > self._max_lines:
                self._text_widget.delete('1.0', f'{line_count - self._max_lines}.0')

            self._text_widget.configure(state='disabled')
        except Exception:
            pass
