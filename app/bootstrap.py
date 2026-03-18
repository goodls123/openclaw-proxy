"""
应用初始化
"""

import os
import sys
import logging
from typing import Optional, Callable

from config.settings import Settings
from config.constants import APP_NAME, APP_VERSION


class Application:
    """
    应用程序类

    负责：
    1. 初始化日志系统
    2. 创建服务容器
    3. 管理应用生命周期
    """

    def __init__(self, config_file: Optional[str] = None):
        """
        初始化应用

        Args:
            config_file: 配置文件路径（可选）
        """
        self.settings = Settings.get_instance()
        self._setup_paths()
        self._setup_logging()

        self.logger = logging.getLogger("openclaw_proxy")
        self.logger.info("=" * 50)
        self.logger.info(f"{APP_NAME} 启动")
        self.logger.info(f"版本: {APP_VERSION}")
        self.logger.info(f"Python版本: {sys.version}")
        self.logger.info(f"平台: {sys.platform}")
        self.logger.info(f"配置目录: {self.settings.config_dir}")

        # 确定配置文件路径
        if config_file is None:
            config_file = os.path.join(self.settings.config_dir, "config.ini")
        self.config_file = config_file
        self.logger.info(f"配置文件: {self.config_file}")

        # 延迟创建容器
        self._container: Optional["ServiceContainer"] = None

    def _setup_paths(self) -> None:
        """设置路径"""
        self.settings.ensure_dirs()

    def _setup_logging(self) -> None:
        """设置日志"""
        from utils.logging_utils import setup_logging

        setup_logging(
            log_level=self.settings.log_level,
            log_dir=self.settings.log_dir,
        )

    @property
    def container(self) -> "ServiceContainer":
        """获取服务容器"""
        if self._container is None:
            from app.container import ServiceContainer

            self._container = ServiceContainer.create(self.config_file)
        return self._container

    def reload_config(self) -> None:
        """重新加载配置"""
        self.container.config_repo.load()
        self.container.reset_services()

    def run_gui(self, title: str = APP_NAME) -> int:
        """
        运行图形界面模式

        Args:
            title: 窗口标题

        Returns:
            退出码
        """
        from ui.windows.main_window import MainWindow

        window = MainWindow(self.container, title=title)
        window.run()
        return 0

    def run_status(self) -> int:
        """
        运行状态窗口模式

        Returns:
            退出码
        """
        from ui.windows.status_window import StatusWindow

        window = StatusWindow(self.container)
        window.run()
        return 0

    def shutdown(self) -> None:
        """关闭应用"""
        self.logger.info("应用关闭")
        logging.shutdown()


def create_app(config_file: Optional[str] = None) -> Application:
    """
    创建应用实例

    Args:
        config_file: 配置文件路径

    Returns:
        应用实例
    """
    return Application(config_file=config_file)
