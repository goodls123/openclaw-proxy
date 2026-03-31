"""
依赖注入容器
管理所有服务的创建和依赖注入
"""

from dataclasses import dataclass, field
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from services.interfaces import (
        ITunnelService,
        IKeyService,
        ITokenService,
        IBrowserService,
        IUpdateService,
        IConfigRepository,
        IRemoteConfigRepository,
    )
    from services.multi_tunnel_service import MultiTunnelService


@dataclass
class ServiceContainer:
    """
    服务容器 - 管理所有依赖

    使用懒加载模式，只有在首次访问时才创建服务实例。
    """

    # 仓库
    config_repo: "IConfigRepository"
    remote_config_repo: "IRemoteConfigRepository"

    # 服务实例（懒加载）
    _tunnel_service: Optional["ITunnelService"] = field(default=None, repr=False)
    _multi_tunnel_service: Optional["MultiTunnelService"] = field(default=None, repr=False)
    _key_service: Optional["IKeyService"] = field(default=None, repr=False)
    _token_service: Optional["ITokenService"] = field(default=None, repr=False)
    _browser_service: Optional["IBrowserService"] = field(default=None, repr=False)
    _update_service: Optional["IUpdateService"] = field(default=None, repr=False)

    @property
    def tunnel_service(self) -> "ITunnelService":
        """获取隧道服务"""
        if self._tunnel_service is None:
            from services.tunnel_service import TunnelService

            self._tunnel_service = TunnelService(self.config_repo)
        return self._tunnel_service

    @property
    def multi_tunnel_service(self) -> "MultiTunnelService":
        """获取多隧道服务"""
        if self._multi_tunnel_service is None:
            from services.multi_tunnel_service import MultiTunnelService
            from repositories.json_config_repository import JsonConfigRepository
            import os

            config_dir = os.path.dirname(self.config_repo._config_file)
            json_repo = JsonConfigRepository(config_dir)
            self._multi_tunnel_service = MultiTunnelService(json_repo)
        return self._multi_tunnel_service

    @property
    def key_service(self) -> "IKeyService":
        """获取密钥服务"""
        if self._key_service is None:
            from services.key_service import KeyService

            self._key_service = KeyService(self.config_repo)
        return self._key_service

    @property
    def token_service(self) -> "ITokenService":
        """获取Token服务"""
        if self._token_service is None:
            from services.token_service import TokenService
            from repositories.json_config_repository import JsonConfigRepository
            import os

            config_dir = os.path.dirname(self.config_repo._config_file)
            json_repo = JsonConfigRepository(config_dir)

            self._token_service = TokenService(
                self.config_repo,
                self.remote_config_repo,
                json_repo,
            )
        return self._token_service

    @property
    def browser_service(self) -> "IBrowserService":
        """获取浏览器服务"""
        if self._browser_service is None:
            from services.browser_service import BrowserService

            self._browser_service = BrowserService(
                self.config_repo,
                self.token_service,
            )
        return self._browser_service

    @property
    def update_service(self) -> "IUpdateService":
        """获取更新服务"""
        if self._update_service is None:
            from services.update_service import UpdateService

            self._update_service = UpdateService(self.config_repo)
        return self._update_service

    @classmethod
    def create(cls, config_dir: str) -> "ServiceContainer":
        """
        创建服务容器

        Args:
            config_dir: 配置文件目录

        Returns:
            服务容器实例
        """
        import os
        from repositories.config_repository import ConfigRepository
        from repositories.remote_config_repository import RemoteConfigRepository

        config_file = os.path.join(config_dir, "config.json")
        config_repo = ConfigRepository(config_file)
        remote_config_repo = RemoteConfigRepository()

        return cls(config_repo=config_repo, remote_config_repo=remote_config_repo)

    def reset_services(self) -> None:
        """重置所有服务实例（用于配置变更后）"""
        self._tunnel_service = None
        self._multi_tunnel_service = None
        self._key_service = None
        self._token_service = None
        self._browser_service = None
        self._update_service = None
