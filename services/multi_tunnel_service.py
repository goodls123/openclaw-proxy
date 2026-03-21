"""
多隧道管理服务
支持同时管理多个SSH隧道
"""

import logging
import os
import threading
from typing import Optional, Dict, Callable, Tuple, List
from dataclasses import dataclass, field
from enum import Enum

from models.server_config import ServerConfig, MultiServerConfig, PortMappingConfig
from models import TunnelState, TunnelStatus, PortMapping
from services.interfaces import IConfigRepository

logger = logging.getLogger("openclaw_proxy")


class ServerTunnelState(Enum):
    """单个服务器隧道状态"""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"
    STOPPING = "stopping"


@dataclass
class ServerTunnelStatus:
    """单个服务器隧道状态"""
    server_id: str
    server_name: str
    state: ServerTunnelState = ServerTunnelState.DISCONNECTED
    message: str = ""
    pid: Optional[int] = None
    port_mappings: List[PortMappingConfig] = field(default_factory=list)


class ServerTunnel:
    """单个服务器隧道"""

    def __init__(self, server_config: ServerConfig, key_path: str, known_hosts: str):
        self.server_config = server_config
        self._key_path = key_path
        self._known_hosts = known_hosts
        self._process = None
        self._running = False

    def check_prerequisites(self, auto_kill: bool = False) -> Tuple[bool, str]:
        """检查运行前置条件"""
        import os
        from utils.network_utils import check_ssh_available, can_connect, kill_processes_on_port

        # 检查ssh命令
        available, error = check_ssh_available()
        if not available:
            return False, error

        # 检查私钥文件
        if not os.path.exists(self._key_path):
            return False, f"私钥文件不存在: {self._key_path}\n请先生成并部署SSH密钥"

        # 检查所有本地端口是否被占用
        for mapping in self.server_config.get_enabled_port_mappings():
            if can_connect(mapping.local_bind_host, mapping.local_port, timeout=0.5):
                if auto_kill:
                    success, msg = kill_processes_on_port(mapping.local_port)
                    if success:
                        logger.info(f"已自动清理端口 {mapping.local_port}: {msg}")
                    else:
                        return False, f"无法清理端口 {mapping.local_port}: {msg}"
                else:
                    return False, f"本地端口 {mapping.local_port} 已被占用"

        return True, ""

    def build_command(self) -> List[str]:
        """构建SSH命令"""
        import sys

        ssh = self.server_config.ssh
        cmd = ["ssh", "-N"]

        # 添加所有端口映射
        for mapping in self.server_config.get_enabled_port_mappings():
            cmd.extend([
                "-L",
                f"{mapping.local_bind_host}:{mapping.local_port}:{mapping.remote_host}:{mapping.remote_port}"
            ])

        cmd.extend([
            "-p", str(ssh.port),
            "-i", self._key_path,
            "-o", f"StrictHostKeyChecking={ssh.strict_host_key_checking}",
            "-o", f"ConnectTimeout={ssh.connect_timeout}",
            "-o", f"ServerAliveInterval={ssh.server_alive_interval}",
            "-o", f"ServerAliveCountMax={ssh.server_alive_count_max}",
        ])

        if self._known_hosts:
            cmd.extend(["-o", f"UserKnownHostsFile={self._known_hosts}"])

        if ssh.compression:
            cmd.append("-C")

        cmd.append(f"{ssh.user}@{ssh.host}")
        return cmd

    def start(self, auto_kill_port: bool = True) -> Tuple[bool, str]:
        """启动隧道"""
        import subprocess
        import sys
        from utils.path_utils import ensure_dir

        success, error = self.check_prerequisites(auto_kill=auto_kill_port)
        if not success:
            return False, error

        if self._running:
            self.stop()

        cmd = self.build_command()
        logger.debug(f"SSH命令: {' '.join(cmd)}")

        try:
            if self._known_hosts:
                from utils.path_utils import expand_path
                known_hosts_dir = os.path.dirname(expand_path(self._known_hosts))
                ensure_dir(known_hosts_dir)

            kwargs = {
                "stdout": subprocess.PIPE,
                "stderr": subprocess.PIPE,
                "stdin": subprocess.DEVNULL,
            }
            if sys.platform == "win32":
                kwargs["creationflags"] = (
                    subprocess.CREATE_NEW_PROCESS_GROUP | 0x08000000
                )

            self._process = subprocess.Popen(cmd, **kwargs)
            self._running = True

            logger.info(f"SSH隧道已启动 [{self.server_config.name}] (PID: {self._process.pid})")
            return True, f"SSH隧道已启动 (PID: {self._process.pid})"

        except FileNotFoundError:
            return False, "找不到ssh命令"
        except Exception as e:
            logger.error(f"启动SSH隧道失败: {e}")
            return False, f"启动SSH隧道失败: {str(e)}"

    def wait_for_connection(self, timeout: int = 10) -> Tuple[bool, str]:
        """等待隧道连接建立"""
        import time
        from utils.network_utils import can_connect

        if not self._running:
            return False, "隧道未启动"

        logger.info(f"等待隧道连接建立 [{self.server_config.name}] (超时: {timeout}秒)...")

        check_interval = 0.5
        max_checks = int(timeout / check_interval)

        for _ in range(max_checks):
            if self._process.poll() is not None:
                stderr = ""
                if self._process.stderr:
                    stderr = self._process.stderr.read().decode("utf-8", errors="ignore")
                self._running = False
                return False, f"SSH进程意外退出: {stderr[:200] if stderr else '未知错误'}"

            all_connected = True
            for mapping in self.server_config.get_enabled_port_mappings():
                if not can_connect(mapping.local_bind_host, mapping.local_port, timeout=1):
                    all_connected = False
                    break

            if all_connected:
                logger.info(f"隧道连接已建立 [{self.server_config.name}]")
                return True, f"隧道连接已建立 ({len(self.server_config.get_enabled_port_mappings())} 个映射)"

            time.sleep(check_interval)

        return False, f"等待隧道连接超时 ({timeout}秒)"

    def is_running(self) -> bool:
        """检查是否正在运行"""
        if not self._running or not self._process:
            return False
        return self._process.poll() is None

    def stop(self) -> Tuple[bool, str]:
        """停止隧道"""
        import subprocess
        import sys

        if not self._running or not self._process:
            return True, "隧道未运行"

        try:
            pid = self._process.pid
            logger.info(f"正在停止SSH隧道 [{self.server_config.name}] (PID: {pid})...")

            self._process.terminate()

            try:
                self._process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                if sys.platform == "win32":
                    subprocess.run(
                        ["taskkill", "/PID", str(pid), "/T", "/F"],
                        capture_output=True,
                        timeout=10,
                    )
                else:
                    self._process.kill()
                    self._process.wait(timeout=5)

            self._running = False
            self._process = None
            return True, "SSH隧道已停止"

        except Exception as e:
            logger.error(f"停止SSH隧道失败: {e}")
            self._running = False
            self._process = None
            return False, f"停止SSH隧道失败: {str(e)}"


class MultiTunnelService:
    """
    多隧道管理服务

    功能：
    1. 管理多个SSH隧道
    2. 按服务器ID启动/停止隧道
    3. 批量操作（全部启动/停止）
    4. 状态监控
    """

    def __init__(self, config_repo):
        """
        初始化多隧道服务

        Args:
            config_repo: 配置仓库（JsonConfigRepository）
        """
        self._config_repo = config_repo
        self._tunnels: Dict[str, ServerTunnel] = {}
        self._statuses: Dict[str, ServerTunnelStatus] = {}
        self._lock = threading.Lock()

    def get_all_statuses(self) -> Dict[str, ServerTunnelStatus]:
        """获取所有服务器状态"""
        with self._lock:
            config = self._config_repo.load_multi()

            # 确保所有服务器都有状态
            for server in config.servers:
                if server.id not in self._statuses:
                    self._statuses[server.id] = ServerTunnelStatus(
                        server_id=server.id,
                        server_name=server.name,
                        port_mappings=server.get_enabled_port_mappings(),
                    )
                else:
                    # 更新端口映射
                    self._statuses[server.id].port_mappings = server.get_enabled_port_mappings()

            # 更新运行状态
            for server_id, tunnel in self._tunnels.items():
                if server_id in self._statuses:
                    if tunnel.is_running():
                        self._statuses[server_id].state = ServerTunnelState.CONNECTED
                        self._statuses[server_id].pid = tunnel._process.pid if tunnel._process else None
                    else:
                        if self._statuses[server_id].state == ServerTunnelState.CONNECTED:
                            self._statuses[server_id].state = ServerTunnelState.DISCONNECTED

            return self._statuses.copy()

    def get_status(self, server_id: str) -> Optional[ServerTunnelStatus]:
        """获取单个服务器状态"""
        statuses = self.get_all_statuses()
        return statuses.get(server_id)

    def is_running(self, server_id: str) -> bool:
        """检查指定服务器隧道是否运行"""
        with self._lock:
            tunnel = self._tunnels.get(server_id)
            return tunnel.is_running() if tunnel else False

    def get_running_count(self) -> int:
        """获取正在运行的隧道数量"""
        with self._lock:
            return sum(1 for t in self._tunnels.values() if t.is_running())

    def start_server(self, server_id: str, auto_kill_port: bool = True) -> Tuple[bool, str]:
        """
        启动指定服务器的隧道

        Args:
            server_id: 服务器ID
            auto_kill_port: 是否自动清理端口占用

        Returns:
            (是否成功, 消息)
        """
        with self._lock:
            config = self._config_repo.load_multi()
            server = config.get_server_by_id(server_id)

            if not server:
                return False, f"服务器不存在: {server_id}"

            if not server.enabled:
                return False, f"服务器已禁用: {server.name}"

            # 更新状态
            self._update_status(server_id, ServerTunnelState.CONNECTING, "正在启动...")

            # 从 global.keygen 获取密钥路径
            key_path = config.global_config.keygen.key_path
            known_hosts = config.global_config.keygen.known_hosts

        try:
            # 创建隧道（传入密钥路径）
            tunnel = ServerTunnel(server, key_path, known_hosts)

            # 启动
            success, message = tunnel.start(auto_kill_port=auto_kill_port)
            if not success:
                with self._lock:
                    self._update_status(server_id, ServerTunnelState.ERROR, message)
                return False, message

            # 等待连接
            success, message = tunnel.wait_for_connection(timeout=10)
            if not success:
                tunnel.stop()
                with self._lock:
                    self._update_status(server_id, ServerTunnelState.ERROR, message)
                return False, message

            with self._lock:
                self._tunnels[server_id] = tunnel
                self._update_status(
                    server_id,
                    ServerTunnelState.CONNECTED,
                    "已连接",
                    tunnel._process.pid if tunnel._process else None
                )

            return True, f"[{server.name}] 隧道已连接"

        except Exception as e:
            error = f"启动隧道失败: {str(e)}"
            logger.error(error)
            with self._lock:
                self._update_status(server_id, ServerTunnelState.ERROR, error)
            return False, error

    def stop_server(self, server_id: str) -> Tuple[bool, str]:
        """
        停止指定服务器的隧道

        Args:
            server_id: 服务器ID

        Returns:
            (是否成功, 消息)
        """
        with self._lock:
            tunnel = self._tunnels.get(server_id)
            if not tunnel:
                self._update_status(server_id, ServerTunnelState.DISCONNECTED, "未运行")
                return True, "隧道未运行"

            self._update_status(server_id, ServerTunnelState.STOPPING, "正在停止...")

        try:
            success, message = tunnel.stop()

            with self._lock:
                if server_id in self._tunnels:
                    del self._tunnels[server_id]
                self._update_status(
                    server_id,
                    ServerTunnelState.DISCONNECTED,
                    "已停止" if success else message
                )

            return success, message

        except Exception as e:
            error = f"停止隧道失败: {str(e)}"
            logger.error(error)
            with self._lock:
                self._update_status(server_id, ServerTunnelState.ERROR, error)
            return False, error

    def start_all(self, auto_kill_port: bool = True) -> Dict[str, Tuple[bool, str]]:
        """
        启动所有启用的服务器

        Returns:
            {server_id: (success, message)}
        """
        config = self._config_repo.load_multi()
        results = {}

        for server in config.get_enabled_servers():
            results[server.id] = self.start_server(server.id, auto_kill_port)

        return results

    def stop_all(self) -> Dict[str, Tuple[bool, str]]:
        """
        停止所有运行中的隧道

        Returns:
            {server_id: (success, message)}
        """
        with self._lock:
            server_ids = list(self._tunnels.keys())

        results = {}
        for server_id in server_ids:
            results[server_id] = self.stop_server(server_id)

        return results

    def start_server_async(
        self,
        server_id: str,
        callback: Callable[[bool, str], None],
        auto_kill_port: bool = True,
    ) -> None:
        """异步启动服务器隧道"""

        def do_start():
            success, message = self.start_server(server_id, auto_kill_port)
            callback(success, message)

        threading.Thread(target=do_start, daemon=True).start()

    def stop_server_async(
        self,
        server_id: str,
        callback: Callable[[bool, str], None],
    ) -> None:
        """异步停止服务器隧道"""

        def do_stop():
            success, message = self.stop_server(server_id)
            callback(success, message)

        threading.Thread(target=do_stop, daemon=True).start()

    def _update_status(
        self,
        server_id: str,
        state: ServerTunnelState,
        message: str = "",
        pid: Optional[int] = None,
    ) -> None:
        """更新服务器状态（需要在锁内调用）"""
        config = self._config_repo.load_multi()
        server = config.get_server_by_id(server_id)

        if server:
            if server_id not in self._statuses:
                self._statuses[server_id] = ServerTunnelStatus(
                    server_id=server_id,
                    server_name=server.name,
                    port_mappings=server.get_enabled_port_mappings(),
                )

            self._statuses[server_id].state = state
            self._statuses[server_id].message = message
            self._statuses[server_id].pid = pid
