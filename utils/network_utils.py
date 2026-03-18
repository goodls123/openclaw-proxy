"""
网络工具函数
"""

import socket
import shutil
from typing import Tuple


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
