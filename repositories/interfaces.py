"""
仓库接口定义
"""

from typing import Protocol, Tuple, Any, runtime_checkable

from models import Config


@runtime_checkable
class IConfigRepository(Protocol):
    """配置仓库接口"""

    @property
    def config_file(self) -> str:
        """配置文件路径"""
        ...

    def load(self) -> Config:
        """加载配置"""
        ...

    def save(self, config: Config) -> bool:
        """保存配置"""
        ...

    def update_token(self, token: str, server_id: str = None) -> bool:
        """
        更新指定服务器的 cached_token

        Args:
            token: 新的 token 值
            server_id: 服务器ID，None 表示默认服务器

        Returns:
            是否成功
        """
        ...

    def has_backup(self) -> bool:
        """是否有备份"""
        ...

    def restore_backup(self) -> bool:
        """恢复备份"""
        ...


@runtime_checkable
class IRemoteConfigRepository(Protocol):
    """远程配置仓库接口"""

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

        Returns:
            (是否成功, 配置字典, 错误信息)
        """
        ...

    def extract_token(self, config: Any) -> Tuple[bool, str]:
        """
        从配置中提取token

        Returns:
            (是否成功, token或错误信息)
        """
        ...
