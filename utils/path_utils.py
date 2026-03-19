"""
路径工具函数
"""

import os
from typing import Optional


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


def get_default_key_path(key_type: str = "ed25519", host: str = "openclaw") -> str:
    """
    获取默认的私钥路径

    Args:
        key_type: 密钥类型 (ed25519, rsa)
        host: 主机地址，用于生成密钥文件名

    Returns:
        私钥文件的绝对路径
    """
    ssh_dir = get_default_ssh_dir()
    return os.path.join(ssh_dir, f"{host}_{key_type}")


def get_app_config_dir() -> str:
    """
    获取应用配置目录路径

    Returns:
        配置目录的绝对路径
    """
    return os.path.join(os.path.expanduser("~"), ".openclaw-proxy")


def get_app_log_dir() -> str:
    """
    获取应用日志目录路径

    Returns:
        日志目录的绝对路径
    """
    return os.path.join(get_app_config_dir(), "logs")


def path_exists(path: str) -> bool:
    """
    检查路径是否存在

    Args:
        path: 路径

    Returns:
        是否存在
    """
    return os.path.exists(expand_path(path))


def get_filename(path: str) -> str:
    """
    获取文件名（不含目录）

    Args:
        path: 文件路径

    Returns:
        文件名
    """
    return os.path.basename(expand_path(path))


def find_key_for_host(host: str) -> Optional[str]:
    """
    在系统密钥目录中查找匹配指定 host 的密钥文件

    查找规则：
    1. 查找 {host}_ed25519 或 {host}_rsa 格式的私钥
    2. 优先返回 ed25519 类型

    Args:
        host: 服务器地址

    Returns:
        找到的密钥文件路径，未找到返回 None
    """
    if not host:
        return None

    ssh_dir = get_default_ssh_dir()
    if not os.path.isdir(ssh_dir):
        return None

    # 支持的密钥类型，按优先级排序
    key_types = ["ed25519", "rsa", "ecdsa", "dsa"]

    for key_type in key_types:
        key_path = os.path.join(ssh_dir, f"{host}_{key_type}")
        if os.path.isfile(key_path):
            return key_path

    return None
