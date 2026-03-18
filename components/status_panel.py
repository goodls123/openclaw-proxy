"""
状态面板组件
显示隧道状态的统一面板
"""

import tkinter as tk
from tkinter import ttk
from typing import Optional

from ui.base import get_font
from models import TunnelState


class StatusPanel(ttk.LabelFrame):
    """
    状态面板组件

    功能：
    1. 显示隧道状态（图标 + 文字）
    2. 显示连接信息
    """

    def __init__(
        self,
        parent,
        title: str = "状态",
        show_info: bool = True,
    ):
        """
        初始化状态面板

        Args:
            parent: 父组件
            title: 面板标题
            show_info: 是否显示连接信息
        """
        super().__init__(parent, text=title, padding=8)
        self._show_info = show_info
        self._create_widgets()

    def _create_widgets(self) -> None:
        """创建组件"""
        # 状态显示
        self._status_var = tk.StringVar(value="未连接")
        self._status_label = ttk.Label(
            self,
            textvariable=self._status_var,
            font=get_font(11),
        )
        self._status_label.pack()

        # 连接信息（可选）
        if self._show_info:
            self._info_var = tk.StringVar()
            self._info_label = ttk.Label(
                self,
                textvariable=self._info_var,
                font=get_font(9),
                justify=tk.LEFT,
            )
            self._info_label.pack(anchor=tk.W, pady=(5, 0))

    def set_state(self, state: TunnelState, message: Optional[str] = None) -> None:
        """
        设置状态

        Args:
            state: 隧道状态
            message: 自定义消息
        """
        display_text = f"{state.status_icon} {message or state.display_text}"
        self._status_var.set(display_text)

        # 设置颜色
        self._status_label.config(foreground=state.color)

    def set_info(self, info: str) -> None:
        """
        设置连接信息

        Args:
            info: 信息文本
        """
        if self._show_info:
            self._info_var.set(info)

    def set_info_lines(self, lines: list[str]) -> None:
        """
        设置多行连接信息

        Args:
            lines: 信息行列表
        """
        if self._show_info:
            self._info_var.set("\n".join(lines))

    def get_status_text(self) -> str:
        """获取当前状态文本"""
        return self._status_var.get()
