"""
端口映射数据模型
"""

from dataclasses import dataclass


@dataclass
class PortMapping:
    """单个端口映射配置"""

    local_bind_host: str = "127.0.0.1"  # 本地绑定地址
    local_port: int = 18789  # 本地端口
    remote_host: str = "127.0.0.1"  # 远程目标地址
    remote_port: int = 18789  # 远程目标端口
    is_openclaw: bool = False  # 是否为 OpenClaw 服务

    def to_string(self) -> str:
        """序列化为配置字符串：本地地址:本地端口:远程地址:远程端口"""
        return f"{self.local_bind_host}:{self.local_port}:{self.remote_host}:{self.remote_port}"

    @classmethod
    def from_string(cls, s: str) -> "PortMapping":
        """从配置字符串解析"""
        parts = s.strip().split(":")
        if len(parts) == 4:
            return cls(
                local_bind_host=parts[0],
                local_port=int(parts[1]),
                remote_host=parts[2],
                remote_port=int(parts[3]),
            )
        raise ValueError(f"无效的端口映射格式: {s}")

    def to_display_string(self) -> str:
        """生成显示用的字符串"""
        return f"{self.local_bind_host}:{self.local_port} → {self.remote_host}:{self.remote_port}"

    def __str__(self) -> str:
        return self.to_display_string()
