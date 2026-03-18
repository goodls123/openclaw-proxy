"""
状态窗口Presenter
处理状态窗口的业务逻辑
"""

import logging
from typing import Optional, Callable, TYPE_CHECKING

from presenters.base import BasePresenter
from models import TunnelState

if TYPE_CHECKING:
    from app.container import ServiceContainer

logger = logging.getLogger("openclaw_proxy")


class StatusPresenter(BasePresenter):
    """
    状态窗口Presenter

    负责：
    1. 显示隧道状态
    2. 管理token获取
    3. 处理隧道重启/停止
    """

    def __init__(self, container: "ServiceContainer"):
        super().__init__(container)
        self._on_status_changed: Optional[Callable] = None

    # ============== 属性 ==============

    @property
    def tunnel_state(self) -> TunnelState:
        """获取隧道状态"""
        return self.tunnel_service.state

    @property
    def is_running(self) -> bool:
        """隧道是否正在运行"""
        return self.tunnel_service.is_running

    @property
    def pid(self) -> Optional[int]:
        """获取进程ID"""
        return self.tunnel_service.pid

    # ============== 回调设置 ==============

    def set_on_status_changed(self, callback: Callable) -> None:
        """设置状态变化回调"""
        self._on_status_changed = callback

    # ============== 隧道控制 ==============

    def stop_tunnel(self) -> tuple[bool, str]:
        """
        停止隧道

        Returns:
            (是否成功, 消息)
        """
        success, message = self.tunnel_service.stop()

        if self._on_status_changed:
            self._update_ui(self._on_status_changed, self.tunnel_state, message)

        return success, message

    def restart_tunnel(self) -> tuple[bool, str]:
        """
        重启隧道

        Returns:
            (是否成功, 消息)
        """
        config = self.config_repo.load()

        success, message = self.tunnel_service.restart()
        if not success:
            if self._on_status_changed:
                self._update_ui(self._on_status_changed, self.tunnel_state, message)
            return False, message

        success, message = self.tunnel_service.wait_for_connection(
            timeout=config.browser.open_timeout
        )

        if self._on_status_changed:
            self._update_ui(self._on_status_changed, self.tunnel_state, message)

        return success, message

    def restart_tunnel_async(self, callback: Callable[[bool, str], None]) -> None:
        """
        异步重启隧道

        Args:
            callback: 回调函数
        """
        import threading

        def do_restart():
            success, message = self.restart_tunnel()
            self._update_ui(callback, success, message)

        threading.Thread(target=do_restart, daemon=True).start()

    # ============== Token管理 ==============

    def fetch_token_async(self, callback: Callable[[bool, str], None]) -> None:
        """
        异步获取token

        Args:
            callback: 回调函数
        """
        self.token_service.fetch_token_async(callback)

    def get_token(self) -> Optional[str]:
        """获取token"""
        return self.token_service.get_token()

    def get_browser_url(self) -> str:
        """获取浏览器URL（带token）"""
        return self.browser_service.get_url()

    # ============== 浏览器 ==============

    def open_browser(self) -> bool:
        """打开浏览器"""
        return self.browser_service.open()

    def open_browser_async(
        self,
        on_start: Optional[Callable] = None,
        on_complete: Optional[Callable] = None,
    ) -> None:
        """
        异步打开浏览器

        Args:
            on_start: 开始时回调
            on_complete: 完成时回调
        """
        import threading

        def do_open():
            if on_start:
                self._update_ui(on_start)

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

    # ============== 状态信息 ==============

    def get_status_display_info(self) -> dict:
        """
        获取状态显示信息

        Returns:
            显示信息字典
        """
        config = self.config_repo.load()
        return {
            "local_address": f"http://{config.ssh.local_bind_host}:{config.ssh.local_port}",
            "server": f"{config.ssh.user}@{config.ssh.host}:{config.ssh.port}",
            "port_mappings": [str(m) for m in config.ssh.port_mappings],
            "pid": self.pid,
            "state": self.tunnel_state.display_text,
        }

    # ============== 配置窗口 ==============

    def open_config_window(self, parent, on_save: Optional[Callable] = None) -> None:
        """
        打开配置窗口

        Args:
            parent: 父窗口
            on_save: 保存回调
        """
        # 这个方法会在UI层实现时连接
        pass
