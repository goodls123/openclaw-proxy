"""
浏览器服务
封装浏览器打开逻辑
"""

import logging
import webbrowser
from typing import Optional, TYPE_CHECKING

from services.interfaces import IBrowserService, ITokenService, IConfigRepository

if TYPE_CHECKING:
    pass

logger = logging.getLogger("openclaw_proxy")


class BrowserService(IBrowserService):
    """
    浏览器服务

    功能：
    1. 打开浏览器访问指定URL
    2. 自动添加token到URL
    """

    def __init__(
        self,
        config_repo: IConfigRepository,
        token_service: ITokenService,
    ):
        """
        初始化浏览器服务

        Args:
            config_repo: 配置仓库
            token_service: Token服务
        """
        self._config_repo = config_repo
        self._token_service = token_service

    def open(self, url: Optional[str] = None) -> bool:
        """
        打开浏览器

        Args:
            url: 要打开的URL，None则使用配置中的URL（带token）

        Returns:
            是否成功
        """
        if url is None:
            url = self.get_url()

        logger.info(f"打开浏览器: {url[:50]}...")
        try:
            webbrowser.open(url)
            return True
        except Exception as e:
            logger.error(f"打开浏览器失败: {e}")
            return False

    def get_url(self) -> str:
        """
        获取要打开的URL（带token）

        Returns:
            完整的URL
        """
        return self._token_service.get_browser_url()

    def get_base_url(self) -> str:
        """
        获取基础URL（不带token）

        Returns:
            基础URL
        """
        config = self._config_repo.load()
        return f"http://{config.ssh.local_bind_host}:{config.ssh.local_port}"
