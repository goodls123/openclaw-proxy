"""
SSH隧道管理模块
负责SSH端口转发隧道的启动、健康检查、停止
"""

import os
import sys
import time
import signal
import atexit
import subprocess
import logging
from typing import Optional

from utils import (
    check_ssh_available,
    can_connect,
    expand_path,
    ensure_dir,
)
from config_manager import PortMapping

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
        """设置信号处理器"""
        if sys.platform == "win32":
            # Windows下处理Ctrl+C
            signal.signal(signal.SIGINT, self._signal_handler)
            signal.signal(signal.SIGTERM, self._signal_handler)
        else:
            signal.signal(signal.SIGINT, self._signal_handler)
            signal.signal(signal.SIGTERM, self._signal_handler)

    def _signal_handler(self, signum, frame):
        """信号处理函数"""
        logger.info(f"收到退出信号 {signum}，正在停止隧道...")
        self.stop()
        sys.exit(0)

    def check_prerequisites(self) -> tuple[bool, str]:
        """
        检查运行前置条件

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

    def start(self) -> tuple[bool, str]:
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

    def wait_for_connection(self, timeout: int = 10) -> tuple[bool, str]:
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

    def stop(self) -> tuple[bool, str]:
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


def fetch_remote_config(
    host: str,
    port: int,
    user: str,
    key_path: str,
    remote_config_path: str = "~/.openclaw/openclaw.json",
    timeout: int = 10,
) -> tuple[bool, dict, str]:
    """
    从远程主机获取OpenClaw配置

    Args:
        host: SSH服务器地址
        port: SSH端口
        user: 用户名
        key_path: 私钥路径
        remote_config_path: 远程配置文件路径
        timeout: 超时时间

    Returns:
        (是否成功, 配置字典, 消息)
    """
    import json

    key_path = expand_path(key_path)

    # 检查ssh命令
    available, error = check_ssh_available()
    if not available:
        return False, {}, error

    # 检查私钥
    if not os.path.exists(key_path):
        return False, {}, f"私钥文件不存在: {key_path}"

    # 构建SSH命令读取远程配置
    cmd = [
        "ssh",
        "-o", "BatchMode=yes",
        "-o", "StrictHostKeyChecking=accept-new",
        "-o", f"ConnectTimeout={timeout}",
        "-i", key_path,
        "-p", str(port),
        f"{user}@{host}",
        f"cat {remote_config_path}",
    ]

    try:
        # Windows下隐藏控制台窗口
        kwargs = {
            "capture_output": True,
            "timeout": timeout + 5,
        }
        if sys.platform == "win32":
            kwargs["creationflags"] = 0x08000000  # CREATE_NO_WINDOW

        result = subprocess.run(cmd, **kwargs)

        if result.returncode != 0:
            # 尝试多种编码解码错误信息
            try:
                error_msg = result.stderr.decode('utf-8').strip()
            except UnicodeDecodeError:
                error_msg = result.stderr.decode('gbk', errors='replace').strip()
            if "No such file" in error_msg:
                return False, {}, f"远程配置文件不存在: {remote_config_path}"
            return False, {}, f"读取远程配置失败: {error_msg}"

        # 尝试多种编码解码输出
        try:
            output = result.stdout.decode('utf-8')
        except UnicodeDecodeError:
            try:
                output = result.stdout.decode('gbk')
            except UnicodeDecodeError:
                output = result.stdout.decode('utf-8', errors='replace')

        # 解析JSON
        config = json.loads(output)
        logger.info(f"成功获取远程配置: {remote_config_path}")
        return True, config, "获取成功"

    except json.JSONDecodeError as e:
        return False, {}, f"配置文件JSON解析失败: {e}"
    except subprocess.TimeoutExpired:
        return False, {}, "获取远程配置超时"
    except Exception as e:
        return False, {}, f"获取远程配置异常: {str(e)}"


def extract_gateway_token(config: dict) -> tuple[bool, str, str]:
    """
    从配置中提取gateway的auth token

    Args:
        config: 配置字典

    Returns:
        (是否成功, token, 消息)
    """
    try:
        gateway = config.get("gateway", {})
        auth = gateway.get("auth", {})
        token = auth.get("token", "")

        if not token:
            return False, "", "配置中未找到gateway.auth.token"

        logger.info(f"成功提取token: {token[:8]}...")
        return True, token, "提取成功"

    except Exception as e:
        return False, "", f"提取token失败: {str(e)}"
