"""
数据模型层
包含所有数据结构定义
"""

from models.config import (
    Config,
    SSHConfig,
    BrowserConfig,
    KeygenConfig,
    AppConfig,
    UpdateConfig,
)
from models.port_mapping import PortMapping
from models.tunnel_state import TunnelState, TunnelStatus
from models.update_info import ReleaseInfo, UpdateCheckResult

__all__ = [
    "Config",
    "SSHConfig",
    "BrowserConfig",
    "KeygenConfig",
    "AppConfig",
    "UpdateConfig",
    "PortMapping",
    "TunnelState",
    "TunnelStatus",
    "ReleaseInfo",
    "UpdateCheckResult",
]
