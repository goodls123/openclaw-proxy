"""
公共工具函数模块
包含：日志配置、命令检测、端口探测、路径处理、DPI支持等
"""

import os
import sys
import socket
import shutil
import logging
import ctypes
from datetime import datetime
from typing import Optional, Tuple


def setup_logging(log_level: str = "INFO", log_dir: str = "logs") -> logging.Logger:
    """
    配置日志系统

    Args:
        log_level: 日志级别 (DEBUG, INFO, WARNING, ERROR)
        log_dir: 日志目录

    Returns:
        配置好的Logger实例
    """
    # 创建日志目录
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    # 创建logger
    logger = logging.getLogger("openclaw_proxy")
    logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))

    # 清除已有的handlers
    logger.handlers.clear()

    # 日志格式
    formatter = logging.Formatter(
        "%(asctime)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # 控制台handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # 文件handler - 按日期命名
    log_file = os.path.join(
        log_dir,
        f"openclaw_proxy_{datetime.now().strftime('%Y%m%d')}.log"
    )
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger


def check_ssh_available() -> tuple[bool, str]:
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


def check_ssh_keygen_available() -> tuple[bool, str]:
    """
    检查ssh-keygen命令是否可用

    Returns:
        (是否可用, ssh-keygen命令路径或错误信息)
    """
    keygen_path = shutil.which("ssh-keygen")
    if keygen_path:
        return True, keygen_path
    return False, "未找到ssh-keygen命令，请确保已安装Windows OpenSSH客户端"


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


def expand_path(path: str) -> str:
    """
    展开路径中的环境变量和用户目录

    Args:
        path: 原始路径

    Returns:
        展开后的绝对路径
    """
    # 展开 %USERNAME% 等环境变量
    path = os.path.expandvars(path)
    # 展开 ~ 用户目录
    path = os.path.expanduser(path)
    # 转为绝对路径
    path = os.path.abspath(path)
    return path


def ensure_dir(path: str) -> bool:
    """
    确保目录存在，不存在则创建

    Args:
        path: 目录路径

    Returns:
        是否成功
    """
    try:
        expanded = expand_path(path)
        if not os.path.exists(expanded):
            os.makedirs(expanded)
        return True
    except OSError:
        return False


def get_default_ssh_dir() -> str:
    """
    获取默认的.ssh目录路径

    Returns:
        .ssh目录的绝对路径
    """
    return os.path.join(os.path.expanduser("~"), ".ssh")


def get_default_key_path(key_type: str = "ed25519") -> str:
    """
    获取默认的私钥路径

    Args:
        key_type: 密钥类型 (ed25519, rsa)

    Returns:
        私钥文件的绝对路径
    """
    ssh_dir = get_default_ssh_dir()
    return os.path.join(ssh_dir, f"openclaw_{key_type}")


def sanitize_log_message(message: str) -> str:
    """
    清理日志消息中的敏感信息

    Args:
        message: 原始消息

    Returns:
        清理后的消息
    """
    # 不记录密码相关信息
    sensitive_keywords = ["password", "passphrase", "secret", "token"]
    for keyword in sensitive_keywords:
        if keyword in message.lower():
            return f"[敏感信息已隐藏]"
    return message


# ============== 高分屏DPI支持 ==============

_dpi_info = {
    "enabled": False,
    "awareness_level": None,
    "system_dpi": 96,
    "scale_factor": 1.0,
}


def enable_high_dpi() -> Tuple[bool, str]:
    """
    启用Windows高分屏DPI感知

    在创建Tkinter窗口前调用此函数。

    Returns:
        (是否成功, 消息)
    """
    global _dpi_info

    if sys.platform != "win32":
        _dpi_info["enabled"] = True
        return True, "非Windows系统，跳过DPI设置"

    messages = []

    # 尝试设置 Per Monitor DPI Aware V2 (Windows 10 1703+)
    try:
        # PROCESS_PER_MONITOR_DPI_AWARE = 2
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
        _dpi_info["awareness_level"] = "PerMonitorV2"
        messages.append("已启用 PerMonitorV2 DPI感知")
    except Exception:
        # 尝试设置 System DPI Aware (Windows 8.1+)
        try:
            # PROCESS_SYSTEM_DPI_AWARE = 1
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
            _dpi_info["awareness_level"] = "System"
            messages.append("已启用 System DPI感知")
        except Exception:
            # 回退到老版本API (Windows Vista/7)
            try:
                ctypes.windll.user32.SetProcessDPIAware()
                _dpi_info["awareness_level"] = "Legacy"
                messages.append("已启用 Legacy DPI感知")
            except Exception as e:
                _dpi_info["awareness_level"] = "None"
                messages.append(f"DPI感知设置失败: {e}")

    _dpi_info["enabled"] = True
    return True, "; ".join(messages)


def get_dpi_scale(root=None) -> Tuple[float, int]:
    """
    获取DPI缩放比例

    Args:
        root: Tkinter根窗口（可选，用于获取实际DPI）

    Returns:
        (缩放比例, DPI值)
    """
    global _dpi_info

    if root is not None:
        try:
            # 获取实际DPI
            dpi = root.winfo_fpixels('1i')
            if dpi > 0:
                _dpi_info["system_dpi"] = int(dpi)
                _dpi_info["scale_factor"] = dpi / 96.0
                return _dpi_info["scale_factor"], _dpi_info["system_dpi"]
        except Exception:
            pass

    # 默认值
    return _dpi_info["scale_factor"], _dpi_info["system_dpi"]


def setup_tk_dpi(root) -> Tuple[bool, str]:
    """
    设置Tkinter的DPI缩放

    在创建Tkinter窗口后调用此函数。

    Args:
        root: Tkinter根窗口

    Returns:
        (是否成功, 消息)
    """
    global _dpi_info

    if sys.platform != "win32":
        return True, "非Windows系统，跳过Tk DPI设置"

    messages = []

    try:
        # 获取系统DPI
        dpi = root.winfo_fpixels('1i')
        if dpi > 0:
            _dpi_info["system_dpi"] = int(dpi)
            _dpi_info["scale_factor"] = dpi / 96.0

            # 设置Tk缩放比例
            scale = dpi / 72.0  # Tk默认72 DPI
            root.tk.call('tk', 'scaling', scale)
            messages.append(f"DPI: {int(dpi)}, 缩放: {scale:.2f}x")
        else:
            messages.append("无法获取DPI，使用默认值")
    except Exception as e:
        messages.append(f"DPI设置异常: {e}")

    return True, "; ".join(messages)


def get_dpi_info() -> dict:
    """
    获取DPI信息（用于日志记录）

    Returns:
        DPI信息字典
    """
    return _dpi_info.copy()


def get_scaled_font_size(base_size: int = 10) -> int:
    """
    获取字体大小

    注意：tk scaling 已经处理了 DPI 缩放，不需要手动缩放字体大小，
    否则会导致双重缩放，字体过大。

    Args:
        base_size: 基础字体大小

    Returns:
        字体大小（不进行额外缩放）
    """
    return base_size
