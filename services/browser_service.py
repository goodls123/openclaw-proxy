"""
浏览器服务
封装浏览器打开逻辑
"""

import logging
import webbrowser
from typing import Optional, List, TYPE_CHECKING

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
    3. 支持多端口映射
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

    def _fetch_openclaw_token(
        self,
        host: str,
        port: int,
        user: str,
        key_path: str,
        remote_config_path: str,
    ) -> Optional[str]:
        """
        从远程服务器获取 OpenClaw token

        Args:
            host: SSH 主机地址
            port: SSH 端口
            user: SSH 用户名
            key_path: 私钥路径
            remote_config_path: 远程配置文件路径

        Returns:
            token 字符串，失败返回 None
        """
        from repositories.remote_config_repository import RemoteConfigRepository

        remote_repo = RemoteConfigRepository()
        success, config, error = remote_repo.fetch(
            host=host,
            port=port,
            user=user,
            key_path=key_path,
            remote_path=remote_config_path,
        )

        if not success:
            logger.warning(f"获取远程配置失败: {error}")
            return None

        token_success, token_or_error = remote_repo.extract_token(config)
        if token_success:
            logger.info(f"成功获取 OpenClaw token")
            return token_or_error
        else:
            logger.warning(f"提取 token 失败: {token_or_error}")
            return None

    def open_all_port_mappings(self, server_id: Optional[str] = None) -> bool:
        """
        打开服务器所有端口映射对应的浏览器URL

        Args:
            server_id: 服务器ID，None则使用默认服务器

        Returns:
            是否成功
        """
        from repositories.json_config_repository import JsonConfigRepository
        from utils.path_utils import expand_path
        import os

        # 获取服务器配置
        config_dir = os.path.join(os.path.expanduser("~"), ".openclaw-proxy")
        json_repo = JsonConfigRepository(config_dir)
        multi_config = json_repo.load_multi()

        if server_id:
            server = multi_config.get_server_by_id(server_id)
        else:
            server = multi_config.get_default_server()

        if not server:
            logger.error("未找到服务器配置")
            return False

        # 检查是否有 OpenClaw 端口
        openclaw_ports = [pm for pm in server.get_enabled_port_mappings() if pm.is_openclaw]

        # 如果有 OpenClaw 端口，从远程获取 token
        openclaw_token = None
        if openclaw_ports:
            key_path = expand_path(multi_config.global_config.keygen.key_path)
            remote_config_path = (
                server.browser.token.remote_config_path
                if server.browser and server.browser.token
                else "~/.openclaw/openclaw.json"
            )

            logger.info("从远程获取 OpenClaw token...")
            openclaw_token = self._fetch_openclaw_token(
                host=server.ssh.host,
                port=server.ssh.port,
                user=server.ssh.user,
                key_path=key_path,
                remote_config_path=remote_config_path,
            )

        # 遍历所有启用的端口映射
        success = True
        for pm in server.get_enabled_port_mappings():
            base_url = f"http://{pm.local_bind_host}:{pm.local_port}"

            if pm.is_openclaw:
                # OpenClaw 服务：带 token 打开
                if openclaw_token:
                    url = f"{base_url}/#token={openclaw_token}"
                else:
                    url = base_url
                    logger.warning(f"OpenClaw token 获取失败，打开不带 token 的 URL")
                logger.info(f"打开浏览器 (OpenClaw): {url[:50]}...")
            else:
                # 非 OpenClaw 服务：直接打开基础 URL
                url = base_url
                logger.info(f"打开浏览器: {url}")

            try:
                webbrowser.open(url)
            except Exception as e:
                logger.error(f"打开浏览器失败 ({pm.local_bind_host}:{pm.local_port}): {e}")
                success = False

        return success

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
