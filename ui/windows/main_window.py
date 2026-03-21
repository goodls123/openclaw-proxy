"""
主窗口
"""

import logging
import threading
import tkinter as tk
from tkinter import ttk, messagebox
from typing import TYPE_CHECKING, Optional

from ui.base import BaseWindow, center_window
from ui.dialogs.update_dialog import UpdateDialog
from components.server_list_panel import ServerListPanel
from presenters.main_presenter import MainPresenter
from utils.logging_utils import TkinterLogHandler

logger = logging.getLogger("openclaw_proxy")

if TYPE_CHECKING:
    from app.container import ServiceContainer


class MainWindow(BaseWindow):
    """
    主窗口

    功能：
    1. 服务器列表管理
    2. 配置SSH连接
    3. 启动/停止连接
    4. 浏览器打开
    5. 检查更新
    """

    def __init__(self, container: "ServiceContainer", title: str = "OpenClaw连接代理"):
        super().__init__(title)

        self._container = container
        self._presenter = MainPresenter(container)
        self._presenter.attach_view(self)

        # 隧道运行状态
        self._is_tunnel_running = False
        self._current_server_id: Optional[str] = None

        self.root.resizable(True, True)
        self.root.minsize(600, 400)

        self._create_widgets()
        self._setup_callbacks()
        self._load_servers()
        self._check_prerequisites()

        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        # 居中显示
        center_window(self.root, 700, 380)

        # 启动时后台检查更新
        self._check_update_async()

        logger.info("虾代理启动成功，点击服务器列表开启代理")


    def _create_widgets(self) -> None:
        """创建组件"""
        main_frame = ttk.Frame(self.root, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 服务器列表
        self._server_list = ServerListPanel(
            main_frame,
            on_server_toggle=self._on_server_toggle,
            on_server_config=self._on_server_config,
            on_server_open_browser=self._on_server_open_browser,
            on_add_server=self._on_add_server,
        )
        self._server_list.pack(fill=tk.X, pady=(0, 10))

        # 按钮区域
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(pady=5)

        self._toggle_btn = ttk.Button(
            btn_frame,
            text="启动代理",
            command=self._toggle_tunnel,
            width=12,
        )
        self._toggle_btn.pack(side=tk.LEFT, padx=5)

        ttk.Button(
            btn_frame,
            text="密钥管理",
            command=self._open_security,
            width=12,
        ).pack(side=tk.LEFT, padx=5)

        ttk.Button(
            btn_frame,
            text="软件更新",
            command=self._open_update,
            width=12,
        ).pack(side=tk.LEFT, padx=5)

        # 日志显示区域
        self._setup_log_panel(main_frame)

    def _setup_log_panel(self, parent: ttk.Frame) -> None:
        """设置日志显示面板"""
        # 日志面板容器
        log_frame = ttk.LabelFrame(parent, text="运行日志", padding=5)
        log_frame.pack(fill=tk.BOTH, expand=True, pady=(10, 0))

        # 创建带滚动条的Text组件
        log_container = ttk.Frame(log_frame)
        log_container.pack(fill=tk.BOTH, expand=True)

        # 垂直滚动条
        scrollbar = ttk.Scrollbar(log_container, orient=tk.VERTICAL)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # 日志文本框
        self._log_text = tk.Text(
            log_container,
            height=6,
            width=60,
            state='disabled',
            wrap=tk.WORD,
            font=('Consolas', 9),
            bg='#1e1e1e',
            fg='#d4d4d4',
            yscrollcommand=scrollbar.set,
        )
        self._log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self._log_text.yview)

        # 配置日志颜色标签
        self._log_text.tag_configure('INFO', foreground='#4ec9b0')
        self._log_text.tag_configure('WARNING', foreground='#dcdcaa')
        self._log_text.tag_configure('ERROR', foreground='#f14c4c')
        self._log_text.tag_configure('DEBUG', foreground='#608b4e')

        # 创建并注册日志处理器
        self._log_handler = TkinterLogHandler(max_lines=200)
        self._log_handler.set_text_widget(self._log_text)
        self._log_handler.setLevel(logging.INFO)
        logger.addHandler(self._log_handler)

    def _load_servers(self) -> None:
        """加载服务器列表"""
        from repositories.json_config_repository import JsonConfigRepository
        import os

        config_dir = os.path.join(os.path.expanduser("~"), ".openclaw-proxy")
        json_repo = JsonConfigRepository(config_dir)
        config = json_repo.load_multi()  # 使用 load_multi() 获取 MultiServerConfig

        # 获取所有服务器的运行状态
        statuses = self._container.multi_tunnel_service.get_all_statuses()

        self._server_list.clear_servers()

        for server in config.servers:
            # 检查服务器实际运行状态
            is_connected = False
            if server.id in statuses:
                from services.multi_tunnel_service import ServerTunnelState
                is_connected = statuses[server.id].state == ServerTunnelState.CONNECTED

            self._server_list.add_server(
                server_id=server.id,
                name=server.name,
                host=f"{server.ssh.host}:{server.ssh.port}",
                is_connected=is_connected,
            )

            # 选中第一个服务器
            if self._current_server_id is None:
                self._current_server_id = server.id
                self._server_list.select_server(server.id)

        # 更新全局隧道运行状态
        running_count = self._container.multi_tunnel_service.get_running_count()
        self._is_tunnel_running = running_count > 0
        if self._is_tunnel_running:
            self._toggle_btn.config(text="停止代理", state=tk.NORMAL)
        else:
            self._toggle_btn.config(text="启动代理", state=tk.NORMAL)

    def _on_server_toggle(self, server_id: str) -> None:
        """服务器左键点击 - 启动/停止单个服务器"""
        self._current_server_id = server_id
        self._toggle_single_tunnel(server_id)

    def _toggle_single_tunnel(self, server_id: str) -> None:
        """切换单个服务器隧道状态"""
        if self._server_list.is_server_connected(server_id):
            self._stop_single_tunnel(server_id)
        else:
            self._start_single_tunnel(server_id)

    def _start_single_tunnel(self, server_id: str) -> None:
        """启动单个服务器隧道"""
        self._toggle_btn.config(state=tk.DISABLED)
        self.root.update()

        def do_start():
            success, message = self._container.multi_tunnel_service.start_server(server_id)
            self.root.after(0, lambda: self._on_single_start_complete(server_id, success, message))

        threading.Thread(target=do_start, daemon=True).start()

    def _on_single_start_complete(self, server_id: str, success: bool, message: str) -> None:
        """单个服务器启动完成回调"""
        self._server_list.set_server_connected(server_id, success)

        if success:
            self._is_tunnel_running = True
            self._toggle_btn.config(text="停止代理", state=tk.NORMAL)

            # 自动打开浏览器
            config = self._container.config_repo.load()
            if config.browser.auto_open:
                self._open_browser()
        else:
            self._toggle_btn.config(state=tk.NORMAL)
            messagebox.showerror("错误", f"启动失败: {message}", parent=self.root)

    def _stop_single_tunnel(self, server_id: str) -> None:
        """停止单个服务器隧道"""
        success, message = self._container.multi_tunnel_service.stop_server(server_id)
        self._server_list.set_server_connected(server_id, False)

        # 检查是否还有其他服务器在运行
        running_count = self._container.multi_tunnel_service.get_running_count()
        if running_count == 0:
            self._is_tunnel_running = False
            self._toggle_btn.config(text="启动代理", state=tk.NORMAL)

        if not success:
            messagebox.showerror("错误", f"停止失败: {message}", parent=self.root)

    def _on_server_config(self, server_id: str) -> None:
        """服务器右键菜单 - 打开SSH配置"""
        self._current_server_id = server_id
        self._open_server_config(server_id)

    def _on_server_open_browser(self, server_id: str) -> None:
        """服务器右键菜单 - 浏览器打开"""
        self._current_server_id = server_id
        self._open_browser()

    def _open_server_config(self, server_id: str) -> None:
        """打开指定服务器的SSH配置"""
        from ui.dialogs.config_dialog import ConfigDialog

        # 检查服务器是否正在运行
        if self._server_list.is_server_connected(server_id):
            result = messagebox.askyesno(
                "服务器运行中",
                "该服务器正在运行中，修改配置需要先停止代理。\n\n是否停止代理并打开配置？",
                parent=self.root
            )
            if not result:
                return

            # 停止单个服务器
            self._stop_single_tunnel(server_id)

        ConfigDialog(
            self.root,
            self._container,
            on_save=self._refresh_status,
            server_id=server_id,
        )

    def _check_global_key_exists(self) -> bool:
        """检查全局密钥文件是否存在（从 config.json 的 global.keygen.key_path）"""
        import os
        from utils.path_utils import expand_path
        from repositories.json_config_repository import JsonConfigRepository

        config_dir = os.path.join(os.path.expanduser("~"), ".openclaw-proxy")
        json_repo = JsonConfigRepository(config_dir)
        multi_config = json_repo.load_multi()

        # 检查全局密钥路径
        key_path = multi_config.global_config.keygen.key_path
        if key_path:
            key_path = expand_path(key_path)
            if key_path and os.path.exists(key_path):
                return True
        return False

    def _on_add_server(self) -> None:
        """添加服务器"""
        from ui.dialogs.config_dialog import ConfigDialog

        dialog = ConfigDialog(
            self.root,
            self._container,
            on_save=self._refresh_status,
            is_new=True,
        )
        self.root.wait_window(dialog)

        if dialog.get_result():
            self._load_servers()

    def _setup_callbacks(self) -> None:
        """设置回调"""
        self._presenter.set_on_update_available(self._on_update_available)

    def _check_prerequisites(self) -> None:
        """异步检查前置条件"""
        import threading

        def do_check():
            from utils.network_utils import check_ssh_available

            # 检查SSH可用性
            ssh_available, ssh_error = check_ssh_available()

            # 检查密钥文件是否存在
            key_exists = self._check_global_key_exists()

            # 检查隧道是否运行中
            tunnel_running = self._presenter.is_tunnel_running

            # 回到主线程更新UI
            self.root.after(0, lambda: self._on_prerequisites_checked(
                ssh_available, ssh_error, key_exists, tunnel_running
            ))

        thread = threading.Thread(target=do_check, daemon=True)
        thread.start()

    def _on_prerequisites_checked(
        self,
        ssh_available: bool,
        ssh_error: str,
        key_exists: bool,
        tunnel_running: bool,
    ) -> None:
        """前置条件检查完成回调"""
        if not ssh_available:
            messagebox.showerror("错误", ssh_error, parent=self.root)
            self.root.quit()
            return

        # 检查全局密钥文件是否存在
        if not key_exists:
            result = messagebox.askyesno(
                "密钥未配置",
                "密钥文件不存在或未配置。\n\n是否现在配置密钥？",
                parent=self.root
            )
            if result:
                self._open_security()
            return

        if tunnel_running:
            self._is_tunnel_running = True
            self._toggle_btn.config(text="停止代理", state=tk.NORMAL)

            # 更新服务器列表状态
            if self._current_server_id:
                self._server_list.set_server_connected(self._current_server_id, True)
        else:
            # 启动时不需要进行密钥连接测试
            self._toggle_btn.config(state=tk.NORMAL)

    def _test_connection_async(self) -> None:
        """异步测试SSH连接"""
        self._toggle_btn.config(state=tk.DISABLED)

        def on_result(success: bool, message: str):
            if success:
                self._toggle_btn.config(state=tk.NORMAL)
            else:
                self._toggle_btn.config(state=tk.DISABLED)

        self._presenter.test_connection_async(on_result)

    def _toggle_tunnel(self) -> None:
        """切换隧道状态（启动/停止全部）"""
        if self._is_tunnel_running:
            self._stop_all_tunnels()
        else:
            self._start_all_tunnels()

    def _start_all_tunnels(self) -> None:
        """启动全部隧道"""
        self._toggle_btn.config(state=tk.DISABLED, text="启动中...")
        self.root.update()

        def do_start():
            results = self._container.multi_tunnel_service.start_all()
            self.root.after(0, lambda: self._on_start_all_complete(results))

        threading.Thread(target=do_start, daemon=True).start()

    def _on_start_all_complete(self, results: dict) -> None:
        """启动全部完成回调"""
        success_count = sum(1 for success, _ in results.values() if success)
        total_count = len(results)

        if success_count > 0:
            self._is_tunnel_running = True
            self._toggle_btn.config(text="停止代理", state=tk.NORMAL)

            # 更新服务器列表状态
            for server_id, (success, _) in results.items():
                self._server_list.set_server_connected(server_id, success)

            # 自动打开浏览器
            config = self._container.config_repo.load()
            if config.browser.auto_open:
                self._open_browser()

            if success_count < total_count:
                failed = [name for _, (succ, name) in results.items() if not succ]
                messagebox.showwarning(
                    "部分启动成功",
                    f"成功启动 {success_count}/{total_count} 个服务器\n\n失败: {', '.join(failed)}",
                    parent=self.root
                )
        else:
            self._toggle_btn.config(text="启动代理", state=tk.NORMAL)
            failed = [name for _, (succ, name) in results.items() if not succ]
            messagebox.showerror("错误", f"启动失败:\n{', '.join(failed)}", parent=self.root)

    def _stop_all_tunnels(self) -> None:
        """停止全部隧道"""
        self._toggle_btn.config(state=tk.DISABLED, text="停止中...")
        self.root.update()

        results = self._container.multi_tunnel_service.stop_all()
        success_count = sum(1 for success, _ in results.values() if success)

        self._is_tunnel_running = False
        self._toggle_btn.config(text="启动代理", state=tk.NORMAL)

        # 更新服务器列表状态
        for server_id in results.keys():
            self._server_list.set_server_connected(server_id, False)

        if success_count < len(results):
            logger.warning(f"部分隧道停止失败: {len(results) - success_count} 个")

    def _open_browser(self) -> None:
        """浏览器打开（打开当前服务器所有端口映射）"""
        def on_complete(success: bool):
            if not success:
                messagebox.showwarning("提示", "无法获取token，请检查远程配置", parent=self.root)

        self._presenter.open_browser_all_ports_async(
            server_id=self._current_server_id,
            on_complete=on_complete
        )

    def _fetch_token_async(self) -> None:
        """异步获取token"""
        def on_result(success: bool, token: str):
            if not success:
                logger = __import__('logging').getLogger("openclaw_proxy")
                logger.warning("获取token失败")

        self._presenter.fetch_token_async(on_result)

    def _open_config(self) -> None:
        """打开配置窗口"""
        from ui.dialogs.config_dialog import ConfigDialog

        ConfigDialog(self.root, self._container, on_save=self._refresh_status)

    def _open_security(self) -> None:
        """打开密钥管理弹窗"""
        from ui.dialogs.security_dialog import SecurityDialog

        dialog = SecurityDialog(self.root, self._container, on_save=self._refresh_status)
        self.root.wait_window(dialog)

    def _open_update(self) -> None:
        """打开更新设置弹窗"""
        from ui.dialogs.update_config_dialog import UpdateConfigDialog
        from presenters.config_presenter import ConfigPresenter

        presenter = ConfigPresenter(self._container)
        config = presenter.load_config()
        dialog = UpdateConfigDialog(self.root, config, presenter)
        self.root.wait_window(dialog)
        if dialog.get_result():
            presenter.save_config(config)

    def _refresh_status(self) -> None:
        """刷新状态（配置保存后调用）"""
        self._container.config_repo.load()
        self._load_servers()

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
        # 移除日志处理器
        if hasattr(self, '_log_handler'):
            logger.removeHandler(self._log_handler)

        if self._presenter.is_tunnel_running:
            self._presenter.stop_tunnel()
        self.root.quit()
        self.root.destroy()
