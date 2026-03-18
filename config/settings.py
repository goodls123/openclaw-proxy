"""
应用设置
"""

import os
from typing import Optional


class Settings:
    """应用设置（运行时配置）"""

    _instance: Optional["Settings"] = None

    def __init__(self):
        # 应用配置目录
        self.config_dir = os.path.join(os.path.expanduser("~"), ".openclaw-proxy")
        # 配置文件路径
        self.config_file = os.path.join(self.config_dir, "config.ini")
        # 日志目录
        self.log_dir = os.path.join(self.config_dir, "logs")
        # 日志级别
        self.log_level = "INFO"

    @classmethod
    def get_instance(cls) -> "Settings":
        """获取单例实例"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def ensure_dirs(self) -> None:
        """确保必要的目录存在"""
        if not os.path.exists(self.config_dir):
            os.makedirs(self.config_dir)
        if not os.path.exists(self.log_dir):
            os.makedirs(self.log_dir)

    def update(self, **kwargs) -> None:
        """
        更新设置

        Args:
            **kwargs: 要更新的设置项
        """
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
