"""
SSH配置对话框
"""

import logging
import tkinter as tk
from tkinter import ttk, messagebox
from typing import TYPE_CHECKING, Optional, Callable
import threading

logger = logging.getLogger("openclaw_proxy")

from ui.base import set_window_icon
from components.port_mapping_frame import PortMappingFrame
from presenters.config_presenter import ConfigPresenter

if TYPE_CHECKING:
    from app.container import ServiceContainer


class ConfigDialog(tk.Toplevel):
    """
    SSH配置对话框

    功能：
    1. SSH连接配置
    2. 密钥生成和部署
    3. 支持新建/编辑服务器
    """

    def __init__(
        self,
        parent,
        container: "ServiceContainer",
        on_save: Optional[Callable] = None,
        server_id: Optional[str] = None,
        is_new: bool = False,
    ):
        super().__init__(parent)
        self._is_new = is_new
        self._server_name = "新增连接" if is_new else "SSH配置"
        self.title(f"{self._server_name} - 连接配置" if is_new else f"OpenClaw连接代理 - {self._server_name}")
        self.resizable(True, True)
        self.transient(parent)

        self._container = container
        self._presenter = ConfigPresenter(container)
        self._on_save = on_save
        self._server_id = server_id
        self._result = False

        set_window_icon(self)

        self._create_widgets()
        self._load_config()

        self.minsize(550, 480)
        self._center_window(800, 600)

        self.grab_set()

    def _center_window(self, width: int, height: int) -> None:
        """窗口居中"""
        self.update_idletasks()
        x = self.master.winfo_x() + (self.master.winfo_width() - width) // 2
        y = self.master.winfo_y() + (self.master.winfo_height() - height) // 2
        self.geometry(f"{width}x{height}+{x}+{y}")

    def _create_widgets(self) -> None:
        """创建组件"""
        main_frame = ttk.Frame(self, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(0, weight=1)

        # SSH配置区域
        canvas = tk.Canvas(main_frame, highlightthickness=0)
        scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=canvas.yview)
        scroll_frame = ttk.Frame(canvas)

        scroll_frame.bind(
            "<Configure>",
            lambda _: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas_window = canvas.create_window((0, 0), window=scroll_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        # Canvas宽度变化时同步scroll_frame宽度
        canvas.bind("<Configure>", lambda e: canvas.itemconfig(canvas_window, width=e.width))

        canvas.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")

        # 鼠标滚轮滚动支持
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        canvas.bind_all("<MouseWheel>", _on_mousewheel)

        scroll_frame.columnconfigure(0, weight=1)
        scroll_frame.columnconfigure(1, weight=1)
        self._create_ssh_frame(scroll_frame)

        # 保存解绑函数引用
        self._mousewheel_unbind = lambda: canvas.unbind_all("<MouseWheel>")

        # 窗口关闭时解绑鼠标滚轮
        self.protocol("WM_DELETE_WINDOW", self._on_close_with_unbind)

        # 底部按钮
        btn_frame = ttk.Frame(main_frame)
        btn_frame.grid(row=1, column=0, columnspan=2, pady=10)

        ttk.Button(btn_frame, text="保存", command=self._on_save_click, width=12).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="取消", command=self.destroy, width=12).pack(side=tk.LEFT, padx=5)

    def _create_ssh_frame(self, parent) -> None:
        """创建SSH配置区域"""
        # 服务器配置
        server_group = ttk.LabelFrame(parent, text="服务器配置", padding=8)
        server_group.grid(row=0, column=0, columnspan=2, sticky="ew", pady=5)
        server_group.columnconfigure(1, weight=1)

        # 服务器名称（新建和编辑模式都显示）
        ttk.Label(server_group, text="服务器名称:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self._name_var = tk.StringVar()
        ttk.Entry(server_group, textvariable=self._name_var).grid(row=0, column=1, sticky="ew", pady=2)
        name_row = 1

        ttk.Label(server_group, text="服务器地址:").grid(row=name_row, column=0, sticky=tk.W, pady=2)
        self._host_var = tk.StringVar()
        host_entry = ttk.Entry(server_group, textvariable=self._host_var)
        host_entry.grid(row=name_row, column=1, sticky="ew", pady=2)
        host_entry.bind("<FocusOut>", self._on_host_change)

        port_row = name_row + 1
        user_row = name_row + 2
        key_row = name_row + 3

        ttk.Label(server_group, text="SSH端口:").grid(row=port_row, column=0, sticky=tk.W, pady=2)
        self._port_var = tk.StringVar()
        ttk.Entry(server_group, textvariable=self._port_var, width=10).grid(row=port_row, column=1, sticky=tk.W, pady=2)

        ttk.Label(server_group, text="用户名:").grid(row=user_row, column=0, sticky=tk.W, pady=2)
        self._user_var = tk.StringVar()
        ttk.Entry(server_group, textvariable=self._user_var).grid(row=user_row, column=1, sticky="ew", pady=2)

        # 密钥配置行
        ttk.Label(server_group, text="密钥:").grid(row=key_row, column=0, sticky=tk.W, pady=2)

        key_frame = ttk.Frame(server_group)
        key_frame.grid(row=key_row, column=1, sticky="ew", pady=2)
        key_frame.columnconfigure(0, weight=1)

        self._key_display_var = tk.StringVar()
        key_entry = ttk.Entry(key_frame, textvariable=self._key_display_var, state="readonly")
        key_entry.grid(row=0, column=0, sticky="ew", padx=(0, 5))

        self._deploy_key_btn = ttk.Button(key_frame, text="部署公钥", command=self._deploy_public_key, width=10)
        self._deploy_key_btn.grid(row=0, column=1, padx=2)

        # ttk.Button(key_frame, text="测试", command=self._test_connection, width=6).grid(row=0, column=2, padx=2)

        # SSH连接选项
        options_group = ttk.LabelFrame(parent, text="连接选项", padding=8)
        options_group.grid(row=1, column=0, columnspan=2, sticky="ew", pady=5)
        options_group.columnconfigure(1, weight=1)

        # 自动运行
        self._auto_run_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            options_group,
            text="应用启动时自动运行",
            variable=self._auto_run_var,
        ).grid(row=0, column=0, columnspan=2, sticky=tk.W, pady=2)

        # 主机密钥校验
        ttk.Label(options_group, text="主机密钥校验:").grid(row=1, column=0, sticky=tk.W, pady=2)
        self._strict_host_key_var = tk.StringVar()
        strict_combo = ttk.Combobox(options_group, textvariable=self._strict_host_key_var, width=15, state="readonly")
        strict_combo["values"] = ("accept-new", "yes", "no")
        strict_combo.grid(row=1, column=1, sticky=tk.W, pady=2)

        # 连接超时、保活间隔、启用压缩同一行
        timeout_frame = ttk.Frame(options_group)
        timeout_frame.grid(row=2, column=0, columnspan=2, sticky="ew", pady=5)

        ttk.Label(timeout_frame, text="连接超时(秒):").pack(side=tk.LEFT)
        self._connect_timeout_var = tk.StringVar()
        ttk.Entry(timeout_frame, textvariable=self._connect_timeout_var, width=8).pack(side=tk.LEFT, padx=(0, 15))
        ttk.Label(timeout_frame, text="保活间隔(秒):").pack(side=tk.LEFT)
        self._alive_interval_var = tk.StringVar()
        ttk.Entry(timeout_frame, textvariable=self._alive_interval_var, width=8).pack(side=tk.LEFT, padx=(0, 15))
        self._compression_var = tk.BooleanVar()
        ttk.Checkbutton(timeout_frame, text="启用压缩", variable=self._compression_var).pack(side=tk.LEFT)

        # 端口转发配置
        self._port_mapping_frame = PortMappingFrame(parent, on_change=lambda: None)
        self._port_mapping_frame.grid(row=2, column=0, columnspan=2, sticky="ew", pady=5)

    def _load_config(self) -> None:
        """加载配置"""
        # 新建模式：加载默认值
        if self._is_new:
            self._port_var.set("22")
            self._user_var.set("root")
            self._strict_host_key_var.set("accept-new")
            self._connect_timeout_var.set("10")
            self._alive_interval_var.set("30")
            self._compression_var.set(False)
            # 检查密钥配置
            self._check_and_prompt_key_config()
            return

        # 如果指定了 server_id，加载该服务器配置
        if self._server_id:
            self._load_server_config(self._server_id)
        else:
            config = self._presenter.load_config()
            self._host_var.set(config.ssh.host)
            self._port_var.set(str(config.ssh.port))
            self._user_var.set(config.ssh.user)

            # 加载连接选项
            self._strict_host_key_var.set(config.ssh.strict_host_key_checking)
            self._connect_timeout_var.set(str(config.ssh.connect_timeout))
            self._alive_interval_var.set(str(config.ssh.server_alive_interval))
            self._compression_var.set(config.ssh.compression)

            if config.ssh.port_mappings:
                self._port_mapping_frame.set_mappings(config.ssh.port_mappings)

        # 检查密钥文件是否存在
        self._check_and_prompt_key_config()

    def _check_and_prompt_key_config(self) -> None:
        """检查密钥配置，如果不存在则提示用户配置"""
        import os
        from utils.path_utils import expand_path
        from repositories.json_config_repository import JsonConfigRepository

        # 获取密钥路径（统一从 global.keygen 获取）
        if self._is_new or self._server_id:
            config_dir = os.path.join(os.path.expanduser("~"), ".openclaw-proxy")
            json_repo = JsonConfigRepository(config_dir)
            multi_config = json_repo.load_multi()
            key_path = expand_path(multi_config.global_config.keygen.key_path)
        else:
            config = self._presenter.load_config()
            key_path = expand_path(config.ssh.key_path)

        # 检查密钥文件是否存在
        if not key_path or not os.path.exists(key_path):
            # 提示用户配置密钥
            server_display = self._server_name if not self._is_new else "新服务器"
            result = messagebox.askyesno(
                "密钥未配置",
                f"服务器 [{server_display}] 的密钥文件不存在或未配置。\n\n是否现在配置密钥？",
                parent=self
            )
            if result:
                # 打开密钥配置弹窗
                self._open_security_dialog()

        # 更新密钥显示
        self._update_key_display()

    def _open_security_dialog(self) -> None:
        """打开密钥管理弹窗"""
        from ui.dialogs.security_dialog import SecurityDialog

        dialog = SecurityDialog(self, self._container, on_save=self._on_key_configured)
        self.wait_window(dialog)

    def _on_key_configured(self) -> None:
        """密钥配置完成后的回调"""
        # 密钥路径已保存在 global.keygen 中，服务器配置不需要单独存储
        # 只需更新密钥显示
        self._update_key_display()

    def _load_server_config(self, server_id: str) -> None:
        """加载指定服务器的配置"""
        from repositories.json_config_repository import JsonConfigRepository
        import os

        config_dir = os.path.join(os.path.expanduser("~"), ".openclaw-proxy")
        json_repo = JsonConfigRepository(config_dir)
        multi_config = json_repo.load_multi()

        server = multi_config.get_server_by_id(server_id)
        if server:
            # 更新窗口标题
            self._server_name = server.name
            self.title(f"{self._server_name} - 连接配置")

            # 加载服务器名称
            if self._name_var:
                self._name_var.set(server.name)

            self._host_var.set(server.ssh.host)
            self._port_var.set(str(server.ssh.port))
            self._user_var.set(server.ssh.user)

            # 加载连接选项
            self._auto_run_var.set(server.auto_run)
            self._strict_host_key_var.set(server.ssh.strict_host_key_checking)
            self._connect_timeout_var.set(str(server.ssh.connect_timeout))
            self._alive_interval_var.set(str(server.ssh.server_alive_interval))
            self._compression_var.set(server.ssh.compression)

            # 转换端口映射格式
            from models.port_mapping import PortMapping
            port_mappings = [
                PortMapping(
                    local_bind_host=pm.local_bind_host,
                    local_port=pm.local_port,
                    remote_host=pm.remote_host,
                    remote_port=pm.remote_port,
                    is_openclaw=pm.is_openclaw,
                )
                for pm in server.port_mappings
            ]
            if port_mappings:
                self._port_mapping_frame.set_mappings(port_mappings)

    def _save_config(self):
        """保存配置到对象"""
        if self._server_id:
            return self._save_server_config(self._server_id)

        config = self._presenter.load_config()

        config.ssh.host = self._host_var.get().strip()
        config.ssh.port = int(self._port_var.get() or 22)
        config.ssh.user = self._user_var.get().strip()
        config.ssh.port_mappings = self._port_mapping_frame.get_mappings()

        # 保存连接选项
        config.ssh.strict_host_key_checking = self._strict_host_key_var.get()
        config.ssh.connect_timeout = int(self._connect_timeout_var.get() or 10)
        config.ssh.server_alive_interval = int(self._alive_interval_var.get() or 30)
        config.ssh.compression = self._compression_var.get()

        return config

    def _save_server_config(self, server_id: str):
        """保存指定服务器的配置"""
        from repositories.json_config_repository import JsonConfigRepository
        from models.server_config import PortMappingConfig
        import os

        config_dir = os.path.join(os.path.expanduser("~"), ".openclaw-proxy")
        json_repo = JsonConfigRepository(config_dir)
        multi_config = json_repo.load_multi()

        server = multi_config.get_server_by_id(server_id)
        if server:
            # 更新服务器名称（优先使用输入的名称，否则使用主机地址）
            name = self._name_var.get().strip() if self._name_var else ""
            server.name = name or self._host_var.get().strip()

            server.ssh.host = self._host_var.get().strip()
            server.ssh.port = int(self._port_var.get() or 22)
            server.ssh.user = self._user_var.get().strip()

            # 保存连接选项
            server.auto_run = self._auto_run_var.get()
            server.ssh.strict_host_key_checking = self._strict_host_key_var.get()
            server.ssh.connect_timeout = int(self._connect_timeout_var.get() or 10)
            server.ssh.server_alive_interval = int(self._alive_interval_var.get() or 30)
            server.ssh.compression = self._compression_var.get()

            # 转换端口映射格式
            port_mappings = self._port_mapping_frame.get_mappings()
            server.port_mappings = [
                PortMappingConfig(
                    name=f"端口 {pm.local_port}",
                    enabled=True,
                    local_bind_host=pm.local_bind_host,
                    local_port=pm.local_port,
                    remote_host=pm.remote_host,
                    remote_port=pm.remote_port,
                    is_openclaw=pm.is_openclaw,
                )
                for pm in port_mappings
            ]

            # 保存到 JSON 配置
            json_repo.save(multi_config)

        # 返回旧版 Config 格式（用于兼容）
        return multi_config.to_legacy_config()

    def _create_new_server(self) -> bool:
        """创建新服务器"""
        from repositories.json_config_repository import JsonConfigRepository
        from models.server_config import ServerConfig, SSHConfig, PortMappingConfig
        import os
        import uuid

        # 获取表单数据
        name = self._name_var.get().strip() if self._name_var else ""
        host = self._host_var.get().strip()
        port = int(self._port_var.get() or 22)
        user = self._user_var.get().strip()

        # 加载配置
        config_dir = os.path.join(os.path.expanduser("~"), ".openclaw-proxy")
        json_repo = JsonConfigRepository(config_dir)
        multi_config = json_repo.load_multi()

        # 获取端口映射
        port_mappings = self._port_mapping_frame.get_mappings()

        # 创建服务器配置（key_path 和 known_hosts 从 global.keygen 获取，不在此存储）
        server = ServerConfig(
            id=f"srv-{uuid.uuid4().hex[:8]}",
            name=name or host,
            enabled=True,
            auto_run=self._auto_run_var.get(),
            ssh=SSHConfig(
                host=host,
                port=port,
                user=user,
                strict_host_key_checking=self._strict_host_key_var.get(),
                connect_timeout=int(self._connect_timeout_var.get() or 10),
                server_alive_interval=int(self._alive_interval_var.get() or 30),
                server_alive_count_max=3,
                compression=self._compression_var.get(),
            ),
            port_mappings=[
                PortMappingConfig(
                    id=f"pm-{uuid.uuid4().hex[:8]}",
                    name=f"端口 {pm.local_port}",
                    enabled=True,
                    local_bind_host=pm.local_bind_host,
                    local_port=pm.local_port,
                    remote_host=pm.remote_host,
                    remote_port=pm.remote_port,
                    is_openclaw=pm.is_openclaw,
                )
                for pm in port_mappings
            ] if port_mappings else [
                PortMappingConfig(
                    id=f"pm-{uuid.uuid4().hex[:8]}",
                    name="主映射",
                    enabled=True,
                    local_bind_host="127.0.0.1",
                    local_port=18789,
                    remote_host="127.0.0.1",
                    remote_port=18789,
                    is_openclaw=False,
                )
            ],
        )

        # 添加到配置并保存
        multi_config.servers.append(server)
        if json_repo.save(multi_config):
            logger.info(f"创建新服务器: {server.name}")
            return True
        else:
            messagebox.showerror("错误", "保存服务器配置失败", parent=self)
            return False

    def get_result(self) -> bool:
        """获取结果"""
        return self._result

    def _validate_config(self, host: str, port: int, port_mappings: list) -> tuple[bool, list[str]]:
        """
        验证配置参数

        Args:
            host: 服务器地址
            port: SSH端口
            port_mappings: 端口映射列表

        Returns:
            (是否验证通过, 错误信息列表)
        """
        import os
        from repositories.json_config_repository import JsonConfigRepository

        errors = []

        # 加载现有配置
        config_dir = os.path.join(os.path.expanduser("~"), ".openclaw-proxy")
        json_repo = JsonConfigRepository(config_dir)
        multi_config = json_repo.load_multi()

        # 1. 检查服务器地址+SSH端口是否重复
        for server in multi_config.servers:
            # 编辑模式下跳过自己
            if self._server_id and server.id == self._server_id:
                continue

            if server.ssh.host == host and server.ssh.port == port:
                errors.append(f"服务器地址 {host}:{port} 已存在于「{server.name}」")
                break

        # 2. 检查本地端口是否与其他服务器冲突
        current_local_ports = set()
        for pm in port_mappings:
            key = (pm.local_bind_host, pm.local_port)
            current_local_ports.add(key)

        for server in multi_config.servers:
            # 编辑模式下跳过自己
            if self._server_id and server.id == self._server_id:
                continue

            for pm in server.port_mappings:
                key = (pm.local_bind_host, pm.local_port)
                if key in current_local_ports:
                    errors.append(
                        f"本地端口 {pm.local_bind_host}:{pm.local_port} 已被「{server.name}」使用"
                    )

        # 3. 检查本地端口是否被系统占用
        for pm in port_mappings:
            if self._is_port_in_use(pm.local_bind_host, pm.local_port):
                errors.append(f"本地端口 {pm.local_bind_host}:{pm.local_port} 已被系统占用")

        return len(errors) == 0, errors

    def _is_port_in_use(self, host: str, port: int) -> bool:
        """
        检查端口是否被系统占用

        Args:
            host: 绑定地址
            port: 端口号

        Returns:
            是否被占用
        """
        import socket
        try:
            # 尝试绑定端口，如果成功说明端口未被占用
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(1)
                s.bind((host, port))
                return False
        except OSError:
            return True

    def _on_save_click(self) -> None:
        """保存按钮点击"""
        # 验证必填字段
        host = self._host_var.get().strip()
        if not host:
            messagebox.showerror("错误", "请输入服务器地址", parent=self)
            return

        # 获取端口
        try:
            port = int(self._port_var.get() or 22)
        except ValueError:
            messagebox.showerror("错误", "SSH端口必须是数字", parent=self)
            return

        # 获取端口映射
        port_mappings = self._port_mapping_frame.get_mappings()

        # 验证配置参数
        valid, errors = self._validate_config(host, port, port_mappings)
        if not valid:
            messagebox.showerror("配置验证失败", "\n".join(errors), parent=self)
            return

        # 新建模式：创建新服务器
        if self._is_new:
            success = self._create_new_server()
            if success:
                self._result = True
                if self._on_save:
                    self._on_save()
                self.destroy()
            return

        # 编辑模式：保存配置
        config = self._save_config()

        # 如果是编辑指定服务器，直接保存到 JSON
        if self._server_id:
            if self._on_save:
                self._on_save()
            self.destroy()
            return

        # 保存到旧版配置（兼容模式）
        if self._presenter.save_config(config):
            errors = []

            # 如果隧道正在运行，重启让配置生效
            tunnel_service = self._container.tunnel_service
            if tunnel_service.is_running:
                success, message = tunnel_service.restart()
                if not success:
                    errors.append(f"重启代理失败: {message}")
                    logger.warning(f"重启代理失败: {message}")

            # 如果启用了自动获取 token，重新获取
            if config.browser.auto_fetch_token:
                logger.info("保存配置后重新获取 token...")
                self._container.token_service.clear_cache()
                success, error_msg = self._container.token_service.fetch_token_sync()
                if success:
                    logger.info("Token 获取成功")
                else:
                    errors.append(f"Token 获取失败: {error_msg}")
                    logger.warning(f"Token 获取失败: {error_msg}")

            if errors:
                messagebox.showwarning("警告", "\n".join(errors), parent=self)

            if self._on_save:
                self._on_save()
            self.destroy()
        else:
            messagebox.showerror("错误", "保存配置失败", parent=self)

    def _update_key_display(self) -> None:
        """更新密钥显示状态"""
        import os
        from utils.path_utils import expand_path
        from repositories.json_config_repository import JsonConfigRepository

        # 获取密钥路径（统一从 global.keygen 获取）
        if self._is_new or self._server_id:
            config_dir = os.path.join(os.path.expanduser("~"), ".openclaw-proxy")
            json_repo = JsonConfigRepository(config_dir)
            multi_config = json_repo.load_multi()
            key_path = expand_path(multi_config.global_config.keygen.key_path)
        else:
            config = self._presenter.load_config()
            key_path = expand_path(config.ssh.key_path)

        if key_path and os.path.exists(key_path):
            self._key_display_var.set(os.path.basename(key_path))
        else:
            self._key_display_var.set("(未配置)")

    def _deploy_public_key(self) -> None:
        """部署公钥到远程服务器"""        
        host = self._host_var.get().strip()
        port_str = self._port_var.get().strip()
        user = self._user_var.get().strip()

        if not host:
            messagebox.showerror("错误", "请输入服务器地址", parent=self)
            return
        if not port_str:
            messagebox.showerror("错误", "请输入SSH端口", parent=self)
            return
        if not user:
            messagebox.showerror("错误", "请输入用户名", parent=self)
            return

        # 获取密钥路径（统一从 global.keygen 获取）
        import os
        from utils.path_utils import expand_path

        if self._server_id or self._is_new:
            from repositories.json_config_repository import JsonConfigRepository
            config_dir = os.path.join(os.path.expanduser("~"), ".openclaw-proxy")
            json_repo = JsonConfigRepository(config_dir)
            multi_config = json_repo.load_multi()
            key_path = expand_path(multi_config.global_config.keygen.key_path)
        else:
            config = self._presenter.load_config()
            key_path = expand_path(config.ssh.key_path)

        if not key_path or not os.path.exists(key_path):
            messagebox.showerror("错误", "密钥文件不存在，请先在密钥管理中生成密钥", parent=self)
            return

        # 检查公钥是否存在
        pub_key_path = key_path + ".pub"
        if not os.path.exists(pub_key_path):
            messagebox.showerror("错误", f"公钥文件不存在:\n{pub_key_path}", parent=self)
            return

        # 先测试当前密钥是否可以连接（检查公钥是否已部署）
        def check_and_deploy():
            try:
                port_val = int(port_str)
                success, message = self._container.key_service.test_connection(
                    host=host,
                    port=port_val,
                    user=user,
                    key_path=key_path,
                )
                if success:
                    # 公钥已部署，直接提示
                    self.after(0, lambda: messagebox.showinfo("提示", "公钥已部署，无需重复部署", parent=self))
                    return
            except Exception as e:
                logger.debug(f"测试密钥连接失败: {e}")

            # 公钥未部署，弹出密码输入框
            self.after(0, lambda: self._show_deploy_dialog(host, port_str, user, key_path))

        threading.Thread(target=check_and_deploy, daemon=True).start()

    def _show_deploy_dialog(self, host: str, port_str: str, user: str, key_path: str) -> None:
        """显示部署公钥对话框"""
        # 弹出密码输入框
        dialog = tk.Toplevel(self)
        dialog.title("部署公钥")
        dialog.transient(self)
        dialog.grab_set()
        dialog.resizable(False, False)
        set_window_icon(dialog)

        frame = ttk.Frame(dialog, padding=15)
        frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frame, text=f"将公钥部署到 {user}@{host}").grid(row=0, column=0, columnspan=2, pady=5)

        ttk.Label(frame, text="密码:").grid(row=1, column=0, sticky=tk.W, pady=5)
        password_var = tk.StringVar()
        password_entry = ttk.Entry(frame, textvariable=password_var, show="*", width=25)
        password_entry.grid(row=1, column=1, pady=5, padx=(5, 0))

        status_var = tk.StringVar(value="")
        status_label = ttk.Label(frame, textvariable=status_var, foreground="blue")
        status_label.grid(row=2, column=0, columnspan=2, pady=10)

        btn_frame = ttk.Frame(frame)
        btn_frame.grid(row=3, column=0, columnspan=2, pady=(10, 0))
        ok_btn = ttk.Button(btn_frame, text="确定", width=10)
        ok_btn.pack(side=tk.LEFT, padx=5)
        cancel_btn = ttk.Button(btn_frame, text="取消", width=10)
        cancel_btn.pack(side=tk.LEFT, padx=5)

        def set_ui_enabled(enabled: bool):
            state = tk.NORMAL if enabled else tk.DISABLED
            password_entry.config(state=state)
            ok_btn.config(state=state)
            cancel_btn.config(state=state)

        def update_status(msg: str):
            dialog.after(0, lambda: status_var.set(msg))

        def show_error(msg: str):
            def do_show():
                status_var.set(f"✗ {msg}")
                status_label.config(foreground="red")
                messagebox.showerror("失败", msg, parent=dialog)
                set_ui_enabled(True)
                dialog.after(100, lambda: status_label.config(foreground="blue"))
            dialog.after(0, do_show)

        def on_ok(_event=None):
            password_val = password_var.get()
            if not password_val:
                messagebox.showerror("错误", "请输入密码", parent=dialog)
                return

            set_ui_enabled(False)
            update_status("正在部署公钥...")

            def do_deploy():
                try:
                    port_val = int(port_str)
                    success, message, error_detail = self._container.key_service.deploy_key(
                        host=host,
                        port=port_val,
                        user=user,
                        password=password_val,
                        key_path=key_path,
                        progress_callback=update_status,
                    )

                    if not dialog.winfo_exists():
                        return

                    if success:
                        dialog.after(0, lambda: on_deploy_success())
                    else:
                        error_msg = message
                        if error_detail:
                            error_msg += f"\n{error_detail}"
                        show_error(error_msg)

                except Exception as e:
                    if dialog.winfo_exists():
                        show_error(f"部署失败: {str(e)}")

            def on_deploy_success():
                messagebox.showinfo("成功", "公钥部署成功", parent=dialog)
                dialog.destroy()

            threading.Thread(target=do_deploy, daemon=True).start()

        def on_cancel():
            dialog.destroy()

        ok_btn.config(command=on_ok)
        cancel_btn.config(command=on_cancel)
        dialog.bind("<Return>", on_ok)
        dialog.bind("<Escape>", lambda _e: on_cancel())

        dialog.update_idletasks()
        x = self.winfo_x() + (self.winfo_width() - dialog.winfo_width()) // 2
        y = self.winfo_y() + (self.winfo_height() - dialog.winfo_height()) // 2
        dialog.geometry(f"+{x}+{y}")

        password_entry.focus_set()
        dialog.wait_window()

    def _test_connection(self) -> None:
        """测试连接"""
        host = self._host_var.get().strip()
        port_str = self._port_var.get().strip()
        user = self._user_var.get().strip()

        # 获取密钥路径（统一从 global.keygen 获取）
        if self._server_id or self._is_new:
            import os
            from utils.path_utils import expand_path
            from repositories.json_config_repository import JsonConfigRepository
            config_dir = os.path.join(os.path.expanduser("~"), ".openclaw-proxy")
            json_repo = JsonConfigRepository(config_dir)
            multi_config = json_repo.load_multi()
            key_path = multi_config.global_config.keygen.key_path
        else:
            config = self._presenter.load_config()
            key_path = config.ssh.key_path

        def on_result(success: bool, message: str):
            if success:
                messagebox.showinfo("成功", message, parent=self)
            else:
                messagebox.showerror("失败", message, parent=self)

        self._presenter.test_connection_async(
            host=host,
            port=int(port_str or 22),
            user=user,
            key_path=key_path,
            callback=on_result,
        )

    def _on_host_change(self, _) -> None:
        """服务器地址变更时自动查找匹配的密钥"""
        import os
        from utils.path_utils import find_key_for_host

        host = self._host_var.get().strip()
        key_path = find_key_for_host(host)

        if key_path:
            # 密钥路径统一存储在 global.keygen 中
            # 如果需要更新，应该更新全局配置而不是服务器配置
            self._update_key_display()
            logger.info(f"已自动匹配密钥: {key_path}")
        else:
            self._update_key_display()
            logger.debug(f"未找到匹配 {host} 的密钥")

    def _on_close_with_unbind(self) -> None:
        """窗口关闭时解绑鼠标滚轮事件"""
        if hasattr(self, '_mousewheel_unbind'):
            self._mousewheel_unbind()
        self.destroy()
