"""
Presenter基类
"""

from abc import ABC, abstractmethod
from typing import Callable, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from app.container import ServiceContainer


class BasePresenter(ABC):
    """
    Presenter基类

    Presenter负责：
    1. 接收UI事件
    2. 调用Service处理业务逻辑
    3. 更新UI状态

    Presenter不应该：
    1. 直接导入tkinter
    2. 直接操作UI控件
    3. 包含业务逻辑（应放在Service中）
    """

    def __init__(self, container: "ServiceContainer"):
        """
        初始化Presenter

        Args:
            container: 服务容器，提供所有依赖的服务
        """
        self._container = container
        self._view: Any = None

    @property
    def container(self) -> "ServiceContainer":
        """获取服务容器"""
        return self._container

    @property
    def view(self) -> Any:
        """获取绑定的视图"""
        return self._view

    def attach_view(self, view: Any) -> None:
        """
        绑定视图

        Args:
            view: 视图对象（窗口或控件）
        """
        self._view = view
        self._on_view_attached()

    def detach_view(self) -> None:
        """解绑视图"""
        self._on_view_detaching()
        self._view = None

    def _on_view_attached(self) -> None:
        """视图绑定后的回调（子类可重写）"""
        pass

    def _on_view_detaching(self) -> None:
        """视图解绑前的回调（子类可重写）"""
        pass

    def _run_on_ui_thread(self, callback: Callable[..., None]) -> None:
        """
        在UI线程执行回调

        Args:
            callback: 要执行的回调函数
        """
        if self._view is not None and hasattr(self._view, "root"):
            try:
                self._view.root.after(0, callback)
            except Exception:
                # 如果窗口已关闭，忽略错误
                pass

    def _update_ui(self, update_func: Callable[..., None], *args, **kwargs) -> None:
        """
        更新UI（线程安全）

        Args:
            update_func: 更新函数
            *args: 位置参数
            **kwargs: 关键字参数
        """
        def do_update():
            if self._view is not None:
                try:
                    update_func(*args, **kwargs)
                except Exception:
                    pass

        self._run_on_ui_thread(do_update)

    # ============== 便捷访问服务的属性 ==============

    @property
    def config_repo(self):
        """获取配置仓库"""
        return self._container.config_repo

    @property
    def tunnel_service(self):
        """获取隧道服务"""
        return self._container.tunnel_service

    @property
    def key_service(self):
        """获取密钥服务"""
        return self._container.key_service

    @property
    def token_service(self):
        """获取Token服务"""
        return self._container.token_service

    @property
    def browser_service(self):
        """获取浏览器服务"""
        return self._container.browser_service

    @property
    def update_service(self):
        """获取更新服务"""
        return self._container.update_service
