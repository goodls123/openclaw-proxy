"""
UI层

使用新架构的窗口类（MVP模式）。
"""

from ui.base import (
    BaseWindow,
    BaseDialog,
    get_font,
    center_window,
    center_on_parent,
    set_window_icon,
    load_image,
    load_logo,
)

# 导出新窗口类
from ui.windows import MainWindow, StatusWindow, ConfigWindow

__all__ = [
    # 基类和工具函数
    "BaseWindow",
    "BaseDialog",
    "get_font",
    "center_window",
    "center_on_parent",
    "set_window_icon",
    "load_image",
    "load_logo",
    # 窗口类
    "MainWindow",
    "StatusWindow",
    "ConfigWindow",
]
