"""
隧道服务
封装SSH隧道管理逻辑
"""

import logging
import threading
from typing import Optional, Tuple, Callable, TYPE_CHECKING

from models import TunnelState, TunnelStatus, PortMapping
from services.interfaces import ITunnelService, IConfigRepository

if TYPE_CHECKING:
    from ssh_tunnel import SSHTunnel

logger = logging.getLogger("openclaw_proxy")


class TunnelService(ITunnelService):
    """
    隧道服务

    功能：
    1. 启动/停止/重启SSH隧道
    2. 监控隧道状态
    3. 检查运行前置条件
    """

    def __init__(self, config_repo: IConfigRepository):
        """
        初始化隧道服务

        Args:
            config_repo: 配置仓库
        """
        self._config_repo = config_repo
        self._tunnel: Optional["SSHTunnel"] = None
        self._status = TunnelStatus(state=TunnelState.DISCONNECTED)

    @property
    def state(self) -> TunnelState:
        """获取当前状态"""
        return self._status.state

    @property
    def is_running(self) -> bool:
        """是否正在运行"""
        return self._status.state in (
            TunnelState.CONNECTED,
            TunnelState.CONNECTING,
            TunnelState.RECONNECTING,
        )

    @property
    def pid(self) -> Optional[int]:
        """获取进程ID"""
        return self._status.pid

    @property
    def status(self) -> TunnelStatus:
        """获取状态对象"""
        return self._status

    def _update_status(
        self,
        state: TunnelState,
        message: str = "",
        pid: Optional[int] = None,
    ) -> None:
        """更新状态"""
        self._status = TunnelStatus(
            state=state,
            message=message or state.display_text,
            pid=pid or self._status.pid,
        )

    def _create_tunnel(self) -> "SSHTunnel":
        """创建隧道实例"""
        from ssh_tunnel import SSHTunnel

        config = self._config_repo.load()
        return SSHTunnel(
            host=config.ssh.host,
            port=config.ssh.port,
            user=config.ssh.user,
            key_path=config.ssh.key_path,
            known_hosts=config.ssh.known_hosts,
            strict_host_key_checking=config.ssh.strict_host_key_checking,
            connect_timeout=config.ssh.connect_timeout,
            server_alive_interval=config.ssh.server_alive_interval,
            server_alive_count_max=config.ssh.server_alive_count_max,
            compression=config.ssh.compression,
            port_mappings=config.ssh.port_mappings,
        )

    def check_prerequisites(self) -> Tuple[bool, str]:
        """
        检查运行前置条件

        Returns:
            (是否满足, 错误信息)
        """
        from utils.network_utils import check_ssh_available

        available, error = check_ssh_available()
        if not available:
            return False, error

        if self._tunnel:
            success, error = self._tunnel.check_prerequisites()
            return success, error

        # 创建临时隧道检查
        tunnel = self._create_tunnel()
        return tunnel.check_prerequisites()

    def start(self) -> Tuple[bool, str]:
        """
        启动隧道

        Returns:
            (是否成功, 消息)
        """
        if self.is_running and self._tunnel:
            logger.warning("隧道已在运行")
            return True, "隧道已在运行"

        self._update_status(TunnelState.CONNECTING, "正在启动...")

        try:
            # 创建隧道
            self._tunnel = self._create_tunnel()

            # 检查前置条件
            success, error = self._tunnel.check_prerequisites()
            if not success:
                self._update_status(TunnelState.ERROR, error)
                return False, error

            # 启动
            success, message = self._tunnel.start()
            if not success:
                self._update_status(TunnelState.ERROR, message)
                return False, message

            self._update_status(
                TunnelState.CONNECTED,
                message,
                self._tunnel._process.pid if self._tunnel._process else None,
            )
            return True, message

        except Exception as e:
            error = f"启动隧道失败: {str(e)}"
            logger.error(error)
            self._update_status(TunnelState.ERROR, error)
            return False, error

    def stop(self) -> Tuple[bool, str]:
        """
        停止隧道

        Returns:
            (是否成功, 消息)
        """
        if not self._tunnel:
            self._update_status(TunnelState.DISCONNECTED)
            return True, "隧道未运行"

        try:
            success, message = self._tunnel.stop()
            self._tunnel = None
            self._update_status(TunnelState.DISCONNECTED, message)
            return success, message
        except Exception as e:
            error = f"停止隧道失败: {str(e)}"
            logger.error(error)
            self._update_status(TunnelState.ERROR, error)
            return False, error

    def restart(self) -> Tuple[bool, str]:
        """
        重启隧道

        Returns:
            (是否成功, 消息)
        """
        self._update_status(TunnelState.RECONNECTING, "正在重启...")

        # 先停止
        if self._tunnel:
            self._tunnel.stop()

        # 重新启动
        return self.start()

    def wait_for_connection(self, timeout: int = 10) -> Tuple[bool, str]:
        """
        等待连接建立

        Args:
            timeout: 超时时间（秒）

        Returns:
            (是否成功, 消息)
        """
        if not self._tunnel:
            return False, "隧道未启动"

        config = self._config_repo.load()
        success, message = self._tunnel.wait_for_connection(timeout=timeout)

        if not success:
            self._update_status(TunnelState.ERROR, message)
            self._tunnel.stop()
            self._tunnel = None

        return success, message

    def start_async(
        self,
        callback: Callable[[bool, str], None],
        wait_timeout: int = 10,
    ) -> None:
        """
        异步启动隧道

        Args:
            callback: 回调函数
            wait_timeout: 等待连接超时
        """

        def do_start():
            success, message = self.start()
            if success:
                success, message = self.wait_for_connection(wait_timeout)
            callback(success, message)

        threading.Thread(target=do_start, daemon=True).start()
