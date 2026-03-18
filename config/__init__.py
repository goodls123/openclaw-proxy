"""
配置模块
"""

from config.settings import Settings
from config.constants import (
    APP_NAME,
    APP_VERSION,
    GITHUB_REPO,
    GITHUB_RELEASES_URL,
    DEFAULT_SSH_PORT,
    DEFAULT_LOCAL_HOST,
    DEFAULT_BROWSER_TIMEOUT,
    DEFAULT_CONNECT_TIMEOUT,
)

__all__ = [
    "Settings",
    "APP_NAME",
    "APP_VERSION",
    "GITHUB_REPO",
    "GITHUB_RELEASES_URL",
    "DEFAULT_SSH_PORT",
    "DEFAULT_LOCAL_HOST",
    "DEFAULT_BROWSER_TIMEOUT",
    "DEFAULT_CONNECT_TIMEOUT",
]
