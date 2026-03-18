"""
配置窗口Presenter
处理配置窗口的业务逻辑
"""

import logging
from typing import Optional, Callable, TYPE_CHECKING

from presenters.base import BasePresenter
from models import Config, PortMapping

if TYPE_CHECKING:
    from app.container import ServiceContainer

logger = logging.getLogger("openclaw_proxy")


class ConfigPresenter(BasePresenter):
    """
    配置窗口Presenter

    负责：
    1. 加载/保存配置
    2. 密钥生成和部署
    3. 连接测试
    4. 更新检查
    """

    def __init__(self, container: "ServiceContainer"):
        super().__init__(container)
        self._on_config_saved: Optional[Callable] = None

    # ============== 回调设置 ==============

    def set_on_config_saved(self, callback: Callable) -> None:
        """设置配置保存回调"""
        self._on_config_saved = callback

    # ============== 配置管理 ==============

    def load_config(self) -> Config:
        """
        加载配置

        Returns:
            配置对象
        """
        return self.config_repo.load()

    def save_config(self, config: Config) -> bool:
        """
        保存配置

        Args:
            config: 配置对象

        Returns:
            是否成功
        """
        success = self.config_repo.save(config)

        if success and self._on_config_saved:
            self._update_ui(self._on_config_saved)

        return success

    def has_backup(self) -> bool:
        """是否有备份"""
        return self.config_repo.has_backup()

    def restore_backup(self) -> bool:
        """恢复备份"""
        success = self.config_repo.restore_backup()

        if success and self._on_config_saved:
            self._update_ui(self._on_config_saved)

        return success

    # ============== 密钥管理 ==============

    def key_exists(self, key_path: Optional[str] = None) -> bool:
        """
        检查密钥是否存在

        Args:
            key_path: 密钥路径

        Returns:
            是否存在
        """
        return self.key_service.key_exists(key_path)

    def generate_key(
        self,
        key_path: str,
        key_type: str = "ed25519",
        comment: str = "openclaw-proxy",
        overwrite: bool = False,
    ) -> tuple[bool, str]:
        """
        生成SSH密钥对

        Args:
            key_path: 密钥路径
            key_type: 密钥类型
            comment: 密钥注释
            overwrite: 是否覆盖

        Returns:
            (是否成功, 消息)
        """
        return self.key_service.generate_key(
            key_path=key_path,
            key_type=key_type,
            comment=comment,
            overwrite=overwrite,
        )

    def generate_and_deploy_key(
        self,
        host: str,
        port: int,
        user: str,
        password: str,
        key_path: str,
        key_type: str = "ed25519",
        comment: str = "openclaw-proxy",
        overwrite: bool = True,
        progress_callback: Optional[Callable[[str], None]] = None,
    ) -> tuple[bool, str, Optional[str]]:
        """
        生成并部署密钥

        Args:
            host: 服务器地址
            port: SSH端口
            user: 用户名
            password: 密码
            key_path: 密钥路径
            key_type: 密钥类型
            comment: 密钥注释
            overwrite: 是否覆盖
            progress_callback: 进度回调

        Returns:
            (是否成功, 消息, 错误详情)
        """
        return self.key_service.generate_and_deploy(
            host=host,
            port=port,
            user=user,
            password=password,
            key_path=key_path,
            key_type=key_type,
            comment=comment,
            overwrite=overwrite,
            progress_callback=progress_callback,
        )

    def generate_and_deploy_key_async(
        self,
        host: str,
        port: int,
        user: str,
        password: str,
        key_path: str,
        key_type: str = "ed25519",
        comment: str = "openclaw-proxy",
        progress_callback: Optional[Callable[[str], None]] = None,
        complete_callback: Optional[Callable[[bool, str, Optional[str]], None]] = None,
    ) -> None:
        """
        异步生成并部署密钥

        Args:
            host: 服务器地址
            port: SSH端口
            user: 用户名
            password: 密码
            key_path: 密钥路径
            key_type: 密钥类型
            comment: 密钥注释
            progress_callback: 进度回调
            complete_callback: 完成回调
        """
        import threading

        def do_generate():
            success, message, error_detail = self.generate_and_deploy_key(
                host=host,
                port=port,
                user=user,
                password=password,
                key_path=key_path,
                key_type=key_type,
                comment=comment,
                progress_callback=lambda msg: (
                    self._update_ui(progress_callback, msg) if progress_callback else None
                ),
            )

            if complete_callback:
                self._update_ui(complete_callback, success, message, error_detail)

        threading.Thread(target=do_generate, daemon=True).start()

    # ============== 连接测试 ==============

    def test_connection(
        self,
        host: str,
        port: int,
        user: str,
        key_path: str,
    ) -> tuple[bool, str]:
        """
        测试SSH连接

        Args:
            host: 服务器地址
            port: SSH端口
            user: 用户名
            key_path: 密钥路径

        Returns:
            (是否成功, 消息)
        """
        return self.key_service.test_connection(
            host=host,
            port=port,
            user=user,
            key_path=key_path,
        )

    def test_connection_async(
        self,
        host: str,
        port: int,
        user: str,
        key_path: str,
        callback: Callable[[bool, str], None],
    ) -> None:
        """
        异步测试SSH连接

        Args:
            host: 服务器地址
            port: SSH端口
            user: 用户名
            key_path: 密钥路径
            callback: 回调函数
        """
        import threading

        def do_test():
            success, message = self.test_connection(host, port, user, key_path)
            self._update_ui(callback, success, message)

        threading.Thread(target=do_test, daemon=True).start()

    def test_host_reachable(
        self,
        host: str,
        port: int,
    ) -> tuple[bool, str]:
        """
        测试主机是否可达

        Args:
            host: 服务器地址
            port: SSH端口

        Returns:
            (是否可达, 消息)
        """
        return self.key_service.test_host_reachable(host, port)

    # ============== 更新检查 ==============

    def check_update_async(self, force: bool = False) -> None:
        """
        异步检查更新

        Args:
            force: 是否强制检查
        """
        self.update_service.check_for_update_async(
            callback=lambda result: None,  # 由UI层处理
            force=force,
        )

    # ============== 端口映射 ==============

    def get_port_mapping_presets(self) -> list[tuple[str, PortMapping]]:
        """
        获取端口映射预设

        Returns:
            预设列表 [(名称, 映射), ...]
        """
        return [
            ("HTTP (80)", PortMapping("127.0.0.1", 80, "127.0.0.1", 80)),
            ("HTTPS (443)", PortMapping("127.0.0.1", 443, "127.0.0.1", 443)),
            ("MySQL (3306)", PortMapping("127.0.0.1", 3306, "127.0.0.1", 3306)),
            ("PostgreSQL (5432)", PortMapping("127.0.0.1", 5432, "127.0.0.1", 5432)),
            ("Redis (6379)", PortMapping("127.0.0.1", 6379, "127.0.0.1", 6379)),
            ("MongoDB (27017)", PortMapping("127.0.0.1", 27017, "127.0.0.1", 27017)),
        ]
