"""
主窗口Presenter
处理主窗口的业务逻辑
"""

import logging
from typing import Optional, Callable, TYPE_CHECKING

from presenters.base import BasePresenter
from models import TunnelState, UpdateCheckResult

if TYPE_CHECKING:
    from app.container import ServiceContainer
    from ui.windows.main_window import MainWindow

logger = logging.getLogger("openclaw_proxy")


class MainPresenter(BasePresenter):
    """
    主窗口Presenter

    负责：
    1. 隧道控制（启动/停止）
    2. 连接测试
    3. 更新检查
    4. 浏览器打开
    """

    def __init__(self, container: "ServiceContainer"):
        super().__init__(container)
        self._on_tunnel_state_changed: Optional[Callable] = None
        self._on_update_available: Optional[Callable] = None

    # ============== 属性 ==============

    @property
    def tunnel_state(self) -> TunnelState:
        """获取隧道状态"""
        return self.tunnel_service.state

    @property
    def is_tunnel_running(self) -> bool:
        """隧道是否正在运行"""
        return self.tunnel_service.is_running

    @property
    def current_version(self) -> str:
        """当前版本"""
        return self.update_service.current_version

    # ============== 回调设置 ==============

    def set_on_tunnel_state_changed(self, callback: Callable) -> None:
        """设置隧道状态变化回调"""
        self._on_tunnel_state_changed = callback

    def set_on_update_available(self, callback: Callable) -> None:
        """设置有更新可用回调"""
        self._on_update_available = callback

    # ============== 隧道控制 ==============

    def check_prerequisites(self) -> tuple[bool, str]:
        """
        检查运行前置条件

        Returns:
            (是否满足, 错误信息)
        """
        return self.tunnel_service.check_prerequisites()

    def test_connection_async(self, callback: Callable[[bool, str], None]) -> None:
        """
        异步测试SSH连接

        Args:
            callback: 回调函数 (success, message)
        """
        import threading

        def do_test():
            config = self.config_repo.load()
            success, message = self.key_service.test_connection(
                host=config.ssh.host,
                port=config.ssh.port,
                user=config.ssh.user,
                key_path=config.ssh.key_path,
            )
            self._update_ui(callback, success, message)

        threading.Thread(target=do_test, daemon=True).start()

    def start_tunnel(self) -> tuple[bool, str]:
        """
        启动隧道

        Returns:
            (是否成功, 消息)
        """
        config = self.config_repo.load()

        success, message = self.tunnel_service.start()
        if not success:
            return False, message

        success, message = self.tunnel_service.wait_for_connection(
            timeout=config.browser.open_timeout
        )
        if not success:
            return False, message

        # 通知状态变化
        if self._on_tunnel_state_changed:
            self._update_ui(self._on_tunnel_state_changed, self.tunnel_state)

        return True, "隧道启动成功"

    def start_tunnel_async(
        self,
        callback: Callable[[bool, str], None],
    ) -> None:
        """
        异步启动隧道

        Args:
            callback: 回调函数
        """
        import threading

        def do_start():
            success, message = self.start_tunnel()
            self._update_ui(callback, success, message)

        threading.Thread(target=do_start, daemon=True).start()

    def stop_tunnel(self) -> tuple[bool, str]:
        """
        停止隧道

        Returns:
            (是否成功, 消息)
        """
        success, message = self.tunnel_service.stop()

        # 通知状态变化
        if self._on_tunnel_state_changed:
            self._update_ui(self._on_tunnel_state_changed, self.tunnel_state)

        return success, message

    # ============== Token管理 ==============

    def fetch_token_async(self, callback: Callable[[bool, str], None]) -> None:
        """
        异步获取token

        Args:
            callback: 回调函数
        """
        self.token_service.fetch_token_async(callback)

    def get_browser_url(self) -> str:
        """获取浏览器URL（带token）"""
        return self.browser_service.get_url()

    # ============== 浏览器 ==============

    def open_browser(self) -> bool:
        """打开浏览器"""
        return self.browser_service.open()

    def open_browser_all_ports(self, server_id: Optional[str] = None) -> bool:
        """
        打开服务器所有端口映射对应的浏览器

        Args:
            server_id: 服务器ID，None则使用默认服务器

        Returns:
            是否成功
        """
        return self.browser_service.open_all_port_mappings(server_id)

    def open_browser_async(self, on_complete: Optional[Callable] = None) -> None:
        """
        异步打开浏览器（如果需要先获取token）

        Args:
            on_complete: 完成回调
        """
        import threading

        def do_open():
            # 如果没有token，先获取
            if not self.token_service.token:
                success, _ = self.token_service.fetch_token_sync()
                if not success:
                    if on_complete:
                        self._update_ui(on_complete, False)
                    return

            self.open_browser()
            if on_complete:
                self._update_ui(on_complete, True)

        threading.Thread(target=do_open, daemon=True).start()

    def open_browser_all_ports_async(
        self,
        server_id: Optional[str] = None,
        on_complete: Optional[Callable[[bool], None]] = None,
    ) -> None:
        """
        异步打开服务器所有端口映射的浏览器

        Args:
            server_id: 服务器ID，None则使用默认服务器
            on_complete: 完成回调
        """
        import threading

        def do_open():
            # 如果没有token，先获取
            if not self.token_service.token:
                success, _ = self.token_service.fetch_token_sync()
                if not success:
                    if on_complete:
                        self._update_ui(on_complete, False)
                    return

            self.open_browser_all_ports(server_id)
            if on_complete:
                self._update_ui(on_complete, True)

        threading.Thread(target=do_open, daemon=True).start()

    # ============== 更新检查 ==============

    def check_update_async(self, force: bool = False) -> None:
        """
        异步检查更新

        Args:
            force: 是否强制检查
        """
        def on_result(result: UpdateCheckResult):
            if result.has_update and self._on_update_available:
                self._update_ui(self._on_update_available, result)

        self.update_service.check_for_update_async(on_result, force)

    # ============== 配置 ==============

    def get_config_display_info(self) -> dict:
        """
        获取配置显示信息

        Returns:
            显示信息字典
        """
        config = self.config_repo.load()
        return {
            "server": f"{config.ssh.user}@{config.ssh.host}:{config.ssh.port}",
            "local_port": f"{config.ssh.local_bind_host}:{config.ssh.local_port}",
            "remote_target": f"{config.ssh.remote_host}:{config.ssh.remote_port}",
            "port_mappings": [str(m) for m in config.ssh.port_mappings],
        }

    def open_config_window(self, parent, on_save: Optional[Callable] = None) -> None:
        """
        打开配置窗口

        Args:
            parent: 父窗口
            on_save: 保存回调
        """
        # 这个方法会在UI层实现时连接
        pass
