"""
隧道状态模型
"""

from enum import Enum, auto
from typing import Optional


class TunnelState(Enum):
    """隧道状态枚举"""

    DISCONNECTED = auto()  # 已断开
    CONNECTING = auto()  # 连接中
    CONNECTED = auto()  # 已连接
    RECONNECTING = auto()  # 重连中
    ERROR = auto()  # 错误

    @property
    def is_connected(self) -> bool:
        """是否已连接"""
        return self == TunnelState.CONNECTED

    @property
    def is_connecting(self) -> bool:
        """是否正在连接"""
        return self in (TunnelState.CONNECTING, TunnelState.RECONNECTING)

    @property
    def can_start(self) -> bool:
        """是否可以启动"""
        return self in (TunnelState.DISCONNECTED, TunnelState.ERROR)

    @property
    def can_stop(self) -> bool:
        """是否可以停止"""
        return self in (
            TunnelState.CONNECTED,
            TunnelState.CONNECTING,
            TunnelState.RECONNECTING,
        )

    @property
    def display_text(self) -> str:
        """获取显示文本"""
        texts = {
            TunnelState.DISCONNECTED: "未连接",
            TunnelState.CONNECTING: "正在连接...",
            TunnelState.CONNECTED: "已连接",
            TunnelState.RECONNECTING: "正在重连...",
            TunnelState.ERROR: "连接错误",
        }
        return texts.get(self, "未知状态")

    @property
    def status_icon(self) -> str:
        """获取状态图标"""
        icons = {
            TunnelState.DISCONNECTED: "○",
            TunnelState.CONNECTING: "◐",
            TunnelState.CONNECTED: "●",
            TunnelState.RECONNECTING: "◑",
            TunnelState.ERROR: "✗",
        }
        return icons.get(self, "?")

    @property
    def color(self) -> str:
        """获取状态颜色"""
        colors = {
            TunnelState.DISCONNECTED: "gray",
            TunnelState.CONNECTING: "orange",
            TunnelState.CONNECTED: "green",
            TunnelState.RECONNECTING: "orange",
            TunnelState.ERROR: "red",
        }
        return colors.get(self, "black")


class TunnelStatus:
    """隧道状态信息（包含状态和附加信息）"""

    def __init__(
        self,
        state: TunnelState = TunnelState.DISCONNECTED,
        message: str = "",
        pid: Optional[int] = None,
    ):
        self.state = state
        self.message = message or state.display_text
        self.pid = pid

    @property
    def is_running(self) -> bool:
        """隧道进程是否在运行"""
        return self.pid is not None

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "state": self.state.name,
            "message": self.message,
            "pid": self.pid,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "TunnelStatus":
        """从字典创建"""
        return cls(
            state=TunnelState[data.get("state", "DISCONNECTED")],
            message=data.get("message", ""),
            pid=data.get("pid"),
        )
