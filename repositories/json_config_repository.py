"""
JSON配置仓库
支持多服务器配置的读写
"""

import os
import json
import shutil
import logging
from typing import Optional, List, Tuple, Union

from models.server_config import (
    MultiServerConfig,
    ServerConfig,
    GlobalConfig,
    AppConfig,
    UpdateConfig,
    KeygenConfig,
    SSHConfig,
    BrowserConfig,
    TokenConfig,
    PortMappingConfig,
)
from repositories.interfaces import IConfigRepository
from models import Config  # 旧版配置模型

logger = logging.getLogger("openclaw_proxy")


class JsonConfigRepository(IConfigRepository):
    """
    JSON配置仓库

    同时支持：
    - 新版 MultiServerConfig（多服务器配置）
    - 旧版 Config（通过 IConfigRepository 接口兼容）

    注意：为了兼容 IConfigRepository 接口，load() 方法返回的是旧版 Config。
    如需获取 MultiServerConfig，请使用 load_multi() 方法。
    """

    DEFAULT_CONFIG_FILE = "config.json"

    def __init__(self, config_dir: str):
        """
        初始化JSON配置仓库

        Args:
            config_dir: 配置文件目录
        """
        self._multi_config_dir = config_dir
        self._json_config_file = os.path.join(config_dir, self.DEFAULT_CONFIG_FILE)
        self._multi_config: Optional[MultiServerConfig] = None

    @property
    def config_file(self) -> str:
        """配置文件路径"""
        return self._json_config_file

    def load(self) -> Config:
        """
        加载配置（实现 IConfigRepository 接口）

        Returns:
            旧版配置对象
        """
        multi_config = self.load_multi()
        return multi_config.to_legacy_config()

    def load_multi(self) -> MultiServerConfig:
        """
        加载多服务器配置

        Returns:
            多服务器配置对象
        """
        # 加载JSON配置
        if os.path.exists(self._json_config_file):
            self._multi_config = self._load_json()
            return self._multi_config

        # 创建默认配置
        self._multi_config = self._create_default_config()
        self.save(self._multi_config)
        return self._multi_config

    def _load_json(self) -> MultiServerConfig:
        """加载JSON配置文件"""
        with open(self._json_config_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return self._parse_json(data)

    def _parse_json(self, data: dict) -> MultiServerConfig:
        """解析JSON数据为配置对象"""
        config = MultiServerConfig()
        config.version = data.get("version", "2.0")

        # 解析全局配置
        global_data = data.get("global", {})
        config.global_config = self._parse_global(global_data)

        # 解析服务器列表
        servers_data = data.get("servers", [])
        config.servers = [self._parse_server(s) for s in servers_data]

        return config

    def _parse_global(self, data: dict) -> GlobalConfig:
        """解析全局配置"""
        app_data = data.get("app", {})
        update_data = data.get("update", {})
        keygen_data = data.get("keygen", {})

        return GlobalConfig(
            app=AppConfig(
                log_level=app_data.get("log_level", "INFO"),
                log_dir=app_data.get("log_dir", "logs"),
            ),
            update=UpdateConfig(
                auto_check=update_data.get("auto_check", True),
            ),
            keygen=KeygenConfig(
                key_type=keygen_data.get("key_type", "ed25519"),
                comment=keygen_data.get("comment", "openclaw-proxy"),
                key_path=keygen_data.get("key_path", ""),
                known_hosts=keygen_data.get("known_hosts", ""),
            ),
        )

    def _parse_server(self, data: dict) -> ServerConfig:
        """解析服务器配置"""
        ssh_data = data.get("ssh", {})
        ssh = SSHConfig(
            host=ssh_data.get("host", "localhost"),
            port=ssh_data.get("port", 22),
            user=ssh_data.get("user", "root"),
            # key_path 和 known_hosts 从 global.keygen 获取
            strict_host_key_checking=ssh_data.get("strict_host_key_checking", "accept-new"),
            connect_timeout=ssh_data.get("connect_timeout", 10),
            server_alive_interval=ssh_data.get("server_alive_interval", 30),
            server_alive_count_max=ssh_data.get("server_alive_count_max", 3),
            compression=ssh_data.get("compression", False),
        )

        port_mappings = []
        for pm_data in data.get("port_mappings", []):
            port_mappings.append(PortMappingConfig(
                id=pm_data.get("id", ""),
                name=pm_data.get("name", ""),
                enabled=pm_data.get("enabled", True),
                local_bind_host=pm_data.get("local_bind_host", "127.0.0.1"),
                local_port=pm_data.get("local_port", 18789),
                remote_host=pm_data.get("remote_host", "127.0.0.1"),
                remote_port=pm_data.get("remote_port", 18789),
                is_openclaw=pm_data.get("is_openclaw", False),
            ))

        browser = None
        browser_data = data.get("browser")
        if browser_data:
            token_data = browser_data.get("token", {})
            browser = BrowserConfig(
                enabled=browser_data.get("enabled", True),
                auto_open=browser_data.get("auto_open", True),
                url_template=browser_data.get("url_template", "http://{local_host}:{local_port}"),
                open_timeout=browser_data.get("open_timeout", 10),
                token=TokenConfig(
                    auto_fetch=token_data.get("auto_fetch", True),
                    remote_config_path=token_data.get("remote_config_path", "~/.openclaw/openclaw.json"),
                    cached_token=token_data.get("cached_token", ""),
                ),
            )

        return ServerConfig(
            id=data.get("id", ""),
            name=data.get("name", ""),
            enabled=data.get("enabled", True),
            auto_run=data.get("auto_run", False),
            ssh=ssh,
            port_mappings=port_mappings,
            browser=browser,
            notes=data.get("notes", ""),
        )

    def save(self, config: Union[MultiServerConfig, Config]) -> bool:
        """
        保存配置

        支持：
        - MultiServerConfig（新版多服务器配置）
        - Config（旧版配置，自动转换）

        Args:
            config: 配置对象

        Returns:
            是否成功
        """
        try:
            # 如果是旧版 Config，转换为 MultiServerConfig
            if isinstance(config, Config):
                config = self._legacy_to_multi(config)

            data = self._to_dict(config)

            # 确保目录存在
            os.makedirs(self._multi_config_dir, exist_ok=True)

            # 先备份现有配置
            self._backup_config()

            # 写入文件
            with open(self._json_config_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            self._multi_config = config
            logger.info(f"配置已保存到: {self._json_config_file}")
            return True
        except Exception as e:
            logger.error(f"保存配置失败: {e}")
            return False

    def _legacy_to_multi(self, legacy: Config) -> MultiServerConfig:
        """将旧版 Config 转换为 MultiServerConfig"""
        import uuid
        from models import PortMapping

        multi = MultiServerConfig()

        # 全局配置
        multi.global_config.app.log_level = legacy.app.log_level
        multi.global_config.app.log_dir = legacy.app.log_dir
        multi.global_config.update.auto_check = legacy.update.auto_check
        multi.global_config.keygen.key_type = legacy.keygen.key_type
        multi.global_config.keygen.comment = legacy.keygen.comment
        multi.global_config.keygen.key_path = legacy.ssh.key_path
        multi.global_config.keygen.known_hosts = legacy.ssh.known_hosts

        # 创建默认服务器
        server = ServerConfig(
            id=f"srv-{uuid.uuid4().hex[:8]}",
            name=legacy.ssh.host,
            enabled=True,
            auto_run=True,  # 旧版配置迁移时默认启用自动运行
            ssh=SSHConfig(
                host=legacy.ssh.host,
                port=legacy.ssh.port,
                user=legacy.ssh.user,
                strict_host_key_checking=legacy.ssh.strict_host_key_checking,
                connect_timeout=legacy.ssh.connect_timeout,
                server_alive_interval=legacy.ssh.server_alive_interval,
                server_alive_count_max=legacy.ssh.server_alive_count_max,
                compression=legacy.ssh.compression,
            ),
            port_mappings=[
                PortMappingConfig(
                    id=f"pm-{uuid.uuid4().hex[:8]}",
                    name=f"端口 {pm.local_port}",
                    enabled=True,
                    local_bind_host=pm.local_bind_host,
                    local_port=pm.local_port,
                    remote_host=pm.remote_host,
                    remote_port=pm.remote_port,
                    is_openclaw=getattr(pm, 'is_openclaw', False),
                )
                for pm in legacy.ssh.port_mappings
            ] if legacy.ssh.port_mappings else [
                PortMappingConfig(
                    id=f"pm-{uuid.uuid4().hex[:8]}",
                    name="主映射",
                    enabled=True,
                    local_bind_host=legacy.ssh.local_bind_host,
                    local_port=legacy.ssh.local_port,
                    remote_host=legacy.ssh.remote_host,
                    remote_port=legacy.ssh.remote_port,
                    is_openclaw=False,
                )
            ],
            browser=BrowserConfig(
                enabled=True,
                auto_open=legacy.browser.auto_open,
                url_template=legacy.browser.url.replace(
                    f"{legacy.ssh.local_bind_host}:{legacy.ssh.local_port}",
                    "{local_host}:{local_port}"
                ) if legacy.browser.url else "http://{local_host}:{local_port}",
                open_timeout=legacy.browser.open_timeout,
                token=TokenConfig(
                    auto_fetch=legacy.browser.auto_fetch_token,
                    remote_config_path=legacy.browser.remote_config_path,
                    cached_token=legacy.browser.token,
                ),
            ),
        )

        multi.servers = [server]
        return multi

    def _to_dict(self, config: MultiServerConfig) -> dict:
        """将配置对象转换为字典"""
        return {
            "$schema": "https://openclaw-proxy.example.com/schemas/config-v2.json",
            "version": config.version,
            "global": {
                "app": {
                    "log_level": config.global_config.app.log_level,
                    "log_dir": config.global_config.app.log_dir,
                },
                "update": {
                    "auto_check": config.global_config.update.auto_check,
                },
                "keygen": {
                    "key_type": config.global_config.keygen.key_type,
                    "comment": config.global_config.keygen.comment,
                    "key_path": config.global_config.keygen.key_path,
                    "known_hosts": config.global_config.keygen.known_hosts,
                },
            },
            "servers": [self._server_to_dict(s) for s in config.servers],
        }

    def _server_to_dict(self, server: ServerConfig) -> dict:
        """将服务器配置转换为字典"""
        data = {
            "id": server.id,
            "name": server.name,
            "enabled": server.enabled,
            "auto_run": server.auto_run,
            "ssh": {
                "host": server.ssh.host,
                "port": server.ssh.port,
                "user": server.ssh.user,
                # key_path 和 known_hosts 从 global.keygen 获取，不在此存储
                "strict_host_key_checking": server.ssh.strict_host_key_checking,
                "connect_timeout": server.ssh.connect_timeout,
                "server_alive_interval": server.ssh.server_alive_interval,
                "server_alive_count_max": server.ssh.server_alive_count_max,
                "compression": server.ssh.compression,
            },
            "port_mappings": [
                {
                    "id": pm.id,
                    "name": pm.name,
                    "enabled": pm.enabled,
                    "local_bind_host": pm.local_bind_host,
                    "local_port": pm.local_port,
                    "remote_host": pm.remote_host,
                    "remote_port": pm.remote_port,
                    "is_openclaw": pm.is_openclaw,
                }
                for pm in server.port_mappings
            ],
            "notes": server.notes,
        }

        if server.browser:
            data["browser"] = {
                "enabled": server.browser.enabled,
                "auto_open": server.browser.auto_open,
                "url_template": server.browser.url_template,
                "open_timeout": server.browser.open_timeout,
                "token": {
                    "auto_fetch": server.browser.token.auto_fetch,
                    "remote_config_path": server.browser.token.remote_config_path,
                    "cached_token": server.browser.token.cached_token,
                },
            }

        return data

    def _create_default_config(self) -> MultiServerConfig:
        """创建默认配置"""
        config = MultiServerConfig()
        config.servers = []  # 初始为空，用户手动添加服务器
        return config

    def _backup_config(self) -> bool:
        """备份当前配置文件"""
        backup_file = self._json_config_file + ".bak"
        if os.path.exists(self._json_config_file):
            try:
                shutil.copy2(self._json_config_file, backup_file)
                return True
            except Exception:
                pass
        return False

    def has_backup(self) -> bool:
        """是否有备份"""
        return os.path.exists(self._json_config_file + ".bak")

    def restore_backup(self) -> bool:
        """恢复备份"""
        backup_file = self._json_config_file + ".bak"
        if os.path.exists(backup_file):
            try:
                shutil.copy2(backup_file, self._json_config_file)
                self.load()  # 重新加载配置
                return True
            except Exception:
                return False
        return False

    def add_server(self, server: ServerConfig) -> bool:
        """添加服务器"""
        if self._multi_config is None:
            self.load_multi()

        # 检查ID是否重复
        if any(s.id == server.id for s in self._multi_config.servers):
            logger.error(f"服务器ID已存在: {server.id}")
            return False

        self._multi_config.servers.append(server)
        return self.save(self._multi_config)

    def update_server(self, server: ServerConfig) -> bool:
        """更新服务器"""
        if self._multi_config is None:
            self.load_multi()

        for i, s in enumerate(self._multi_config.servers):
            if s.id == server.id:
                self._multi_config.servers[i] = server
                return self.save(self._multi_config)

        logger.error(f"服务器不存在: {server.id}")
        return False

    def remove_server(self, server_id: str) -> bool:
        """删除服务器"""
        if self._multi_config is None:
            self.load_multi()

        original_count = len(self._multi_config.servers)
        self._multi_config.servers = [s for s in self._multi_config.servers if s.id != server_id]

        if len(self._multi_config.servers) == original_count:
            logger.error(f"服务器不存在: {server_id}")
            return False

        return self.save(self._multi_config)

    def get_server(self, server_id: str) -> Optional[ServerConfig]:
        """获取服务器配置"""
        if self._multi_config is None:
            self.load_multi()
        return self._multi_config.get_server_by_id(server_id)

    def update_token(self, token: str, server_id: str = None) -> bool:
        """
        更新指定服务器的 cached_token

        只更新 token 字段，不修改其他配置。

        Args:
            token: 新的 token 值
            server_id: 服务器ID，None 表示默认服务器

        Returns:
            是否成功
        """
        try:
            if self._multi_config is None:
                self.load_multi()

            # 获取目标服务器
            if server_id:
                server = self._multi_config.get_server_by_id(server_id)
            else:
                server = self._multi_config.get_default_server()

            if not server:
                logger.error(f"未找到服务器: {server_id or '默认'}")
                return False

            if not server.browser:
                logger.error(f"服务器 {server.name} 没有浏览器配置")
                return False

            # 只更新 cached_token
            server.browser.token.cached_token = token

            # 直接保存，不触发 _legacy_to_multi 转换
            data = self._to_dict(self._multi_config)

            # 备份并写入
            self._backup_config()
            with open(self._json_config_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            logger.info(f"Token 已更新到服务器 {server.name}")
            return True
        except Exception as e:
            logger.error(f"更新 token 失败: {e}")
            return False


class ConfigValidator:
    """配置验证器"""

    @staticmethod
    def validate(config: MultiServerConfig) -> Tuple[bool, List[str]]:
        """
        验证配置

        Returns:
            (是否有效, 错误列表)
        """
        errors = []

        # 验证版本
        if config.version not in ["2.0", "2.0.0"]:
            errors.append(f"不支持的配置版本: {config.version}")

        # 如果没有服务器配置，直接返回（允许空配置）
        if not config.servers:
            return True, []

        # 检查重复ID
        server_ids = [s.id for s in config.servers]
        duplicates = [id for id in server_ids if server_ids.count(id) > 1]
        if duplicates:
            errors.append(f"服务器ID重复: {set(duplicates)}")

        # 验证每个服务器
        for server in config.servers:
            errors.extend(ConfigValidator.validate_server(server))

        # 验证端口冲突
        errors.extend(ConfigValidator.check_port_conflicts(config))

        return len(errors) == 0, errors

    @staticmethod
    def validate_server(server: ServerConfig) -> List[str]:
        """验证服务器配置"""
        errors = []

        # SSH配置验证
        if not server.ssh.host:
            errors.append(f"服务器 [{server.name}] 缺少主机地址")

        if not server.ssh.user:
            errors.append(f"服务器 [{server.name}] 缺少用户名")

        if server.ssh.port < 1 or server.ssh.port > 65535:
            errors.append(f"服务器 [{server.name}] SSH端口无效: {server.ssh.port}")

        # 端口映射验证
        for pm in server.port_mappings:
            if pm.enabled:
                if pm.local_port < 1 or pm.local_port > 65535:
                    errors.append(f"服务器 [{server.name}] 本地端口无效: {pm.local_port}")
                if pm.remote_port < 1 or pm.remote_port > 65535:
                    errors.append(f"服务器 [{server.name}] 远程端口无效: {pm.remote_port}")

        return errors

    @staticmethod
    def check_port_conflicts(config: MultiServerConfig) -> List[str]:
        """检查端口冲突"""
        errors = []
        port_map = {}  # (local_host, local_port) -> server_name

        for server in config.servers:
            if not server.enabled:
                continue

            for pm in server.port_mappings:
                if not pm.enabled:
                    continue

                key = (pm.local_bind_host, pm.local_port)
                if key in port_map:
                    errors.append(
                        f"端口冲突: 服务器 [{server.name}] 和 [{port_map[key]}] "
                        f"都使用了 {pm.local_bind_host}:{pm.local_port}"
                    )
                else:
                    port_map[key] = server.name

        return errors
