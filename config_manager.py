"""
配置管理模块
负责配置文件的加载、保存、默认值生成
"""

import os
import configparser
from dataclasses import dataclass, field
from typing import Optional
from utils import get_default_key_path, get_default_ssh_dir


@dataclass
class PortMapping:
    """单个端口映射配置"""
    local_bind_host: str = "127.0.0.1"  # 本地绑定地址
    local_port: int = 18789             # 本地端口
    remote_host: str = "127.0.0.1"      # 远程目标地址
    remote_port: int = 18789            # 远程目标端口

    def to_string(self) -> str:
        """序列化为配置字符串：本地地址:本地端口:远程地址:远程端口"""
        return f"{self.local_bind_host}:{self.local_port}:{self.remote_host}:{self.remote_port}"

    @classmethod
    def from_string(cls, s: str) -> "PortMapping":
        """从配置字符串解析"""
        parts = s.strip().split(":")
        if len(parts) == 4:
            return cls(
                local_bind_host=parts[0],
                local_port=int(parts[1]),
                remote_host=parts[2],
                remote_port=int(parts[3]),
            )
        raise ValueError(f"无效的端口映射格式: {s}")


@dataclass
class SSHConfig:
    """SSH连接配置"""
    host: str = "localhost"
    port: int = 22
    user: str = "root"
    local_bind_host: str = "localhost"
    local_port: int = 18789
    remote_host: str = "localhost"
    remote_port: int = 18789
    key_path: str = ""
    known_hosts: str = ""
    strict_host_key_checking: str = "accept-new"
    connect_timeout: int = 10
    server_alive_interval: int = 30
    server_alive_count_max: int = 3
    compression: bool = False
    # 多端口映射列表
    port_mappings: list[PortMapping] = field(default_factory=list)

    def __post_init__(self):
        if not self.key_path:
            self.key_path = get_default_key_path("ed25519")
        if not self.known_hosts:
            self.known_hosts = os.path.join(get_default_ssh_dir(), "known_hosts")


@dataclass
class BrowserConfig:
    """浏览器配置"""
    auto_open: bool = True
    url: str = "http://localhost:18789"
    open_timeout: int = 10
    # Token相关配置
    auto_fetch_token: bool = True  # 是否自动从远程获取token
    remote_config_path: str = "~/.openclaw/openclaw.json"  # 远程配置文件路径
    token: str = ""  # 缓存的token


@dataclass
class KeygenConfig:
    """密钥生成配置"""
    key_type: str = "ed25519"
    comment: str = "openclaw-proxy"


@dataclass
class AppConfig:
    """应用程序配置"""
    log_level: str = "INFO"
    log_dir: str = "logs"


@dataclass
class UpdateConfig:
    """更新配置"""
    auto_check: bool = True  # 是否自动检查更新


@dataclass
class Config:
    """完整配置"""
    ssh: SSHConfig = field(default_factory=SSHConfig)
    browser: BrowserConfig = field(default_factory=BrowserConfig)
    keygen: KeygenConfig = field(default_factory=KeygenConfig)
    app: AppConfig = field(default_factory=AppConfig)
    update: UpdateConfig = field(default_factory=UpdateConfig)


class ConfigManager:
    """配置管理器"""

    DEFAULT_CONFIG_FILE = "config.ini"

    def __init__(self, config_file: Optional[str] = None):
        self.config_file = config_file or self.DEFAULT_CONFIG_FILE
        self.config = Config()
        self._parser = configparser.ConfigParser()

    def load(self) -> Config:
        """加载配置文件"""
        if not os.path.exists(self.config_file):
            self.save()
            return self.config

        self._parser.read(self.config_file, encoding="utf-8")

        # 读取SSH配置
        if "ssh" in self._parser:
            ssh = self._parser["ssh"]
            self.config.ssh = SSHConfig(
                host=ssh.get("host", "192.168.50.114"),
                port=ssh.getint("port", 22),
                user=ssh.get("user", "goodls"),
                local_bind_host=ssh.get("local_bind_host", "127.0.0.1"),
                local_port=ssh.getint("local_port", 18789),
                remote_host=ssh.get("remote_host", "127.0.0.1"),
                remote_port=ssh.getint("remote_port", 18789),
                key_path=ssh.get("key_path", get_default_key_path("ed25519")),
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
            self.config.browser = BrowserConfig(
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
            self.config.keygen = KeygenConfig(
                key_type=keygen.get("key_type", "ed25519"),
                comment=keygen.get("comment", "openclaw-proxy"),
            )

        # 读取应用配置
        if "app" in self._parser:
            app = self._parser["app"]
            self.config.app = AppConfig(
                log_level=app.get("log_level", "INFO"),
                log_dir=app.get("log_dir", "logs"),
            )

        # 读取更新配置
        if "update" in self._parser:
            update = self._parser["update"]
            self.config.update = UpdateConfig(
                auto_check=update.getboolean("auto_check", True),
            )

        # 读取多端口映射配置
        if "port_mappings" in self._parser:
            mappings_str = self._parser["port_mappings"].get("mappings", "")
            if mappings_str.strip():
                self.config.ssh.port_mappings = []
                for mapping_str in mappings_str.split(";"):
                    mapping_str = mapping_str.strip()
                    if mapping_str:
                        try:
                            self.config.ssh.port_mappings.append(
                                PortMapping.from_string(mapping_str)
                            )
                        except ValueError as e:
                            # 忽略无效的映射配置
                            pass

        # 向后兼容：如果没有 port_mappings 但有旧的端口配置，自动迁移
        if not self.config.ssh.port_mappings and self.config.ssh.local_port:
            self.config.ssh.port_mappings = [
                PortMapping(
                    local_bind_host=self.config.ssh.local_bind_host,
                    local_port=self.config.ssh.local_port,
                    remote_host=self.config.ssh.remote_host,
                    remote_port=self.config.ssh.remote_port,
                )
            ]

        return self.config

    def _backup_config(self) -> bool:
        """备份当前配置文件"""
        import shutil
        backup_file = self.config_file + ".bak"
        if os.path.exists(self.config_file):
            try:
                shutil.copy2(self.config_file, backup_file)
                return True
            except Exception:
                pass
        return False

    def has_backup(self) -> bool:
        """检查是否存在备份文件"""
        return os.path.exists(self.config_file + ".bak")

    def restore_backup(self) -> bool:
        """从备份恢复配置"""
        import shutil
        backup_file = self.config_file + ".bak"
        if os.path.exists(backup_file):
            try:
                shutil.copy2(backup_file, self.config_file)
                self.load()  # 重新加载配置
                return True
            except Exception:
                return False
        return False

    def save(self) -> bool:
        """保存配置到文件（自动备份旧配置）"""
        try:
            # 先备份现有配置
            self._backup_config()

            self._parser["ssh"] = {
                "host": self.config.ssh.host,
                "port": str(self.config.ssh.port),
                "user": self.config.ssh.user,
                "local_bind_host": self.config.ssh.local_bind_host,
                "local_port": str(self.config.ssh.local_port),
                "remote_host": self.config.ssh.remote_host,
                "remote_port": str(self.config.ssh.remote_port),
                "key_path": self.config.ssh.key_path,
                "known_hosts": self.config.ssh.known_hosts,
                "strict_host_key_checking": self.config.ssh.strict_host_key_checking,
                "connect_timeout": str(self.config.ssh.connect_timeout),
                "server_alive_interval": str(self.config.ssh.server_alive_interval),
                "server_alive_count_max": str(self.config.ssh.server_alive_count_max),
                "compression": str(self.config.ssh.compression).lower(),
            }

            self._parser["browser"] = {
                "auto_open": str(self.config.browser.auto_open).lower(),
                "url": self.config.browser.url,
                "open_timeout": str(self.config.browser.open_timeout),
                "auto_fetch_token": str(self.config.browser.auto_fetch_token).lower(),
                "remote_config_path": self.config.browser.remote_config_path,
                "token": self.config.browser.token,
            }

            self._parser["keygen"] = {
                "key_type": self.config.keygen.key_type,
                "comment": self.config.keygen.comment,
            }

            self._parser["app"] = {
                "log_level": self.config.app.log_level,
                "log_dir": self.config.app.log_dir,
            }

            self._parser["update"] = {
                "auto_check": str(self.config.update.auto_check).lower(),
            }

            # 保存多端口映射配置
            mappings_str = ";".join([m.to_string() for m in self.config.ssh.port_mappings])
            self._parser["port_mappings"] = {
                "mappings": mappings_str,
            }

            with open(self.config_file, "w", encoding="utf-8") as f:
                self._parser.write(f)

            return True
        except Exception:
            return False

    def update_from_args(self, args) -> None:
        """从命令行参数更新配置"""
        if hasattr(args, 'host') and args.host is not None:
            self.config.ssh.host = args.host
        if hasattr(args, 'port') and args.port is not None:
            self.config.ssh.port = args.port
        if hasattr(args, 'user') and args.user is not None:
            self.config.ssh.user = args.user
        if hasattr(args, 'local_bind_host') and args.local_bind_host is not None:
            self.config.ssh.local_bind_host = args.local_bind_host
        if hasattr(args, 'local_port') and args.local_port is not None:
            self.config.ssh.local_port = args.local_port
        if hasattr(args, 'remote_host') and args.remote_host is not None:
            self.config.ssh.remote_host = args.remote_host
        if hasattr(args, 'remote_port') and args.remote_port is not None:
            self.config.ssh.remote_port = args.remote_port
        if hasattr(args, 'key_path') and args.key_path is not None:
            self.config.ssh.key_path = args.key_path
        if hasattr(args, 'known_hosts') and args.known_hosts is not None:
            self.config.ssh.known_hosts = args.known_hosts
        if hasattr(args, 'strict_host_key_checking') and args.strict_host_key_checking is not None:
            self.config.ssh.strict_host_key_checking = args.strict_host_key_checking
        if hasattr(args, 'connect_timeout') and args.connect_timeout is not None:
            self.config.ssh.connect_timeout = args.connect_timeout
        if hasattr(args, 'server_alive_interval') and args.server_alive_interval is not None:
            self.config.ssh.server_alive_interval = args.server_alive_interval
        if hasattr(args, 'server_alive_count_max') and args.server_alive_count_max is not None:
            self.config.ssh.server_alive_count_max = args.server_alive_count_max
        if hasattr(args, 'compression') and args.compression:
            self.config.ssh.compression = True

        if hasattr(args, 'no_browser') and args.no_browser:
            self.config.browser.auto_open = False
        if hasattr(args, 'browser_url') and args.browser_url is not None:
            self.config.browser.url = args.browser_url
