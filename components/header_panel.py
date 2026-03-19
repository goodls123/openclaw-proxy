"""
头部面板组件
显示Logo和标题
"""

import tkinter as tk
from tkinter import ttk
from typing import Optional

from ui.base import get_font, load_logo


class HeaderPanel(ttk.Frame):
    """
    头部面板组件

    功能：
    1. 显示Logo图片
    2. 显示标题文字
    """

    def __init__(
        self,
        parent,
        title: str = "OpenClaw连接代理",
        logo_size: int = 64,
        show_logo: bool = True,
    ):
        """
        初始化头部面板

        Args:
            parent: 父组件
            title: 标题文字
            logo_size: Logo大小
            show_logo: 是否显示Logo
        """
        super().__init__(parent)
        self._title = title
        self._logo_size = logo_size
        self._show_logo = show_logo
        self._logo_image: Optional[object] = None
        self._create_widgets()

    def _create_widgets(self) -> None:
        """创建组件"""
        # Logo图片
        if self._show_logo:
            self._logo_image = load_logo(self._logo_size)
            if self._logo_image:
                logo_label = ttk.Label(self, image=self._logo_image)
                logo_label.pack(side=tk.LEFT, padx=(0, 10))

        # 标题
        ttk.Label(
            self,
            text=self._title,
            font=get_font(14, bold=True),
        ).pack(side=tk.LEFT, padx=(10, 0))

    def set_title(self, title: str) -> None:
        """
        设置标题

        Args:
            title: 新标题
        """
        self._title = title
        # 重新创建组件
        for widget in self.winfo_children():
            widget.destroy()
        self._create_widgets()
