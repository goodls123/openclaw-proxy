"""
配置仓库
负责配置文件的读写和备份管理
"""

import os
import configparser
import logging
from typing import Optional, List

from models import Config, SSHConfig, BrowserConfig, KeygenConfig, AppConfig, UpdateConfig, PortMapping
from repositories.interfaces import IConfigRepository
from utils.path_utils import expand_path, get_default_ssh_dir, get_default_key_path

logger = logging.getLogger("openclaw_proxy")


class ConfigRepository(IConfigRepository):
    """
    配置仓库

    功能：
    1. 加载/保存配置文件
    2. 配置备份和恢复
    3. 命令行参数更新
    """

    def __init__(self, config_file: str):
        """
        初始化配置仓库

        Args:
            config_file: 配置文件路径
        """
        self._config_file = config_file
        self._parser = configparser.ConfigParser()
        self._config: Optional[Config] = None

    @property
    def config_file(self) -> str:
        """配置文件路径"""
        return self._config_file

    def load(self) -> Config:
        """
        加载配置

        Returns:
            配置对象
        """
        if not os.path.exists(self._config_file):
            # 创建默认配置并保存
            self._config = Config()
            self.save(self._config)
            return self._config

        self._parser.read(self._config_file, encoding="utf-8")
        self._config = self._parse_config()
        return self._config

    def _parse_config(self) -> Config:
        """解析配置文件"""
        config = Config()

        # 读取SSH配置
        if "ssh" in self._parser:
            ssh = self._parser["ssh"]
            host = ssh.get("host", "localhost")
            config.ssh = SSHConfig(
                host=host,
                port=ssh.getint("port", 22),
                user=ssh.get("user", "root"),
                local_bind_host=ssh.get("local_bind_host", "127.0.0.1"),
                local_port=ssh.getint("local_port", 18789),
                remote_host=ssh.get("remote_host", "127.0.0.1"),
                remote_port=ssh.getint("remote_port", 18789),
                key_path=ssh.get("key_path", get_default_key_path("ed25519", host)),
                known_hosts=ssh.get("known_hosts", os.path.join(get_default_ssh_dir(), "known_hosts")),
                strict_host_key_checking=ssh.get("strict_host_key_checking", "accept-new"),
                connect_timeout=ssh.getint("connect_timeout", 10),
                server_alive_interval=ssh.getint("server_alive_interval", 30),
                server_alive_count_max=ssh.getint("server_alive_count_max", 3),
                compression=ssh.getboolean("compression", False),
            )

        # 读取浏览器配置
        if "browser" in self._parser:
            browser = self._parser["browser"]
            config.browser = BrowserConfig(
                auto_open=browser.getboolean("auto_open", True),
                url=browser.get("url", "http://127.0.0.1:18789"),
                open_timeout=browser.getint("open_timeout", 10),
                auto_fetch_token=browser.getboolean("auto_fetch_token", True),
                remote_config_path=browser.get("remote_config_path", "~/.openclaw/openclaw.json"),
                token=browser.get("token", ""),
            )

        # 读取密钥生成配置
        if "keygen" in self._parser:
            keygen = self._parser["keygen"]
            config.keygen = KeygenConfig(
                key_type=keygen.get("key_type", "ed25519"),
                comment=keygen.get("comment", "openclaw-proxy"),
            )

        # 读取应用配置
        if "app" in self._parser:
            app = self._parser["app"]
            config.app = AppConfig(
                log_level=app.get("log_level", "INFO"),
                log_dir=app.get("log_dir", "logs"),
            )

        # 读取更新配置
        if "update" in self._parser:
            update = self._parser["update"]
            config.update = UpdateConfig(
                auto_check=update.getboolean("auto_check", True),
            )

        # 读取多端口映射配置
        if "port_mappings" in self._parser:
            mappings_str = self._parser["port_mappings"].get("mappings", "")
            if mappings_str.strip():
                config.ssh.port_mappings = []
                for mapping_str in mappings_str.split(";"):
                    mapping_str = mapping_str.strip()
                    if mapping_str:
                        try:
                            config.ssh.port_mappings.append(
                                PortMapping.from_string(mapping_str)
                            )
                        except ValueError:
                            pass

        # 向后兼容：如果没有 port_mappings 但有旧的端口配置，自动迁移
        if not config.ssh.port_mappings and config.ssh.local_port:
            config.ssh.port_mappings = [
                PortMapping(
                    local_bind_host=config.ssh.local_bind_host,
                    local_port=config.ssh.local_port,
                    remote_host=config.ssh.remote_host,
                    remote_port=config.ssh.remote_port,
                )
            ]

        return config

    def save(self, config: Config) -> bool:
        """
        保存配置

        Args:
            config: 配置对象

        Returns:
            是否成功
        """
        try:
            # 先备份现有配置
            self._backup_config()

            self._parser["ssh"] = {
                "host": config.ssh.host,
                "port": str(config.ssh.port),
                "user": config.ssh.user,
                "local_bind_host": config.ssh.local_bind_host,
                "local_port": str(config.ssh.local_port),
                "remote_host": config.ssh.remote_host,
                "remote_port": str(config.ssh.remote_port),
                "key_path": config.ssh.key_path,
                "known_hosts": config.ssh.known_hosts,
                "strict_host_key_checking": config.ssh.strict_host_key_checking,
                "connect_timeout": str(config.ssh.connect_timeout),
                "server_alive_interval": str(config.ssh.server_alive_interval),
                "server_alive_count_max": str(config.ssh.server_alive_count_max),
                "compression": str(config.ssh.compression).lower(),
            }

            self._parser["browser"] = {
                "auto_open": str(config.browser.auto_open).lower(),
                "url": config.browser.url,
                "open_timeout": str(config.browser.open_timeout),
                "auto_fetch_token": str(config.browser.auto_fetch_token).lower(),
                "remote_config_path": config.browser.remote_config_path,
                "token": config.browser.token,
            }

            self._parser["keygen"] = {
                "key_type": config.keygen.key_type,
                "comment": config.keygen.comment,
            }

            self._parser["app"] = {
                "log_level": config.app.log_level,
                "log_dir": config.app.log_dir,
            }

            self._parser["update"] = {
                "auto_check": str(config.update.auto_check).lower(),
            }

            # 保存多端口映射配置
            mappings_str = ";".join([m.to_string() for m in config.ssh.port_mappings])
            self._parser["port_mappings"] = {
                "mappings": mappings_str,
            }

            # 确保目录存在
            config_dir = os.path.dirname(self._config_file)
            if config_dir and not os.path.exists(config_dir):
                os.makedirs(config_dir)

            with open(self._config_file, "w", encoding="utf-8") as f:
                self._parser.write(f)

            self._config = config
            return True

        except Exception as e:
            logger.error(f"保存配置失败: {e}")
            return False

    def _backup_config(self) -> bool:
        """备份当前配置文件"""
        import shutil

        backup_file = self._config_file + ".bak"
        if os.path.exists(self._config_file):
            try:
                shutil.copy2(self._config_file, backup_file)
                return True
            except Exception:
                pass
        return False

    def has_backup(self) -> bool:
        """是否有备份"""
        return os.path.exists(self._config_file + ".bak")

    def restore_backup(self) -> bool:
        """恢复备份"""
        import shutil

        backup_file = self._config_file + ".bak"
        if os.path.exists(backup_file):
            try:
                shutil.copy2(backup_file, self._config_file)
                self.load()  # 重新加载配置
                return True
            except Exception:
                return False
        return False

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
