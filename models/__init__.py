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

# 多服务器配置模型（需要显式从 server_config 导入以避免命名冲突）
from models.server_config import (
    MultiServerConfig,
    ServerConfig,
    GlobalConfig,
    PortMappingConfig,
    TokenConfig,
    MigrationInfo,
)
from models.server_config import (
    SSHConfig as NewSSHConfig,
    BrowserConfig as NewBrowserConfig,
)

__all__ = [
    # 旧版配置（保持向后兼容）
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
    # 多服务器配置
    "MultiServerConfig",
    "ServerConfig",
    "GlobalConfig",
    "PortMappingConfig",
    "NewSSHConfig",
    "NewBrowserConfig",
    "TokenConfig",
    "MigrationInfo",
]
