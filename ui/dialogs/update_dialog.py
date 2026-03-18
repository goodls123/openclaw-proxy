"""
更新对话框
"""

import tkinter as tk
from tkinter import ttk
import webbrowser

from ui.base import BaseDialog, get_font
from models import UpdateCheckResult
from config.constants import GITHUB_RELEASES_URL


class UpdateDialog(BaseDialog):
    """更新提示对话框"""

    def __init__(self, parent, result: UpdateCheckResult):
        """
        初始化更新对话框

        Args:
            parent: 父窗口
            result: 更新检查结果
        """
        self._result = result
        super().__init__(parent, "发现新版本")
        self._create_widgets()
        self._center_on_parent()

    def _create_widgets(self) -> None:
        """创建组件"""
        main_frame = ttk.Frame(self, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 标题
        title_label = ttk.Label(
            main_frame,
            text="有新版本可用!",
            font=get_font(14, bold=True),
            foreground="green",
        )
        title_label.pack(pady=(0, 15))

        # 版本信息
        version_frame = ttk.Frame(main_frame)
        version_frame.pack(fill=tk.X, pady=5)

        ttk.Label(
            version_frame,
            text=f"当前版本: {self._result.current_version}",
            font=get_font(10),
        ).pack()

        ttk.Label(
            version_frame,
            text=f"最新版本: {self._result.latest_version}",
            font=get_font(11, bold=True),
            foreground="blue",
        ).pack(pady=(5, 0))

        # 更新说明（如果有）
        if self._result.release_info and self._result.release_info.body:
            notes_frame = ttk.LabelFrame(main_frame, text="更新说明", padding=10)
            notes_frame.pack(fill=tk.BOTH, expand=True, pady=(15, 5))

            # 使用Text组件显示多行文本
            notes_text = tk.Text(
                notes_frame,
                width=50,
                height=8,
                wrap=tk.WORD,
                font=get_font(9),
            )
            notes_text.insert(tk.END, self._result.release_info.body[:500])  # 限制长度
            notes_text.config(state=tk.DISABLED)
            notes_text.pack(fill=tk.BOTH, expand=True)

        # 按钮
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(pady=(20, 0))

        ttk.Button(
            btn_frame,
            text="前往下载",
            command=self._go_download,
            width=12,
        ).pack(side=tk.LEFT, padx=5)

        ttk.Button(
            btn_frame,
            text="稍后提醒",
            command=self.destroy,
            width=12,
        ).pack(side=tk.LEFT, padx=5)

    def _go_download(self) -> None:
        """打开下载页面"""
        url = (
            self._result.release_info.url
            if self._result.release_info
            else GITHUB_RELEASES_URL
        )
        webbrowser.open(url)
        self.destroy()
