"""
更新配置对话框
"""

import tkinter as tk
from tkinter import ttk, messagebox

from ui.base import get_font, set_window_icon
from components.header_panel import HeaderPanel
from presenters.config_presenter import ConfigPresenter
from models import Config


class UpdateConfigDialog(tk.Toplevel):
    """更新配置弹窗"""

    def __init__(self, parent, config: Config, presenter: ConfigPresenter):
        super().__init__(parent)
        self.title("OpenClaw连接代理")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        self._config = config
        self._presenter = presenter
        self._result = False

        set_window_icon(self)
        self._create_widgets()
        self._load_config()
        self._center_window()

    def _center_window(self):
        """窗口居中"""
        self.update_idletasks()
        x = self.master.winfo_x() + (self.master.winfo_width() - 600) // 2
        y = self.master.winfo_y() + (self.master.winfo_height() - 450) // 2
        self.geometry(f"600x450+{x}+{y}")

    def _create_widgets(self):
        """创建组件"""
        main_frame = ttk.Frame(self, padding=15)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 头部（Logo + 标题）
        self._header = HeaderPanel(main_frame, title="OpenClaw连接代理", logo_size=128)
        self._header.pack(pady=(0, 10))

        # 版本信息组
        version_group = ttk.LabelFrame(main_frame, text="版本信息", padding=10)
        version_group.pack(fill=tk.X, pady=5)

        from version import __version__
        ttk.Label(
            version_group,
            text=f"当前版本: {__version__}",
            font=get_font(11),
        ).pack(anchor=tk.W, pady=5)

        # 更新设置组
        settings_group = ttk.LabelFrame(main_frame, text="更新选项", padding=10)
        settings_group.pack(fill=tk.X, pady=10)

        self._auto_check_update_var = tk.BooleanVar()
        ttk.Checkbutton(
            settings_group,
            text="启动时自动检查更新",
            variable=self._auto_check_update_var,
        ).pack(anchor=tk.W, pady=5)

        # 检查按钮
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(pady=10)

        self._check_update_btn = ttk.Button(
            btn_frame,
            text="立即检查更新",
            command=self._check_update,
            width=15,
        )
        self._check_update_btn.pack(side=tk.LEFT, padx=5)

        # 状态标签
        self._status_var = tk.StringVar()
        ttk.Label(main_frame, textvariable=self._status_var, foreground="gray").pack(pady=5)

        # 底部按钮
        bottom_frame = ttk.Frame(main_frame)
        bottom_frame.pack(pady=10)
        ttk.Button(bottom_frame, text="确定", command=self._on_ok, width=10).pack(side=tk.LEFT, padx=5)
        ttk.Button(bottom_frame, text="取消", command=self._on_cancel, width=10).pack(side=tk.LEFT, padx=5)

    def _load_config(self):
        """加载配置"""
        self._auto_check_update_var.set(self._config.update.auto_check)

    def _check_update(self):
        """检查更新"""
        self._check_update_btn.config(state="disabled")
        self._status_var.set("正在检查更新...")

        def on_result(result):
            self.after(0, lambda: self._handle_result(result))

        self._presenter.update_service.check_for_update_async(on_result, force=True)

    def _handle_result(self, result):
        """处理检查结果"""
        self._check_update_btn.config(state="normal")

        if result.error:
            self._status_var.set(f"检查失败: {result.error}")
            messagebox.showerror("检查更新", f"检查更新失败:\n{result.error}", parent=self)
        elif result.has_update:
            self._status_var.set(f"发现新版本: {result.latest_version}")
            from ui.dialogs.update_dialog import UpdateDialog
            UpdateDialog(self, result)
        else:
            from version import __version__
            self._status_var.set("当前已是最新版本")
            messagebox.showinfo("检查更新", f"当前已是最新版本 ({__version__})", parent=self)

    def _on_ok(self):
        """确定"""
        self._config.update.auto_check = self._auto_check_update_var.get()
        self._result = True
        self.destroy()

    def _on_cancel(self):
        """取消"""
        self.destroy()

    def get_result(self) -> bool:
        """获取结果"""
        return self._result
