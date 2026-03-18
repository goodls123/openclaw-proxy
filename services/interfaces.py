"""
服务接口定义
使用Protocol定义接口，便于依赖注入和测试
"""

from typing import Protocol, Optional, Tuple, Callable, Any, runtime_checkable

from models import Config, TunnelState, PortMapping, ReleaseInfo, UpdateCheckResult


# ============== Repository 接口 ==============

@runtime_checkable
class IConfigRepository(Protocol):
    """配置仓库接口"""

    @property
    def config_file(self) -> str:
        """配置文件路径"""
        ...

    def load(self) -> Config:
        """加载配置"""
        ...

    def save(self, config: Config) -> bool:
        """保存配置"""
        ...

    def has_backup(self) -> bool:
        """是否有备份"""
        ...

    def restore_backup(self) -> bool:
        """恢复备份"""
        ...


@runtime_checkable
class IRemoteConfigRepository(Protocol):
    """远程配置仓库接口"""

    def fetch(
        self,
        host: str,
        port: int,
        user: str,
        key_path: str,
        remote_path: str,
        timeout: int = 10,
    ) -> Tuple[bool, Any, str]:
        """
        获取远程配置

        Returns:
            (是否成功, 配置字典, 错误信息)
        """
        ...

    def extract_token(self, config: Any) -> Tuple[bool, str]:
        """
        从配置中提取token

        Returns:
            (是否成功, token或错误信息)
        """
        ...


# ============== Service 接口 ==============

@runtime_checkable
class ITunnelService(Protocol):
    """隧道服务接口"""

    @property
    def state(self) -> TunnelState:
        """获取当前状态"""
        ...

    @property
    def is_running(self) -> bool:
        """是否正在运行"""
        ...

    @property
    def pid(self) -> Optional[int]:
        """获取进程ID"""
        ...

    def check_prerequisites(self) -> Tuple[bool, str]:
        """
        检查运行前置条件

        Returns:
            (是否满足, 错误信息)
        """
        ...

    def start(self) -> Tuple[bool, str]:
        """
        启动隧道

        Returns:
            (是否成功, 消息)
        """
        ...

    def stop(self) -> Tuple[bool, str]:
        """
        停止隧道

        Returns:
            (是否成功, 消息)
        """
        ...

    def restart(self) -> Tuple[bool, str]:
        """
        重启隧道

        Returns:
            (是否成功, 消息)
        """
        ...

    def wait_for_connection(self, timeout: int = 10) -> Tuple[bool, str]:
        """
        等待连接建立

        Returns:
            (是否成功, 消息)
        """
        ...


@runtime_checkable
class IKeyService(Protocol):
    """密钥服务接口"""

    def key_exists(self, key_path: Optional[str] = None) -> bool:
        """
        检查密钥是否存在

        Args:
            key_path: 密钥路径，None则使用配置中的路径
        """
        ...

    def generate_key(
        self,
        key_path: str,
        key_type: str = "ed25519",
        comment: str = "openclaw-proxy",
        overwrite: bool = False,
        passphrase: str = "",
    ) -> Tuple[bool, str]:
        """
        生成SSH密钥对

        Returns:
            (是否成功, 消息)
        """
        ...

    def deploy_key(
        self,
        host: str,
        port: int,
        user: str,
        password: str,
        key_path: str,
        progress_callback: Optional[Callable[[str], None]] = None,
    ) -> Tuple[bool, str, Optional[str]]:
        """
        部署公钥到远程服务器

        Returns:
            (是否成功, 消息, 错误详情)
        """
        ...

    def test_connection(
        self,
        host: str,
        port: int,
        user: str,
        key_path: str,
        timeout: int = 10,
    ) -> Tuple[bool, str]:
        """
        测试密钥连接

        Returns:
            (是否成功, 消息)
        """
        ...

    def test_host_reachable(self, host: str, port: int, timeout: int = 5) -> Tuple[bool, str]:
        """
        测试主机是否可达

        Returns:
            (是否可达, 消息)
        """
        ...


@runtime_checkable
class ITokenService(Protocol):
    """Token服务接口"""

    @property
    def token(self) -> Optional[str]:
        """获取当前token（可能为空）"""
        ...

    def get_token(self) -> Optional[str]:
        """获取token（优先内存缓存，其次配置文件）"""
        ...

    def fetch_token_sync(self) -> Tuple[bool, str]:
        """
        同步获取token

        Returns:
            (是否成功, token或错误信息)
        """
        ...

    def fetch_token_async(self, callback: Callable[[bool, str], None]) -> None:
        """
        异步获取token

        Args:
            callback: 回调函数，参数为(是否成功, token或错误信息)
        """
        ...

    def get_browser_url(self) -> str:
        """获取带token的浏览器URL"""
        ...

    def clear_cache(self) -> None:
        """清除token缓存"""
        ...


@runtime_checkable
class IBrowserService(Protocol):
    """浏览器服务接口"""

    def open(self, url: Optional[str] = None) -> bool:
        """
        打开浏览器

        Args:
            url: 要打开的URL，None则使用配置中的URL

        Returns:
            是否成功
        """
        ...

    def get_url(self) -> str:
        """获取要打开的URL（带token）"""
        ...


@runtime_checkable
class IUpdateService(Protocol):
    """更新服务接口"""

    def check_for_update(
        self,
        force: bool = False,
    ) -> UpdateCheckResult:
        """
        检查更新

        Args:
            force: 是否强制检查（忽略时间间隔）

        Returns:
            更新检查结果
        """
        ...

    def check_for_update_async(
        self,
        callback: Callable[[UpdateCheckResult], None],
        force: bool = False,
    ) -> None:
        """
        异步检查更新

        Args:
            callback: 回调函数
            force: 是否强制检查
        """
        ...

    @property
    def current_version(self) -> str:
        """当前版本"""
        ...

    @property
    def releases_url(self) -> str:
        """发布页面URL"""
        ...
