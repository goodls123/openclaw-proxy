"""
多服务器配置数据模型
支持多台远程主机的配置管理
"""

import os
import uuid
from dataclasses import dataclass, field
from typing import Optional, List
from datetime import datetime


@dataclass
class PortMappingConfig:
    """端口映射配置（增强版）"""

    id: str = ""
    name: str = ""
    enabled: bool = True
    local_bind_host: str = "127.0.0.1"
    local_port: int = 18789
    remote_host: str = "127.0.0.1"
    remote_port: int = 18789
    is_openclaw: bool = False

    def __post_init__(self):
        if not self.id:
            self.id = self._generate_id()

    @staticmethod
    def _generate_id() -> str:
        """生成唯一ID"""
        return f"pm-{uuid.uuid4().hex[:8]}"

    def to_string(self) -> str:
        """序列化为配置字符串：本地地址:本地端口:远程地址:远程端口"""
        return f"{self.local_bind_host}:{self.local_port}:{self.remote_host}:{self.remote_port}"

    @classmethod
    def from_string(cls, s: str, name: str = "") -> "PortMappingConfig":
        """从配置字符串解析"""
        parts = s.strip().split(":")
        if len(parts) == 4:
            return cls(
                name=name,
                local_bind_host=parts[0],
                local_port=int(parts[1]),
                remote_host=parts[2],
                remote_port=int(parts[3]),
            )
        raise ValueError(f"无效的端口映射格式: {s}")

    def to_display_string(self) -> str:
        """生成显示用的字符串"""
        return f"{self.local_bind_host}:{self.local_port} → {self.remote_host}:{self.remote_port}"

    def __str__(self) -> str:
        return self.to_display_string()


@dataclass
class SSHConfig:
    """SSH连接配置（每个服务器独立）"""

    host: str = "localhost"
    port: int = 22
    user: str = "root"
    # key_path 和 known_hosts 从 global.keygen 获取，不在此存储
    strict_host_key_checking: str = "accept-new"
    connect_timeout: int = 10
    server_alive_interval: int = 30
    server_alive_count_max: int = 3
    compression: bool = False


@dataclass
class TokenConfig:
    """Token配置"""

    auto_fetch: bool = True
    remote_config_path: str = "~/.openclaw/openclaw.json"
    cached_token: str = ""


@dataclass
class BrowserConfig:
    """浏览器配置（每个服务器可独立配置）"""

    enabled: bool = True
    auto_open: bool = True
    url_template: str = "http://{local_host}:{local_port}"
    open_timeout: int = 10
    token: TokenConfig = field(default_factory=TokenConfig)

    def get_url(self, local_host: str, local_port: int) -> str:
        """生成实际URL"""
        return self.url_template.format(
            local_host=local_host,
            local_port=local_port
        )


@dataclass
class ServerConfig:
    """单个服务器配置"""

    id: str = ""
    name: str = ""
    enabled: bool = True
    auto_run: bool = False  # 应用启动时自动运行

    ssh: SSHConfig = field(default_factory=SSHConfig)
    port_mappings: List[PortMappingConfig] = field(default_factory=list)
    browser: Optional[BrowserConfig] = None

    notes: str = ""

    def __post_init__(self):
        if not self.id:
            self.id = self._generate_id()
        if not self.name:
            self.name = self.ssh.host

    @staticmethod
    def _generate_id() -> str:
        """生成唯一ID"""
        return f"srv-{uuid.uuid4().hex[:8]}"

    def get_enabled_port_mappings(self) -> List[PortMappingConfig]:
        """获取启用的端口映射"""
        return [pm for pm in self.port_mappings if pm.enabled]

    def get_primary_mapping(self) -> Optional[PortMappingConfig]:
        """获取主要端口映射（第一个启用的）"""
        enabled = self.get_enabled_port_mappings()
        return enabled[0] if enabled else None


@dataclass
class AppConfig:
    """应用配置"""

    log_level: str = "INFO"
    log_dir: str = "logs"


@dataclass
class UpdateConfig:
    """更新配置"""

    auto_check: bool = True


@dataclass
class KeygenConfig:
    """密钥生成配置"""

    key_type: str = "ed25519"
    comment: str = "openclaw-proxy"
    key_path: str = ""
    known_hosts: str = ""


@dataclass
class GlobalConfig:
    """全局配置"""

    app: AppConfig = field(default_factory=AppConfig)
    update: UpdateConfig = field(default_factory=UpdateConfig)
    keygen: KeygenConfig = field(default_factory=KeygenConfig)


@dataclass
class MigrationInfo:
    """迁移信息"""

    migrated_from: Optional[str] = None  # "ini" or None
    migration_date: Optional[datetime] = None
    original_config_path: str = ""


@dataclass
class MultiServerConfig:
    """完整的多服务器配置"""

    version: str = "2.0"
    global_config: GlobalConfig = field(default_factory=GlobalConfig)
    servers: List[ServerConfig] = field(default_factory=list)
    migration: Optional[MigrationInfo] = None

    def get_default_server(self) -> Optional[ServerConfig]:
        """获取默认服务器（第一个启用的服务器）"""
        for server in self.servers:
            if server.enabled:
                return server
        return None

    def get_auto_run_servers(self) -> List[ServerConfig]:
        """获取所有设置了 auto_run 的服务器"""
        return [s for s in self.servers if s.enabled and s.auto_run]

    def get_server_by_id(self, server_id: str) -> Optional[ServerConfig]:
        """通过ID获取服务器"""
        for server in self.servers:
            if server.id == server_id:
                return server
        return None

    def get_enabled_servers(self) -> List[ServerConfig]:
        """获取所有启用的服务器"""
        return [s for s in self.servers if s.enabled]

    def to_legacy_config(self) -> "Config":
        """转换为旧版Config（用于向后兼容）"""
        from models.config import Config as LegacyConfig
        from models.config import SSHConfig as LegacySSH
        from models.config import BrowserConfig as LegacyBrowser
        from models.port_mapping import PortMapping

        default_server = self.get_default_server()
        if not default_server:
            return LegacyConfig()

        legacy = LegacyConfig()

        # SSH配置（key_path 和 known_hosts 从 global.keygen 获取）
        legacy.ssh = LegacySSH(
            host=default_server.ssh.host,
            port=default_server.ssh.port,
            user=default_server.ssh.user,
            key_path=self.global_config.keygen.key_path,
            known_hosts=self.global_config.keygen.known_hosts,
            strict_host_key_checking=default_server.ssh.strict_host_key_checking,
            connect_timeout=default_server.ssh.connect_timeout,
            server_alive_interval=default_server.ssh.server_alive_interval,
            server_alive_count_max=default_server.ssh.server_alive_count_max,
            compression=default_server.ssh.compression,
        )

        # 端口映射
        primary = default_server.get_primary_mapping()
        if primary:
            legacy.ssh.local_bind_host = primary.local_bind_host
            legacy.ssh.local_port = primary.local_port
            legacy.ssh.remote_host = primary.remote_host
            legacy.ssh.remote_port = primary.remote_port

        # 端口映射列表
        legacy.ssh.port_mappings = [
            PortMapping(
                local_bind_host=pm.local_bind_host,
                local_port=pm.local_port,
                remote_host=pm.remote_host,
                remote_port=pm.remote_port,
                is_openclaw=pm.is_openclaw,
            )
            for pm in default_server.port_mappings
        ]

        # 浏览器配置
        if default_server.browser:
            primary_mapping = default_server.get_primary_mapping()
            url = default_server.browser.get_url(
                primary_mapping.local_bind_host if primary_mapping else "127.0.0.1",
                primary_mapping.local_port if primary_mapping else 18789
            )
            legacy.browser = LegacyBrowser(
                auto_open=default_server.browser.auto_open,
                url=url,
                open_timeout=default_server.browser.open_timeout,
                auto_fetch_token=default_server.browser.token.auto_fetch,
                remote_config_path=default_server.browser.token.remote_config_path,
                token=default_server.browser.token.cached_token,
            )

        # 全局配置
        legacy.keygen.key_type = self.global_config.keygen.key_type
        legacy.keygen.comment = self.global_config.keygen.comment
        legacy.app.log_level = self.global_config.app.log_level
        legacy.app.log_dir = self.global_config.app.log_dir
        legacy.update.auto_check = self.global_config.update.auto_check

        return legacy
