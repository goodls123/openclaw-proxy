"""
Token服务
统一管理Token获取逻辑，消除MainWindow和StatusWindow中的重复代码
"""

import logging
import threading
from typing import Optional, Callable, Tuple, TYPE_CHECKING

from services.interfaces import ITokenService, IConfigRepository, IRemoteConfigRepository

if TYPE_CHECKING:
    pass

logger = logging.getLogger("openclaw_proxy")


class TokenService(ITokenService):
    """
    Token服务 - 统一管理Token获取逻辑

    功能：
    1. 从远程配置获取token
    2. 缓存token到内存（不保存到配置文件）
    3. 生成带token的浏览器URL
    """

    def __init__(
        self,
        config_repo: IConfigRepository,
        remote_config_repo: IRemoteConfigRepository,
    ):
        """
        初始化Token服务

        Args:
            config_repo: 配置仓库
            remote_config_repo: 远程配置仓库
        """
        self._config_repo = config_repo
        self._remote_config_repo = remote_config_repo
        self._token: Optional[str] = None

    @property
    def token(self) -> Optional[str]:
        """获取当前token（可能为空）"""
        return self._token

    def get_token(self) -> Optional[str]:
        """
        获取token（仅从内存缓存）

        Returns:
            token字符串，没有则返回None
        """
        return self._token

    def fetch_token_sync(self) -> Tuple[bool, str]:
        """
        同步获取token

        Returns:
            (是否成功, token或错误信息)
        """
        config = self._config_repo.load()

        logger.info("[Token] 开始获取token...")
        logger.debug(f"[Token] 远程配置路径: {config.browser.remote_config_path}")

        success, remote_config, error = self._remote_config_repo.fetch(
            host=config.ssh.host,
            port=config.ssh.port,
            user=config.ssh.user,
            key_path=config.ssh.key_path,
            remote_path=config.browser.remote_config_path,
        )

        if not success:
            logger.warning(f"[Token] 获取远程配置失败: {error}")
            return False, error

        logger.debug(f"[Token] 远程配置内容长度: {len(remote_config) if remote_config else 0}")

        token_success, token_or_error = self._remote_config_repo.extract_token(remote_config)
        if token_success:
            self._token = token_or_error
            logger.info(f"[Token] 成功获取token: {token_or_error[:8]}...")
            return True, token_or_error
        else:
            logger.warning(f"[Token] 提取token失败: {token_or_error}")
            return False, token_or_error

    def fetch_token_async(self, callback: Callable[[bool, str], None]) -> None:
        """
        异步获取token

        Args:
            callback: 回调函数，参数为(是否成功, token或错误信息)
        """

        def do_fetch():
            success, token = self.fetch_token_sync()
            callback(success, token if success else "")

        threading.Thread(target=do_fetch, daemon=True).start()

    def get_browser_url(self) -> str:
        """
        获取带token的浏览器URL

        Returns:
            完整的浏览器URL
        """
        config = self._config_repo.load()
        base_url = f"http://{config.ssh.local_bind_host}:{config.ssh.local_port}"

        token = self.get_token()
        if token:
            return f"{base_url}/#token={token}"
        return base_url

    def clear_cache(self) -> None:
        """清除token缓存"""
        self._token = None
