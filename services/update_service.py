"""
更新服务
封装版本检查和更新逻辑
"""

import logging
import threading
from typing import Callable, TYPE_CHECKING

from models import UpdateCheckResult
from services.interfaces import IUpdateService, IConfigRepository
from version import __version__, GITHUB_RELEASES_URL

if TYPE_CHECKING:
    pass

logger = logging.getLogger("openclaw_proxy")


class UpdateService(IUpdateService):
    """
    更新服务

    功能：
    1. 检查GitHub上的最新版本
    2. 比较版本号
    3. 管理更新检查间隔
    """

    def __init__(self, config_repo: IConfigRepository):
        """
        初始化更新服务

        Args:
            config_repo: 配置仓库
        """
        self._config_repo = config_repo

    @property
    def current_version(self) -> str:
        """当前版本"""
        return __version__

    @property
    def releases_url(self) -> str:
        """发布页面URL"""
        return GITHUB_RELEASES_URL

    def check_for_update(self, force: bool = False) -> UpdateCheckResult:
        """
        检查更新

        Args:
            force: 是否强制检查（忽略时间间隔）

        Returns:
            更新检查结果
        """
        import os
        from updater import check_for_update, check_for_update_force

        config = self._config_repo.load()
        config_dir = os.path.dirname(self._config_repo.config_file)

        if force:
            result = check_for_update_force(config_dir)
        else:
            result = check_for_update(config_dir)

        # 转换为新的数据模型
        from models import ReleaseInfo

        release_info = None
        if result.release_info:
            release_info = ReleaseInfo(
                version=result.release_info.version,
                name=result.release_info.name,
                url=result.release_info.url,
                body=result.release_info.body,
                published_at=result.release_info.published_at,
            )

        return UpdateCheckResult(
            has_update=result.has_update,
            current_version=result.current_version,
            latest_version=result.latest_version,
            release_info=release_info,
            error=result.error,
        )

    def check_for_update_async(
        self,
        callback: Callable[[UpdateCheckResult], None],
        force: bool = False,
    ) -> None:
        """
        异步检查更新

        Args:
            callback: 回调函数
            force: 是否强制检查
        """

        def do_check():
            try:
                result = self.check_for_update(force)
                callback(result)
            except Exception as e:
                logger.debug(f"更新检查异常: {e}")
                callback(
                    UpdateCheckResult(
                        has_update=False,
                        current_version=self.current_version,
                        latest_version=None,
                        release_info=None,
                        error=str(e),
                    )
                )

        threading.Thread(target=do_check, daemon=True).start()
