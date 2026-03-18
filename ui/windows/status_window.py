"""
状态窗口
"""

import tkinter as tk
from tkinter import ttk, messagebox
from typing import TYPE_CHECKING

from ui.base import BaseWindow, get_font, center_window
from ui.windows.config_window import ConfigWindow
from components.header_panel import HeaderPanel
from components.status_panel import StatusPanel
from presenters.status_presenter import StatusPresenter
from models import TunnelState

if TYPE_CHECKING:
    from app.container import ServiceContainer
    from services.tunnel_service import TunnelService


class StatusWindow(BaseWindow):
    """
    状态窗口

    功能：
    1. 显示隧道运行状态
    2. 打开浏览器
    3. 停止/重启隧道（单按钮切换）
    4. 自动获取token
    """

    def __init__(self, container: "ServiceContainer", tunnel_service: "TunnelService"):
        """
        初始化状态窗口

        Args:
            container: 服务容器
            tunnel_service: 隧道服务（已启动）
        """
        super().__init__("OpenClaw代理 - 运行中")

        self._container = container
        self._presenter = StatusPresenter(container)
        self._presenter.attach_view(self)

        self.root.resizable(True, True)
        self.root.minsize(800, 430)

        self._create_widgets()
        self._setup_callbacks()

        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        # 居中显示
        center_window(self.root, 800, 430)

        # 自动获取token
        config = container.config_repo.load()
        if config.browser.auto_fetch_token:
            self._fetch_token_async()

    def _create_widgets(self) -> None:
        """创建组件"""
        main_frame = ttk.Frame(self.root, padding=15)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 头部（Logo + 标题）
        self._header = HeaderPanel(main_frame, title="虾代理", logo_size=128)
        self._header.pack(pady=(0, 8))

        # 状态面板
        self._status_panel = StatusPanel(main_frame, title="状态", show_info=True)
        self._status_panel.set_state(TunnelState.CONNECTED)
        self._status_panel.pack(fill=tk.X, pady=5)

        # 连接信息
        self._update_info_text()

        # 按钮区域
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(pady=12)

        self._browser_btn = ttk.Button(
            btn_frame,
            text="打开浏览器",
            command=self._open_browser,
            width=14,
        )
        self._browser_btn.pack(side=tk.LEFT, padx=5)

        self._is_tunnel_running = True  # 隧道运行状态

        self._toggle_btn = ttk.Button(
            btn_frame,
            text="停止代理",
            command=self._toggle_tunnel,
            width=14,
        )
        self._toggle_btn.pack(side=tk.LEFT, padx=5)

        ttk.Button(
            btn_frame,
            text="查看配置",
            command=self._open_config,
            width=14,
        ).pack(side=tk.LEFT, padx=5)

    def _setup_callbacks(self) -> None:
        """设置回调"""
        self._presenter.set_on_status_changed(self._on_status_changed)

    def _update_info_text(self) -> None:
        """更新连接信息文本"""
        info = self._presenter.get_status_display_info()
        lines = [
            f"本地地址: {info['local_address']}",
            f"服务器: {info['server']}",
        ]
        if info.get('pid'):
            lines.append(f"进程ID: {info['pid']}")
        self._status_panel.set_info_lines(lines)

    def _toggle_tunnel(self) -> None:
        """切换隧道状态（停止/启动）"""
        if self._is_tunnel_running:
            self._stop_tunnel()
        else:
            self._start_tunnel()

    def _stop_tunnel(self) -> None:
        """停止隧道"""
        success, message = self._presenter.stop_tunnel()
        if success:
            self._is_tunnel_running = False
            self._status_panel.set_state(TunnelState.DISCONNECTED)
            self._toggle_btn.config(text="启动代理")
            self._browser_btn.config(state=tk.DISABLED)
        else:
            messagebox.showerror("错误", message, parent=self.root)

    def _start_tunnel(self) -> None:
        """启动隧道"""
        self._status_panel.set_state(TunnelState.RECONNECTING, "正在重新连接...")
        self._toggle_btn.config(state=tk.DISABLED)
        self.root.update()

        def on_result(success: bool, message: str):
            if success:
                self._is_tunnel_running = True
                self._status_panel.set_state(TunnelState.CONNECTED)
                self._toggle_btn.config(text="停止代理", state=tk.NORMAL)
                self._browser_btn.config(state=tk.NORMAL)

                config = self._container.config_repo.load()
                if config.browser.auto_open:
                    self._open_browser()
            else:
                self._status_panel.set_state(TunnelState.ERROR, f"重启失败: {message}")
                self._toggle_btn.config(state=tk.NORMAL)
                messagebox.showerror("错误", message, parent=self.root)

        self._presenter.restart_tunnel_async(on_result)

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
            # 失败时不显示错误，静默处理

        self._presenter.fetch_token_async(on_result)

    def _open_config(self) -> None:
        """打开配置窗口"""
        ConfigWindow(self.root, self._container, on_save=self._refresh_status)

    def _refresh_status(self) -> None:
        """刷新状态"""
        self._container.config_repo.load()
        self._update_info_text()
        self._status_panel.set_state(TunnelState.CONNECTED, "✓ 配置已更新")

    def _on_status_changed(self, state: TunnelState, message: str = "") -> None:
        """状态变化回调"""
        self._status_panel.set_state(state, message if message else None)
        self._update_info_text()

    def _on_close(self) -> None:
        """窗口关闭"""
        self._presenter.stop_tunnel()
        self.root.quit()
        self.root.destroy()
