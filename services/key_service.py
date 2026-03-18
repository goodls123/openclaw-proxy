"""
密钥服务
封装SSH密钥管理逻辑
"""

import logging
from typing import Optional, Tuple, Callable, TYPE_CHECKING

from services.interfaces import IKeyService, IConfigRepository

if TYPE_CHECKING:
    from key_manager import KeyManager, KeyDeployResult

logger = logging.getLogger("openclaw_proxy")


class KeyService(IKeyService):
    """
    密钥服务

    功能：
    1. 生成SSH密钥对
    2. 部署公钥到远程服务器
    3. 测试密钥连接
    """

    def __init__(self, config_repo: IConfigRepository):
        """
        初始化密钥服务

        Args:
            config_repo: 配置仓库
        """
        self._config_repo = config_repo

    def _create_key_manager(self, key_path: Optional[str] = None) -> "KeyManager":
        """创建密钥管理器"""
        from key_manager import KeyManager

        config = self._config_repo.load()
        path = key_path or config.ssh.key_path
        return KeyManager(
            key_path=path,
            key_type=config.keygen.key_type,
            comment=config.keygen.comment,
        )

    def key_exists(self, key_path: Optional[str] = None) -> bool:
        """
        检查密钥是否存在

        Args:
            key_path: 密钥路径，None则使用配置中的路径

        Returns:
            是否存在
        """
        key_manager = self._create_key_manager(key_path)
        return key_manager.key_exists()

    def generate_key(
        self,
        key_path: str,
        key_type: str = "ed25519",
        comment: str = "openclaw-proxy",
        overwrite: bool = False,
        passphrase: str = "",
    ) -> Tuple[bool, str]:
        """
        生成SSH密钥对

        Args:
            key_path: 密钥路径
            key_type: 密钥类型
            comment: 密钥注释
            overwrite: 是否覆盖
            passphrase: 密钥密码

        Returns:
            (是否成功, 消息)
        """
        from key_manager import KeyManager

        key_manager = KeyManager(
            key_path=key_path,
            key_type=key_type,
            comment=comment,
        )

        return key_manager.generate_key(overwrite=overwrite, passphrase=passphrase)

    def deploy_key(
        self,
        host: str,
        port: int,
        user: str,
        password: str,
        key_path: str,
        progress_callback: Optional[Callable[[str], None]] = None,
    ) -> Tuple[bool, str, Optional[str]]:
        """
        部署公钥到远程服务器

        Args:
            host: 服务器地址
            port: SSH端口
            user: 用户名
            password: 密码
            key_path: 密钥路径
            progress_callback: 进度回调

        Returns:
            (是否成功, 消息, 错误详情)
        """
        key_manager = self._create_key_manager(key_path)

        result = key_manager.deploy_public_key(
            host=host,
            port=port,
            user=user,
            password=password,
            progress_callback=progress_callback,
        )

        return result.success, result.message, result.error_detail

    def test_connection(
        self,
        host: str,
        port: int,
        user: str,
        key_path: str,
        timeout: int = 10,
    ) -> Tuple[bool, str]:
        """
        测试密钥连接

        Args:
            host: 服务器地址
            port: SSH端口
            user: 用户名
            key_path: 密钥路径
            timeout: 超时时间

        Returns:
            (是否成功, 消息)
        """
        key_manager = self._create_key_manager(key_path)
        return key_manager.test_key_connection(
            host=host,
            port=port,
            user=user,
            timeout=timeout,
        )

    def test_host_reachable(
        self,
        host: str,
        port: int,
        timeout: int = 5,
    ) -> Tuple[bool, str]:
        """
        测试主机是否可达（仅测试TCP连接，不验证认证）

        Args:
            host: 服务器地址
            port: SSH端口
            timeout: 超时时间

        Returns:
            (是否可达, 消息)
        """
        from key_manager import KeyManager

        return KeyManager.test_host_reachable(host, port, timeout)

    def generate_and_deploy(
        self,
        host: str,
        port: int,
        user: str,
        password: str,
        key_path: str,
        key_type: str = "ed25519",
        comment: str = "openclaw-proxy",
        overwrite: bool = True,
        progress_callback: Optional[Callable[[str], None]] = None,
    ) -> Tuple[bool, str, Optional[str]]:
        """
        生成密钥并部署到远程服务器（一站式操作）

        Args:
            host: 服务器地址
            port: SSH端口
            user: 用户名
            password: 密码
            key_path: 密钥路径
            key_type: 密钥类型
            comment: 密钥注释
            overwrite: 是否覆盖
            progress_callback: 进度回调

        Returns:
            (是否成功, 消息, 错误详情)
        """
        from key_manager import KeyManager

        key_manager = KeyManager(
            key_path=key_path,
            key_type=key_type,
            comment=comment,
        )

        result = key_manager.generate_and_deploy(
            host=host,
            port=port,
            user=user,
            password=password,
            overwrite=overwrite,
            progress_callback=progress_callback,
        )

        return result.success, result.message, result.error_detail
