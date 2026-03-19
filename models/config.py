"""
配置数据模型
"""

import os
from dataclasses import dataclass, field
from typing import Optional, List

from models.port_mapping import PortMapping


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
    port_mappings: List[PortMapping] = field(default_factory=list)

    def __post_init__(self):
        if not self.key_path:
            self.key_path = self._get_default_key_path("ed25519")
        if not self.known_hosts:
            self.known_hosts = os.path.join(self._get_default_ssh_dir(), "known_hosts")

    @staticmethod
    def _get_default_ssh_dir() -> str:
        """获取默认的.ssh目录路径"""
        return os.path.join(os.path.expanduser("~"), ".ssh")

    def _get_default_key_path(self, key_type: str = "ed25519") -> str:
        """获取默认的私钥路径"""
        ssh_dir = self._get_default_ssh_dir()
        return os.path.join(ssh_dir, f"{self.host}_{key_type}")

    def get_primary_mapping(self) -> PortMapping:
        """获取主要端口映射（第一个或默认）"""
        if self.port_mappings:
            return self.port_mappings[0]
        return PortMapping(
            local_bind_host=self.local_bind_host,
            local_port=self.local_port,
            remote_host=self.remote_host,
            remote_port=self.remote_port,
        )


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

    def to_display_dict(self) -> dict:
        """转换为显示用的字典（隐藏敏感信息）"""
        return {
            "ssh": {
                "host": self.ssh.host,
                "port": self.ssh.port,
                "user": self.ssh.user,
                "key_path": self.ssh.key_path,
                "port_mappings": [str(m) for m in self.ssh.port_mappings],
            },
            "browser": {
                "auto_open": self.browser.auto_open,
                "url": self.browser.url,
            },
        }
