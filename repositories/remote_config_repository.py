"""
远程配置仓库
负责从远程服务器获取配置信息
"""

import json
import os
import sys
import subprocess
import logging
from typing import Tuple, Any

from repositories.interfaces import IRemoteConfigRepository
from utils.path_utils import expand_path
from utils.network_utils import check_ssh_available

logger = logging.getLogger("openclaw_proxy")


def fetch_remote_config(
    host: str,
    port: int,
    user: str,
    key_path: str,
    remote_config_path: str = "~/.openclaw/openclaw.json",
    timeout: int = 10,
) -> Tuple[bool, dict, str]:
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


def extract_gateway_token(config: dict) -> Tuple[bool, str, str]:
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


class RemoteConfigRepository(IRemoteConfigRepository):
    """
    远程配置仓库

    功能：
    1. 通过SSH获取远程配置文件
    2. 解析配置提取token
    """

    def fetch(
        self,
        host: str,
        port: int,
        user: str,
        key_path: str,
        remote_path: str,
        timeout: int = 10,
    ) -> Tuple[bool, Any, str]:
        """
        获取远程配置

        Args:
            host: SSH服务器地址
            port: SSH端口
            user: 用户名
            key_path: 私钥路径
            remote_path: 远程配置文件路径
            timeout: 超时时间

        Returns:
            (是否成功, 配置字典, 错误信息)
        """
        key_path = expand_path(key_path)

        success, config, error = fetch_remote_config(
            host=host,
            port=port,
            user=user,
            key_path=key_path,
            remote_config_path=remote_path,
            timeout=timeout,
        )

        return success, config, error

    def extract_token(self, config: Any) -> Tuple[bool, str]:
        """
        从配置中提取token

        Args:
            config: 配置字典

        Returns:
            (是否成功, token或错误信息)
        """
        success, token, message = extract_gateway_token(config)
        return success, token if success else message
