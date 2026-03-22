"""
更新服务
封装版本检查和更新逻辑
"""

import json
import logging
import os
import ssl
import threading
import urllib.request
import urllib.error
from datetime import datetime, timedelta
from typing import Callable, Tuple, Optional

from models import UpdateCheckResult, ReleaseInfo
from services.interfaces import IUpdateService, IConfigRepository
from version import __version__, GITHUB_REPO, GITHUB_RELEASES_URL

logger = logging.getLogger("openclaw_proxy")

# 尝试导入 certifi，如果失败则使用系统证书
try:
    import certifi
    SSL_CONTEXT = ssl.create_default_context(cafile=certifi.where())
except ImportError:
    # certifi 未安装时使用系统默认证书
    SSL_CONTEXT = ssl.create_default_context()
    logger.debug("certifi 未安装，使用系统默认证书")

# GitHub API配置
GITHUB_API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
REQUEST_TIMEOUT = 10  # 秒
CHECK_INTERVAL_HOURS = 24  # 检查间隔


def parse_version(version_str: str) -> Tuple[int, ...]:
    """解析版本号为元组"""
    # 移除 'v' 前缀
    version_str = version_str.lstrip('v').strip()
    parts = []
    for part in version_str.split('.'):
        try:
            parts.append(int(part))
        except ValueError:
            # 处理类似 "1.0.0-beta" 的情况
            num = ''.join(c for c in part if c.isdigit())
            parts.append(int(num) if num else 0)
    return tuple(parts)


def compare_versions(current: str, latest: str) -> int:
    """
    比较版本号
    Returns:
        -1: current < latest
         0: current == latest
         1: current > latest
    """
    try:
        c = parse_version(current)
        l = parse_version(latest)

        # 补齐版本号长度
        max_len = max(len(c), len(l))
        c = c + (0,) * (max_len - len(c))
        l = l + (0,) * (max_len - len(l))

        if c < l:
            return -1
        elif c > l:
            return 1
        return 0
    except Exception as e:
        logger.error(f"版本比较失败: {e}")
        return 0


def get_last_check_file(config_dir: str) -> str:
    """获取上次检查时间文件路径"""
    return os.path.join(config_dir, ".update_check")


def should_check_update(config_dir: str) -> bool:
    """检查是否应该执行更新检查"""
    check_file = get_last_check_file(config_dir)

    if not os.path.exists(check_file):
        return True

    try:
        with open(check_file, 'r', encoding='utf-8') as f:
            last_check_str = f.read().strip()
            last_check = datetime.fromisoformat(last_check_str)
            return datetime.now() - last_check > timedelta(hours=CHECK_INTERVAL_HOURS)
    except Exception:
        return True


def record_check_time(config_dir: str):
    """记录本次检查时间"""
    check_file = get_last_check_file(config_dir)
    try:
        with open(check_file, 'w', encoding='utf-8') as f:
            f.write(datetime.now().isoformat())
    except Exception as e:
        logger.warning(f"记录更新检查时间失败: {e}")


def fetch_latest_release() -> Tuple[bool, Optional[ReleaseInfo], Optional[str]]:
    """
    从GitHub获取最新发布版本

    Returns:
        (成功, ReleaseInfo, 错误信息)
    """
    try:
        request = urllib.request.Request(GITHUB_API_URL)
        request.add_header('User-Agent', f'OpenClaw-Proxy/{__version__}')
        request.add_header('Accept', 'application/vnd.github.v3+json')

        with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT, context=SSL_CONTEXT) as response:
            if response.status != 200:
                return False, None, f"HTTP状态码: {response.status}"

            data = json.loads(response.read().decode('utf-8'))

            release_info = ReleaseInfo(
                version=data.get('tag_name', '').lstrip('v'),
                name=data.get('name', ''),
                url=data.get('html_url', GITHUB_RELEASES_URL),
                body=data.get('body', ''),
                published_at=data.get('published_at', ''),
            )

            return True, release_info, None

    except urllib.error.HTTPError as e:
        if e.code == 403:
            return False, None, "GitHub API请求频率限制"
        return False, None, f"HTTP错误: {e.code}"
    except urllib.error.URLError as e:
        return False, None, f"网络错误: {e.reason}"
    except json.JSONDecodeError:
        return False, None, "JSON解析失败"
    except Exception as e:
        return False, None, f"未知错误: {str(e)}"


def check_for_update_internal(config_dir: str, force: bool = False) -> UpdateCheckResult:
    """
    内部更新检查函数

    Args:
        config_dir: 配置目录路径
        force: 是否强制检查（忽略时间间隔）

    Returns:
        UpdateCheckResult
    """
    # 检查是否应该执行更新检查
    if not force and not should_check_update(config_dir):
        logger.debug("距离上次检查未超过间隔时间，跳过更新检查")
        return UpdateCheckResult(
            has_update=False,
            current_version=__version__,
            latest_version=None,
            release_info=None,
            error=None,
        )

    # 记录检查时间
    record_check_time(config_dir)

    # 获取最新版本
    success, release_info, error = fetch_latest_release()

    if not success:
        logger.warning(f"检查更新失败: {error}")
        return UpdateCheckResult(
            has_update=False,
            current_version=__version__,
            latest_version=None,
            release_info=None,
            error=error,
        )

    if not release_info:
        return UpdateCheckResult(
            has_update=False,
            current_version=__version__,
            latest_version=None,
            release_info=None,
            error="无法获取版本信息",
        )

    # 比较版本
    comparison = compare_versions(__version__, release_info.version)
    has_update = comparison < 0

    if has_update:
        logger.info(f"发现新版本: {release_info.version} (当前: {__version__})")
    else:
        logger.info(f"已是最新版本: {__version__}")

    return UpdateCheckResult(
        has_update=has_update,
        current_version=__version__,
        latest_version=release_info.version,
        release_info=release_info if has_update else None,
        error=None,
    )


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
        config = self._config_repo.load()
        config_dir = os.path.dirname(self._config_repo.config_file)

        return check_for_update_internal(config_dir, force)

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
