"""
配置仓库
负责配置文件的读写和备份管理
使用 JSON 格式存储配置
"""

import os
import logging
from typing import Optional

from models import Config
from repositories.interfaces import IConfigRepository
from repositories.json_config_repository import JsonConfigRepository

logger = logging.getLogger("openclaw_proxy")


class ConfigRepository(IConfigRepository):
    """
    配置仓库（JSON 格式）

    功能：
    1. 加载/保存 JSON 配置文件
    2. 配置备份和恢复
    3. 命令行参数更新

    注意：此类现在是对 JsonConfigRepository 的封装，
    保持接口兼容的同时使用 JSON 格式存储。
    """

    def __init__(self, config_file: str):
        """
        初始化配置仓库

        Args:
            config_file: 配置文件路径（可以是 config.json 或 config.ini，实际使用 JSON）
        """
        self._config_file = config_file
        # 确定配置目录（始终使用 JSON 格式）
        config_dir = os.path.dirname(config_file)
        if not config_dir:
            config_dir = os.path.dirname(os.path.abspath(config_file))
        self._json_repo = JsonConfigRepository(config_dir)
        self._config: Optional[Config] = None

    @property
    def config_file(self) -> str:
        """配置文件路径"""
        return self._json_repo.config_file

    def load(self) -> Config:
        """
        加载配置

        Returns:
            配置对象
        """
        self._config = self._json_repo.load()
        return self._config

    def save(self, config: Config) -> bool:
        """
        保存配置

        Args:
            config: 配置对象

        Returns:
            是否成功
        """
        result = self._json_repo.save(config)
        if result:
            self._config = config
        return result

    def has_backup(self) -> bool:
        """是否有备份"""
        return self._json_repo.has_backup()

    def restore_backup(self) -> bool:
        """恢复备份"""
        return self._json_repo.restore_backup()

    def update_from_args(self, args) -> None:
        """
        从命令行参数更新配置

        Args:
            args: 命令行参数对象
        """
        if self._config is None:
            self.load()

        if hasattr(args, 'host') and args.host is not None:
            self._config.ssh.host = args.host
        if hasattr(args, 'port') and args.port is not None:
            self._config.ssh.port = args.port
        if hasattr(args, 'user') and args.user is not None:
            self._config.ssh.user = args.user
        if hasattr(args, 'local_bind_host') and args.local_bind_host is not None:
            self._config.ssh.local_bind_host = args.local_bind_host
        if hasattr(args, 'local_port') and args.local_port is not None:
            self._config.ssh.local_port = args.local_port
        if hasattr(args, 'remote_host') and args.remote_host is not None:
            self._config.ssh.remote_host = args.remote_host
        if hasattr(args, 'remote_port') and args.remote_port is not None:
            self._config.ssh.remote_port = args.remote_port
        if hasattr(args, 'key_path') and args.key_path is not None:
            self._config.ssh.key_path = args.key_path
        if hasattr(args, 'known_hosts') and args.known_hosts is not None:
            self._config.ssh.known_hosts = args.known_hosts
        if hasattr(args, 'strict_host_key_checking') and args.strict_host_key_checking is not None:
            self._config.ssh.strict_host_key_checking = args.strict_host_key_checking
        if hasattr(args, 'connect_timeout') and args.connect_timeout is not None:
            self._config.ssh.connect_timeout = args.connect_timeout
        if hasattr(args, 'server_alive_interval') and args.server_alive_interval is not None:
            self._config.ssh.server_alive_interval = args.server_alive_interval
        if hasattr(args, 'server_alive_count_max') and args.server_alive_count_max is not None:
            self._config.ssh.server_alive_count_max = args.server_alive_count_max
        if hasattr(args, 'compression') and args.compression:
            self._config.ssh.compression = True

        if hasattr(args, 'no_browser') and args.no_browser:
            self._config.browser.auto_open = False
        if hasattr(args, 'browser_url') and args.browser_url is not None:
            self._config.browser.url = args.browser_url

    def update_token(self, token: str, server_id: str = None) -> bool:
        """
        更新指定服务器的 cached_token

        Args:
            token: 新的 token 值
            server_id: 服务器ID，None 表示默认服务器

        Returns:
            是否成功
        """
        return self._json_repo.update_token(token, server_id)
