"""
远程配置仓库
负责从远程服务器获取配置信息
"""

import logging
from typing import Tuple, Any

from repositories.interfaces import IRemoteConfigRepository
from utils.path_utils import expand_path

logger = logging.getLogger("openclaw_proxy")


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
        from ssh_tunnel import fetch_remote_config

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
        from ssh_tunnel import extract_gateway_token

        success, token, message = extract_gateway_token(config)
        return success, token if success else message
