"""
隧道服务
封装SSH隧道管理逻辑
"""

import os
import sys
import time
import signal
import atexit
import subprocess
import logging
import threading
from typing import Optional, Tuple, Callable

from models import TunnelState, TunnelStatus, PortMapping
from services.interfaces import ITunnelService, IConfigRepository
from utils.network_utils import check_ssh_available, can_connect, kill_processes_on_port
from utils.path_utils import expand_path, ensure_dir

logger = logging.getLogger("openclaw_proxy")


class SSHTunnel:
    """SSH隧道管理类"""

    def __init__(
        self,
        host: str,
        port: int,
        user: str,
        local_bind_host: str = "127.0.0.1",
        local_port: int = 18789,
        remote_host: str = "127.0.0.1",
        remote_port: int = 18789,
        key_path: str = "",
        known_hosts: str = "",
        strict_host_key_checking: str = "accept-new",
        connect_timeout: int = 10,
        server_alive_interval: int = 30,
        server_alive_count_max: int = 3,
        compression: bool = False,
        port_mappings: Optional[list[PortMapping]] = None,
    ):
        """
        初始化SSH隧道

        Args:
            host: SSH服务器地址
            port: SSH端口
            user: 用户名
            local_bind_host: 本地绑定地址（向后兼容）
            local_port: 本地端口（向后兼容）
            remote_host: 远程目标地址（向后兼容）
            remote_port: 远程目标端口（向后兼容）
            key_path: 私钥文件路径
            known_hosts: 已知主机文件路径
            strict_host_key_checking: 主机密钥校验策略
            connect_timeout: 连接超时
            server_alive_interval: 保活间隔
            server_alive_count_max: 保活失败次数
            compression: 是否启用压缩
            port_mappings: 多端口映射列表
        """
        self.host = host
        self.port = port
        self.user = user
        self.key_path = expand_path(key_path)
        self.known_hosts = expand_path(known_hosts) if known_hosts else ""
        self.strict_host_key_checking = strict_host_key_checking
        self.connect_timeout = connect_timeout
        self.server_alive_interval = server_alive_interval
        self.server_alive_count_max = server_alive_count_max
        self.compression = compression

        # 处理端口映射
        if port_mappings:
            self.port_mappings = port_mappings
        else:
            # 向后兼容：从单一参数创建
            self.port_mappings = [
                PortMapping(
                    local_bind_host=local_bind_host,
                    local_port=local_port,
                    remote_host=remote_host,
                    remote_port=remote_port,
                )
            ]

        # 保留旧属性以兼容
        self.local_bind_host = self.port_mappings[0].local_bind_host if self.port_mappings else local_bind_host
        self.local_port = self.port_mappings[0].local_port if self.port_mappings else local_port
        self.remote_host = self.port_mappings[0].remote_host if self.port_mappings else remote_host
        self.remote_port = self.port_mappings[0].remote_port if self.port_mappings else remote_port

        self._process: Optional[subprocess.Popen] = None
        self._running = False

        # 注册退出清理
        atexit.register(self.stop)
        self._setup_signal_handlers()

    def _setup_signal_handlers(self):
        """设置信号处理器（仅在主线程中）"""
        try:
            if sys.platform == "win32":
                # Windows下处理Ctrl+C
                signal.signal(signal.SIGINT, self._signal_handler)
                signal.signal(signal.SIGTERM, self._signal_handler)
            else:
                signal.signal(signal.SIGINT, self._signal_handler)
                signal.signal(signal.SIGTERM, self._signal_handler)
        except ValueError:
            # 不在主线程中，跳过信号处理
            pass

    def _signal_handler(self, signum, frame):
        """信号处理函数"""
        logger.info(f"收到退出信号 {signum}，正在停止隧道...")
        self.stop()
        sys.exit(0)

    def check_prerequisites(self, auto_kill: bool = False) -> Tuple[bool, str]:
        """
        检查运行前置条件

        Args:
            auto_kill: 是否自动终止占用端口的进程

        Returns:
            (是否满足, 错误信息)
        """
        # 检查ssh命令
        available, error = check_ssh_available()
        if not available:
            return False, error

        # 检查私钥文件
        if not os.path.exists(self.key_path):
            return False, f"私钥文件不存在: {self.key_path}\n请先生成并部署SSH密钥"

        # 检查所有本地端口是否被占用
        for mapping in self.port_mappings:
            if can_connect(mapping.local_bind_host, mapping.local_port, timeout=0.5):
                if auto_kill:
                    # 自动终止占用端口的进程
                    success, msg = kill_processes_on_port(mapping.local_port)
                    if success:
                        logger.info(f"已自动清理端口 {mapping.local_port}: {msg}")
                    else:
                        return False, f"无法清理端口 {mapping.local_port}: {msg}"
                else:
                    return False, f"本地端口 {mapping.local_port} 已被占用"

        return True, ""

    def build_command(self) -> list[str]:
        """
        构建SSH命令

        Returns:
            命令参数列表
        """
        cmd = [
            "ssh",
            "-N",  # 不执行远程命令
        ]

        # 添加所有端口映射
        for mapping in self.port_mappings:
            cmd.extend([
                "-L",
                f"{mapping.local_bind_host}:{mapping.local_port}:{mapping.remote_host}:{mapping.remote_port}"
            ])

        cmd.extend([
            "-p", str(self.port),
            "-i", self.key_path,
            "-o", f"StrictHostKeyChecking={self.strict_host_key_checking}",
            "-o", f"ConnectTimeout={self.connect_timeout}",
            "-o", f"ServerAliveInterval={self.server_alive_interval}",
            "-o", f"ServerAliveCountMax={self.server_alive_count_max}",
        ])

        # 添加known_hosts配置
        if self.known_hosts:
            cmd.extend(["-o", f"UserKnownHostsFile={self.known_hosts}"])

        # 压缩选项
        if self.compression:
            cmd.append("-C")

        # 目标地址
        cmd.append(f"{self.user}@{self.host}")

        return cmd

    def start(self) -> Tuple[bool, str]:
        """
        启动SSH隧道

        Returns:
            (是否成功, 消息)
        """
        # 检查前置条件
        success, error = self.check_prerequisites()
        if not success:
            return False, error

        # 如果已经在运行，先停止
        if self._running:
            self.stop()

        # 构建命令
        cmd = self.build_command()
        logger.debug(f"SSH命令: {' '.join(cmd)}")

        try:
            # 确保known_hosts目录存在
            if self.known_hosts:
                known_hosts_dir = os.path.dirname(self.known_hosts)
                ensure_dir(known_hosts_dir)

            # 启动SSH进程
            # Windows下使用CREATE_NEW_PROCESS_GROUP创建新进程组
            kwargs = {
                "stdout": subprocess.PIPE,
                "stderr": subprocess.PIPE,
                "stdin": subprocess.DEVNULL,
            }
            if sys.platform == "win32":
                # CREATE_NO_WINDOW (0x08000000) 隐藏控制台窗口
                # CREATE_NEW_PROCESS_GROUP 创建新进程组，便于终止子进程
                kwargs["creationflags"] = (
                    subprocess.CREATE_NEW_PROCESS_GROUP | 0x08000000  # CREATE_NO_WINDOW
                )

            self._process = subprocess.Popen(cmd, **kwargs)
            self._running = True

            logger.info(f"SSH隧道进程已启动 (PID: {self._process.pid})")
            return True, f"SSH隧道已启动 (PID: {self._process.pid})"

        except FileNotFoundError:
            return False, "找不到ssh命令"
        except Exception as e:
            logger.error(f"启动SSH隧道失败: {e}")
            return False, f"启动SSH隧道失败: {str(e)}"

    def wait_for_connection(self, timeout: int = 10) -> Tuple[bool, str]:
        """
        等待隧道连接建立

        Args:
            timeout: 超时时间（秒）

        Returns:
            (是否成功, 消息)
        """
        if not self._running:
            return False, "隧道未启动"

        logger.info(f"等待隧道连接建立 (超时: {timeout}秒)...")

        # 轮询检测本地端口
        check_interval = 0.5
        max_checks = int(timeout / check_interval)

        for i in range(max_checks):
            # 检查进程是否还在运行
            if self._process.poll() is not None:
                # 进程已退出
                stderr = ""
                if self._process.stderr:
                    stderr = self._process.stderr.read().decode("utf-8", errors="ignore")
                self._running = False
                logger.error(f"SSH进程已退出: {stderr}")
                return False, f"SSH进程意外退出: {stderr[:200] if stderr else '未知错误'}"

            # 检测所有本地端口
            all_connected = True
            for mapping in self.port_mappings:
                if not can_connect(mapping.local_bind_host, mapping.local_port, timeout=1):
                    all_connected = False
                    break

            if all_connected:
                logger.info(f"隧道连接已建立 ({len(self.port_mappings)} 个映射)")
                return True, f"隧道连接已建立 ({len(self.port_mappings)} 个映射)"

            time.sleep(check_interval)

        logger.warning("等待隧道连接超时")
        return False, f"等待隧道连接超时 ({timeout}秒)"

    def is_running(self) -> bool:
        """
        检查隧道是否正在运行

        Returns:
            是否正在运行
        """
        if not self._running or not self._process:
            return False

        # 检查进程状态
        return self._process.poll() is None

    def stop(self) -> Tuple[bool, str]:
        """
        停止SSH隧道

        Returns:
            (是否成功, 消息)
        """
        if not self._running or not self._process:
            return True, "隧道未运行"

        try:
            pid = self._process.pid
            logger.info(f"正在停止SSH隧道 (PID: {pid})...")

            # 首先尝试优雅终止
            self._process.terminate()

            # 等待进程退出
            try:
                self._process.wait(timeout=3)
                logger.info(f"SSH进程已正常退出 (PID: {pid})")
            except subprocess.TimeoutExpired:
                # 超时后强制终止
                logger.warning(f"SSH进程未响应，强制终止 (PID: {pid})...")
                if sys.platform == "win32":
                    # Windows下使用taskkill确保子进程也被终止
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

    def get_status(self) -> dict:
        """
        获取隧道状态信息

        Returns:
            状态字典
        """
        return {
            "running": self.is_running(),
            "pid": self._process.pid if self._process else None,
            "host": self.host,
            "port": self.port,
            "local_port": self.local_port,
            "remote_host": self.remote_host,
            "remote_port": self.remote_port,
        }

    def __enter__(self):
        """上下文管理器入口"""
        success, message = self.start()
        if not success:
            raise RuntimeError(message)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.stop()
        return False


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
        self._tunnel: Optional[SSHTunnel] = None
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

    def _create_tunnel(self) -> SSHTunnel:
        """创建隧道实例"""
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

    def check_prerequisites(self, auto_kill: bool = False) -> Tuple[bool, str]:
        """
        检查运行前置条件

        Args:
            auto_kill: 是否自动终止占用端口的进程

        Returns:
            (是否满足, 错误信息)
        """
        available, error = check_ssh_available()
        if not available:
            return False, error

        if self._tunnel:
            success, error = self._tunnel.check_prerequisites(auto_kill=auto_kill)
            return success, error

        # 创建临时隧道检查
        tunnel = self._create_tunnel()
        return tunnel.check_prerequisites(auto_kill=auto_kill)

    def start(self, auto_kill_port: bool = True) -> Tuple[bool, str]:
        """
        启动隧道

        Args:
            auto_kill_port: 是否自动终止占用端口的进程

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

            # 检查前置条件（自动清理端口占用）
            success, error = self._tunnel.check_prerequisites(auto_kill=auto_kill_port)
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

        # 先停止并清理
        if self._tunnel:
            self._tunnel.stop()
            self._tunnel = None

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
