"""
更新信息模型
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class ReleaseInfo:
    """发布版本信息"""

    version: str
    name: str
    url: str
    body: str  # Release notes
    published_at: str


@dataclass
class UpdateCheckResult:
    """更新检查结果"""

    has_update: bool
    current_version: str
    latest_version: Optional[str]
    release_info: Optional[ReleaseInfo]
    error: Optional[str]

    @property
    def is_success(self) -> bool:
        """检查是否成功"""
        return self.error is None

    @property
    def display_message(self) -> str:
        """获取显示消息"""
        if self.error:
            return f"检查失败: {self.error}"
        if self.has_update:
            return f"发现新版本: {self.latest_version}"
        return f"当前已是最新版本 ({self.current_version})"
