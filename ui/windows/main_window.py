"""
主窗口
"""

import tkinter as tk
from tkinter import ttk, messagebox
from typing import TYPE_CHECKING, Optional

from ui.base import BaseWindow, get_font, center_window
from ui.dialogs.update_dialog import UpdateDialog
from components.header_panel import HeaderPanel
from components.status_panel import StatusPanel
from presenters.main_presenter import MainPresenter
from models import TunnelState

if TYPE_CHECKING:
    from app.container import ServiceContainer


class MainWindow(BaseWindow):
    """
    主窗口

    功能：
    1. 配置SSH连接
    2. 启动/停止隧道
    3. 打开浏览器
    4. 检查更新
    """

    def __init__(self, container: "ServiceContainer", title: str = "OpenClaw代理配置"):
        """
        初始化主窗口

        Args:
            container: 服务容器
            title: 窗口标题
        """
        super().__init__(title)

        self._container = container
        self._presenter = MainPresenter(container)
        self._presenter.attach_view(self)

        self.root.resizable(True, True)
        self.root.minsize(620, 310)

        self._create_widgets()
        self._setup_callbacks()
        self._check_prerequisites()

        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        # 居中显示
        center_window(self.root, 800, 460)

        # 启动时后台检查更新
        self._check_update_async()

    def _create_widgets(self) -> None:
        """创建组件"""
        main_frame = ttk.Frame(self.root, padding=15)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 头部（Logo + 标题）
        self._header = HeaderPanel(main_frame, title="OpenClaw 代理工具", logo_size=128)
        self._header.pack(pady=(0, 12))

        # 状态面板
        self._status_panel = StatusPanel(main_frame, show_info=True)
        self._status_panel.pack(fill=tk.X, pady=5)

        # 连接信息面板
        self._info_frame = ttk.LabelFrame(main_frame, text="连接信息", padding=8)
        self._info_frame.pack(fill=tk.X, pady=5)

        self._info_var = tk.StringVar()
        self._update_info_text()
        ttk.Label(self._info_frame, textvariable=self._info_var, justify=tk.LEFT).pack(anchor=tk.W)

        # 按钮区域
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(pady=12)

        self._browser_btn = ttk.Button(
            btn_frame,
            text="打开浏览器",
            command=self._open_browser,
            width=12,
            state=tk.DISABLED,
        )
        self._browser_btn.pack(side=tk.LEFT, padx=5)

        self._start_btn = ttk.Button(
            btn_frame,
            text="启动代理",
            command=self._start_tunnel,
            width=12,
        )
        self._start_btn.pack(side=tk.LEFT, padx=5)

        self._stop_btn = ttk.Button(
            btn_frame,
            text="停止代理",
            command=self._stop_tunnel,
            width=12,
            state=tk.DISABLED,
        )
        self._stop_btn.pack(side=tk.LEFT, padx=5)

        ttk.Button(
            btn_frame,
            text="配置设置",
            command=self._open_config,
            width=12,
        ).pack(side=tk.LEFT, padx=5)

    def _setup_callbacks(self) -> None:
        """设置回调"""
        self._presenter.set_on_tunnel_state_changed(self._on_tunnel_state_changed)
        self._presenter.set_on_update_available(self._on_update_available)

    def _update_info_text(self) -> None:
        """更新连接信息文本"""
        info = self._presenter.get_config_display_info()
        text = f"服务器: {info['server']}\n"
        text += f"端口映射: {', '.join(info['port_mappings']) if info['port_mappings'] else '无'}"
        self._info_var.set(text)

    def _check_prerequisites(self) -> None:
        """检查前置条件"""
        from utils.network_utils import check_ssh_available

        available, error = check_ssh_available()
        if not available:
            messagebox.showerror("错误", error)
            self.root.quit()
            return

        # 异步测试连接
        self._test_connection_async()

    def _test_connection_async(self) -> None:
        """异步测试SSH连接"""
        self._status_panel.set_state(TunnelState.CONNECTING, "正在检测连接...")
        self._start_btn.config(state=tk.DISABLED)

        def on_result(success: bool, message: str):
            if success:
                self._status_panel.set_state(TunnelState.DISCONNECTED, "✓ 连接就绪")
                self._start_btn.config(state=tk.NORMAL)
            else:
                self._status_panel.set_state(TunnelState.ERROR, f"✗ {message}")
                self._start_btn.config(state=tk.DISABLED)
                # 失败时直接打开配置窗口
                self._open_config()

        self._presenter.test_connection_async(on_result)

    def _start_tunnel(self) -> None:
        """启动隧道"""
        self._status_panel.set_state(TunnelState.CONNECTING, "正在启动隧道...")
        self._start_btn.config(state=tk.DISABLED)
        self.root.update()

        def on_result(success: bool, message: str):
            if success:
                self._status_panel.set_state(TunnelState.CONNECTED)
                self._stop_btn.config(state=tk.NORMAL)
                self._browser_btn.config(state=tk.NORMAL)

                # 自动获取token
                config = self._container.config_repo.load()
                if config.browser.auto_fetch_token:
                    self._fetch_token_async()

                # 自动打开浏览器
                if config.browser.auto_open:
                    self._open_browser()
            else:
                self._status_panel.set_state(TunnelState.ERROR, f"启动失败: {message}")
                self._start_btn.config(state=tk.NORMAL)
                messagebox.showerror("错误", message, parent=self.root)

        self._presenter.start_tunnel_async(on_result)

    def _stop_tunnel(self) -> None:
        """停止隧道"""
        success, message = self._presenter.stop_tunnel()
        if success:
            self._status_panel.set_state(TunnelState.DISCONNECTED)
            self._start_btn.config(state=tk.NORMAL)
            self._stop_btn.config(state=tk.DISABLED)
            self._browser_btn.config(state=tk.DISABLED)
        else:
            messagebox.showerror("错误", message, parent=self.root)

    def _open_browser(self) -> None:
        """打开浏览器"""
        def on_fetching():
            self._status_panel.set_state(TunnelState.CONNECTED, "正在获取token...")

        def on_complete(success: bool):
            if success:
                self._status_panel.set_state(TunnelState.CONNECTED)
            else:
                self._status_panel.set_state(TunnelState.CONNECTED, "✗ 获取token失败")
                messagebox.showwarning("提示", "无法获取token，请检查远程配置", parent=self.root)

        self._presenter.open_browser_async(on_start=on_fetching, on_complete=on_complete)

    def _fetch_token_async(self) -> None:
        """异步获取token"""
        def on_result(success: bool, token: str):
            if success:
                self._status_panel.set_state(TunnelState.CONNECTED)
            else:
                logger = __import__('logging').getLogger("openclaw_proxy")
                logger.warning(f"获取token失败")

        self._presenter.fetch_token_async(on_result)

    def _open_config(self) -> None:
        """打开配置窗口"""
        from ui.windows.config_window import ConfigWindow

        ConfigWindow(self.root, self._container, on_save=self._refresh_status)

    def _refresh_status(self) -> None:
        """刷新状态（配置保存后调用）"""
        self._container.config_repo.load()
        self._update_info_text()
        self._status_panel.set_state(TunnelState.DISCONNECTED, "✓ 配置已更新")

    def _on_tunnel_state_changed(self, state: TunnelState) -> None:
        """隧道状态变化回调"""
        self._status_panel.set_state(state)

    def _on_update_available(self, result) -> None:
        """有更新可用回调"""
        UpdateDialog(self.root, result)

    def _check_update_async(self) -> None:
        """异步检查更新"""
        config = self._container.config_repo.load()
        if config.update.auto_check:
            self._presenter.check_update_async()

    def _on_close(self) -> None:
        """窗口关闭"""
        if self._presenter.is_tunnel_running:
            self._presenter.stop_tunnel()
        self.root.quit()
        self.root.destroy()
