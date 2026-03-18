"""
网络工具函数
"""

import os
import socket
import shutil
import subprocess
import sys
from typing import Tuple, Optional, List


def can_connect(host: str, port: int, timeout: float = 1.0) -> bool:
    """
    检测指定主机端口是否可连接

    Args:
        host: 主机地址
        port: 端口号
        timeout: 超时时间（秒）

    Returns:
        是否可连接
    """
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except (socket.error, OSError):
        return False


def check_ssh_available() -> Tuple[bool, str]:
    """
    检查系统ssh命令是否可用

    Returns:
        (是否可用, ssh命令路径或错误信息)
    """
    # Windows上查找ssh.exe
    ssh_path = shutil.which("ssh")
    if ssh_path:
        return True, ssh_path
    return False, "未找到ssh命令，请确保已安装Windows OpenSSH客户端"


def check_ssh_keygen_available() -> Tuple[bool, str]:
    """
    检查ssh-keygen命令是否可用

    Returns:
        (是否可用, ssh-keygen命令路径或错误信息)
    """
    keygen_path = shutil.which("ssh-keygen")
    if keygen_path:
        return True, keygen_path
    return False, "未找到ssh-keygen命令，请确保已安装Windows OpenSSH客户端"


def test_tcp_connection(host: str, port: int, timeout: float = 5.0) -> Tuple[bool, str]:
    """
    测试TCP连接

    Args:
        host: 主机地址
        port: 端口号
        timeout: 超时时间

    Returns:
        (是否成功, 消息)
    """
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        sock.close()

        if result == 0:
            return True, "主机可达"
        else:
            return False, f"无法连接到 {host}:{port}"
    except socket.timeout:
        return False, "连接超时"
    except socket.gaierror as e:
        return False, f"主机名解析失败: {str(e)}"
    except Exception as e:
        return False, f"连接失败: {str(e)}"


def get_local_ip() -> str:
    """
    获取本机IP地址

    Returns:
        本机IP地址
    """
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def find_processes_on_port(port: int) -> List[int]:
    """
    查找占用指定端口的进程PID列表

    Args:
        port: 端口号

    Returns:
        占用该端口的进程PID列表
    """
    pids = []

    if sys.platform == "win32":
        try:
            # Windows: 使用 netstat -ano 查找
            result = subprocess.run(
                f'netstat -ano | findstr ":{port}"',
                capture_output=True,
                text=True,
                shell=True,
                timeout=10,
            )

            for line in result.stdout.strip().split('\n'):
                if 'LISTENING' in line:
                    parts = line.split()
                    if parts:
                        pid = int(parts[-1])
                        if pid > 0 and pid not in pids:
                            pids.append(pid)
        except Exception:
            pass
    else:
        try:
            # Linux/Mac: 使用 lsof
            result = subprocess.run(
                ['lsof', '-t', '-i', f':{port}'],
                capture_output=True,
                text=True,
                timeout=10,
            )
            for line in result.stdout.strip().split('\n'):
                if line.strip():
                    pid = int(line.strip())
                    if pid > 0 and pid not in pids:
                        pids.append(pid)
        except Exception:
            pass

    return pids


def kill_process(pid: int, force: bool = True) -> Tuple[bool, str]:
    """
    终止指定进程

    Args:
        pid: 进程ID
        force: 是否强制终止

    Returns:
        (是否成功, 消息)
    """
    try:
        if sys.platform == "win32":
            # Windows: 使用 taskkill
            cmd = ["taskkill", "/PID", str(pid)]
            if force:
                cmd.append("/F")
            result = subprocess.run(cmd, capture_output=True, timeout=10)

            if result.returncode == 0:
                return True, f"进程 {pid} 已终止"
            else:
                return False, f"终止进程 {pid} 失败"
        else:
            # Linux/Mac: 使用 kill
            import signal
            sig = signal.SIGKILL if force else signal.SIGTERM
            os.kill(pid, sig)
            return True, f"进程 {pid} 已终止"
    except ProcessLookupError:
        return True, f"进程 {pid} 不存在"
    except Exception as e:
        return False, f"终止进程 {pid} 异常: {str(e)}"


def kill_processes_on_port(port: int, force: bool = True) -> Tuple[bool, str]:
    """
    终止占用指定端口的所有进程

    Args:
        port: 端口号
        force: 是否强制终止

    Returns:
        (是否成功, 消息)
    """
    pids = find_processes_on_port(port)

    if not pids:
        return True, f"端口 {port} 未被占用"

    success_count = 0
    messages = []

    for pid in pids:
        success, msg = kill_process(pid, force)
        if success:
            success_count += 1
        messages.append(msg)

    if success_count == len(pids):
        return True, f"已终止 {success_count} 个占用端口 {port} 的进程"
    else:
        return False, "; ".join(messages)


def is_port_available(port: int, host: str = "127.0.0.1") -> bool:
    """
    检查端口是否可用（未被占用）

    Args:
        port: 端口号
        host: 主机地址

    Returns:
        端口是否可用
    """
    return not can_connect(host, port, timeout=0.5)
