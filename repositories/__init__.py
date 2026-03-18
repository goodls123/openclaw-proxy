"""
仓库层
"""

from repositories.interfaces import (
    IConfigRepository,
    IRemoteConfigRepository,
)
from repositories.config_repository import ConfigRepository
from repositories.remote_config_repository import RemoteConfigRepository

__all__ = [
    "IConfigRepository",
    "IRemoteConfigRepository",
    "ConfigRepository",
    "RemoteConfigRepository",
]
