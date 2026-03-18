"""
配置窗口
"""

import tkinter as tk
from tkinter import ttk, messagebox
from typing import TYPE_CHECKING, Optional, Callable
import threading

from ui.base import BaseDialog, get_font, center_on_parent, set_window_icon
from components.port_mapping_frame import PortMappingFrame
from presenters.config_presenter import ConfigPresenter
from models import Config

if TYPE_CHECKING:
    from app.container import ServiceContainer


class ConfigWindow(tk.Toplevel):
    """
    配置窗口

    功能：
    1. SSH连接配置
    2. 安全设置
    3. 浏览器配置
    4. 更新配置
    5. 密钥生成和部署
    """

    def __init__(
        self,
        parent,
        container: "ServiceContainer",
        on_save: Optional[Callable] = None,
    ):
        """
        初始化配置窗口

        Args:
            parent: 父窗口
            container: 服务容器
            on_save: 保存回调
        """
        super().__init__(parent)
        self.title("OpenClaw代理配置")
        self.resizable(True, True)
        self.transient(parent)

        self._container = container
        self._presenter = ConfigPresenter(container)
        self._presenter.attach_view(self)
        self._on_save = on_save

        # 设置窗口图标
        from ui.base import set_window_icon
        set_window_icon(self)

        self._create_widgets()
        self._load_config()

        # 设置最小尺寸和居中
        self.minsize(600, 500)
        self._center_window(600, 500)

        # 模态对话框
        self.grab_set()

    def _center_window(self, width: int, height: int) -> None:
        """窗口居中"""
        self.update_idletasks()
        x = self.master.winfo_x() + (self.master.winfo_width() - width) // 2
        y = self.master.winfo_y() + (self.master.winfo_height() - height) // 2
        self.geometry(f"{width}x{height}+{x}+{y}")

    def _create_widgets(self) -> None:
        """创建组件"""
        # 主框架
        main_frame = ttk.Frame(self, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(0, weight=1)

        # 标签页
        notebook = ttk.Notebook(main_frame)
        notebook.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)

        # SSH连接配置
        ssh_frame = ttk.Frame(notebook, padding=10)
        notebook.add(ssh_frame, text="SSH连接")
        self._create_ssh_frame(ssh_frame)

        # 安全配置
        security_frame = ttk.Frame(notebook, padding=10)
        notebook.add(security_frame, text="安全设置")
        self._create_security_frame(security_frame)

        # 浏览器配置
        browser_frame = ttk.Frame(notebook, padding=10)
        notebook.add(browser_frame, text="浏览器")
        self._create_browser_frame(browser_frame)

        # 更新配置
        update_frame = ttk.Frame(notebook, padding=10)
        notebook.add(update_frame, text="更新")
        self._create_update_frame(update_frame)

        # 底部按钮
        btn_frame = ttk.Frame(main_frame)
        btn_frame.grid(row=1, column=0, pady=10)
        ttk.Button(btn_frame, text="保存并关闭", command=self._on_save_click, width=12).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="恢复备份", command=self._restore_backup, width=12).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="取消", command=self.destroy, width=12).pack(side=tk.LEFT, padx=5)

    def _create_ssh_frame(self, parent) -> None:
        """创建SSH配置页"""
        parent.columnconfigure(1, weight=1)

        # 服务器配置
        server_group = ttk.LabelFrame(parent, text="服务器配置", padding=8)
        server_group.grid(row=0, column=0, columnspan=2, sticky="ew", pady=5)
        server_group.columnconfigure(1, weight=1)

        ttk.Label(server_group, text="服务器地址:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self._host_var = tk.StringVar()
        ttk.Entry(server_group, textvariable=self._host_var).grid(row=0, column=1, sticky="ew", pady=2)

        ttk.Label(server_group, text="SSH端口:").grid(row=1, column=0, sticky=tk.W, pady=2)
        self._port_var = tk.StringVar()
        ttk.Entry(server_group, textvariable=self._port_var, width=10).grid(row=1, column=1, sticky=tk.W, pady=2)

        ttk.Label(server_group, text="用户名:").grid(row=2, column=0, sticky=tk.W, pady=2)
        self._user_var = tk.StringVar()
        ttk.Entry(server_group, textvariable=self._user_var).grid(row=2, column=1, sticky="ew", pady=2)

        # 密钥配置行
        ttk.Label(server_group, text="密钥:").grid(row=3, column=0, sticky=tk.W, pady=2)

        key_frame = ttk.Frame(server_group)
        key_frame.grid(row=3, column=1, sticky="ew", pady=2)
        key_frame.columnconfigure(0, weight=1)

        # 密钥路径输入框（只读）
        self._key_display_var = tk.StringVar()
        key_entry = ttk.Entry(key_frame, textvariable=self._key_display_var, state="readonly")
        key_entry.grid(row=0, column=0, sticky="ew", padx=(0, 5))

        # 生成/重新生成按钮
        self._generate_key_btn = ttk.Button(key_frame, text="生成密钥", command=self._generate_key, width=12)
        self._generate_key_btn.grid(row=0, column=1, padx=2)

        # 测试按钮
        ttk.Button(key_frame, text="测试", command=self._test_connection, width=6).grid(row=0, column=2, padx=2)

        # 端口转发配置（多端口映射）
        self._port_mapping_frame = PortMappingFrame(parent, on_change=self._on_mapping_change)
        self._port_mapping_frame.grid(row=2, column=0, columnspan=2, sticky="ew", pady=5)

    def _create_security_frame(self, parent) -> None:
        """创建安全配置页"""
        parent.columnconfigure(1, weight=1)

        # 密钥配置
        key_group = ttk.LabelFrame(parent, text="密钥配置", padding=8)
        key_group.grid(row=0, column=0, columnspan=2, sticky="ew", pady=5)
        key_group.columnconfigure(1, weight=1)

        ttk.Label(key_group, text="私钥路径:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self._key_path_var = tk.StringVar()
        ttk.Entry(key_group, textvariable=self._key_path_var).grid(row=0, column=1, sticky="ew", pady=2)

        ttk.Label(key_group, text="已知主机文件:").grid(row=1, column=0, sticky=tk.W, pady=2)
        self._known_hosts_var = tk.StringVar()
        ttk.Entry(key_group, textvariable=self._known_hosts_var).grid(row=1, column=1, sticky="ew", pady=2)

        # 连接选项
        conn_group = ttk.LabelFrame(parent, text="连接选项", padding=8)
        conn_group.grid(row=1, column=0, columnspan=2, sticky="ew", pady=5)
        conn_group.columnconfigure(1, weight=1)

        ttk.Label(conn_group, text="主机密钥校验:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self._strict_host_key_var = tk.StringVar()
        strict_combo = ttk.Combobox(conn_group, textvariable=self._strict_host_key_var, width=15, state="readonly")
        strict_combo["values"] = ("accept-new", "yes", "no")
        strict_combo.grid(row=0, column=1, sticky=tk.W, pady=2)

        ttk.Label(conn_group, text="连接超时(秒):").grid(row=1, column=0, sticky=tk.W, pady=2)
        self._connect_timeout_var = tk.StringVar()
        ttk.Entry(conn_group, textvariable=self._connect_timeout_var, width=10).grid(row=1, column=1, sticky=tk.W, pady=2)

        ttk.Label(conn_group, text="保活间隔(秒):").grid(row=2, column=0, sticky=tk.W, pady=2)
        self._alive_interval_var = tk.StringVar()
        ttk.Entry(conn_group, textvariable=self._alive_interval_var, width=10).grid(row=2, column=1, sticky=tk.W, pady=2)

        self._compression_var = tk.BooleanVar()
        ttk.Checkbutton(conn_group, text="启用压缩", variable=self._compression_var).grid(row=3, column=0, columnspan=2, pady=5)

    def _create_browser_frame(self, parent) -> None:
        """创建浏览器配置页"""
        parent.columnconfigure(0, weight=1)

        self._auto_open_var = tk.BooleanVar()
        ttk.Checkbutton(parent, text="自动打开浏览器", variable=self._auto_open_var).grid(row=0, column=0, sticky=tk.W, pady=5)

        ttk.Label(parent, text="访问地址:").grid(row=1, column=0, sticky=tk.W, pady=(10, 2))
        self._browser_url_var = tk.StringVar()
        ttk.Entry(parent, textvariable=self._browser_url_var).grid(row=2, column=0, sticky="ew", pady=2)

        ttk.Label(parent, text="打开超时(秒):").grid(row=3, column=0, sticky=tk.W, pady=(10, 2))
        self._open_timeout_var = tk.StringVar()
        ttk.Entry(parent, textvariable=self._open_timeout_var, width=10).grid(row=4, column=0, sticky=tk.W)

    def _create_update_frame(self, parent) -> None:
        """创建更新配置页"""
        parent.columnconfigure(0, weight=1)

        # 版本信息组
        version_group = ttk.LabelFrame(parent, text="版本信息", padding=10)
        version_group.grid(row=0, column=0, sticky="ew", pady=5)

        from version import __version__
        ttk.Label(
            version_group,
            text=f"当前版本: {__version__}",
            font=get_font(11),
        ).grid(row=0, column=0, sticky=tk.W, pady=5)

        # 更新设置组
        settings_group = ttk.LabelFrame(parent, text="更新设置", padding=10)
        settings_group.grid(row=1, column=0, sticky="ew", pady=10)

        # 自动检查更新选项
        self._auto_check_update_var = tk.BooleanVar()
        ttk.Checkbutton(
            settings_group,
            text="启动时自动检查更新",
            variable=self._auto_check_update_var,
        ).grid(row=0, column=0, sticky=tk.W, pady=5)

        # 手动检查按钮
        btn_frame = ttk.Frame(parent)
        btn_frame.grid(row=2, column=0, pady=15)

        self._check_update_btn = ttk.Button(
            btn_frame,
            text="立即检查更新",
            command=self._manual_check_update,
            width=15,
        )
        self._check_update_btn.pack(side=tk.LEFT, padx=5)

        # 检查状态标签
        self._update_status_var = tk.StringVar()
        self._update_status_label = ttk.Label(
            parent,
            textvariable=self._update_status_var,
            font=get_font(9),
            foreground="gray",
        )
        self._update_status_label.grid(row=3, column=0, pady=5)

    def _load_config(self) -> None:
        """加载配置"""
        config = self._presenter.load_config()

        self._host_var.set(config.ssh.host)
        self._port_var.set(str(config.ssh.port))
        self._user_var.set(config.ssh.user)

        self._key_path_var.set(config.ssh.key_path)
        self._known_hosts_var.set(config.ssh.known_hosts)
        self._strict_host_key_var.set(config.ssh.strict_host_key_checking)
        self._connect_timeout_var.set(str(config.ssh.connect_timeout))
        self._alive_interval_var.set(str(config.ssh.server_alive_interval))
        self._compression_var.set(config.ssh.compression)

        self._auto_open_var.set(config.browser.auto_open)
        self._browser_url_var.set(config.browser.url)
        self._open_timeout_var.set(str(config.browser.open_timeout))

        # 加载端口映射
        if config.ssh.port_mappings:
            self._port_mapping_frame.set_mappings(config.ssh.port_mappings)

        # 加载更新配置
        self._auto_check_update_var.set(config.update.auto_check)

        # 更新密钥显示
        self._update_key_display()

    def _save_config(self) -> Config:
        """保存配置到对象（不写入文件）"""
        config = self._presenter.load_config()

        config.ssh.host = self._host_var.get().strip()
        config.ssh.port = int(self._port_var.get() or 22)
        config.ssh.user = self._user_var.get().strip()
        config.ssh.key_path = self._key_path_var.get().strip()
        config.ssh.known_hosts = self._known_hosts_var.get().strip()
        config.ssh.strict_host_key_checking = self._strict_host_key_var.get()
        config.ssh.connect_timeout = int(self._connect_timeout_var.get() or 10)
        config.ssh.server_alive_interval = int(self._alive_interval_var.get() or 30)
        config.ssh.compression = self._compression_var.get()

        # 保存多端口映射
        config.ssh.port_mappings = self._port_mapping_frame.get_mappings()

        config.browser.auto_open = self._auto_open_var.get()
        config.browser.url = self._browser_url_var.get().strip()
        config.browser.open_timeout = int(self._open_timeout_var.get() or 10)

        # 保存更新配置
        config.update.auto_check = self._auto_check_update_var.get()

        return config

    def _on_save_click(self) -> None:
        """保存按钮点击"""
        config = self._save_config()
        if self._presenter.save_config(config):
            if self._on_save:
                self._on_save()
            self.destroy()
        else:
            messagebox.showerror("错误", "保存配置失败", parent=self)

    def _restore_backup(self) -> None:
        """恢复备份配置"""
        if not self._presenter.has_backup():
            messagebox.showwarning("提示", "没有可恢复的备份文件", parent=self)
            return

        result = messagebox.askyesno(
            "确认恢复",
            "确定要恢复备份配置吗？\n当前未保存的修改将丢失。",
            parent=self,
        )
        if result:
            if self._presenter.restore_backup():
                self._load_config()
                messagebox.showinfo("成功", "已恢复备份配置", parent=self)
            else:
                messagebox.showerror("错误", "恢复备份失败", parent=self)

    def _manual_check_update(self) -> None:
        """手动检查更新"""
        self._check_update_btn.config(state="disabled")
        self._update_status_var.set("正在检查更新...")

        def on_result(result):
            # 使用 after 确保在主线程中执行 UI 更新
            self.after(0, lambda: self._handle_update_result(result))

        # 直接调用服务层，传入回调
        self._presenter.update_service.check_for_update_async(on_result, force=True)

    def _handle_update_result(self, result) -> None:
        """处理更新检查结果（在主线程中执行）"""
        self._check_update_btn.config(state="normal")

        if result.error:
            self._update_status_var.set(f"检查失败: {result.error}")
            messagebox.showerror("检查更新", f"检查更新失败:\n{result.error}", parent=self)
        elif result.has_update:
            self._update_status_var.set(f"发现新版本: {result.latest_version}")
            from ui.dialogs.update_dialog import UpdateDialog
            UpdateDialog(self, result)
        else:
            from version import __version__
            self._update_status_var.set("当前已是最新版本")
            messagebox.showinfo("检查更新", f"当前已是最新版本 ({__version__})", parent=self)

    def _update_key_display(self) -> None:
        """更新密钥显示状态"""
        import os
        from utils.path_utils import expand_path

        key_path = expand_path(self._key_path_var.get())
        if os.path.exists(key_path):
            self._key_display_var.set(os.path.basename(key_path))
            self._generate_key_btn.config(text="重新生成")
        else:
            self._key_display_var.set("")
            self._generate_key_btn.config(text="生成密钥")

    def _generate_key(self) -> None:
        """打开生成密钥对话框"""
        # 从窗体获取服务器配置参数
        host = self._host_var.get().strip()
        port_str = self._port_var.get().strip()
        user = self._user_var.get().strip()

        # 非空检查
        if not host:
            messagebox.showerror("错误", "请输入服务器地址", parent=self)
            return
        if not port_str:
            messagebox.showerror("错误", "请输入SSH端口", parent=self)
            return
        if not user:
            messagebox.showerror("错误", "请输入用户名", parent=self)
            return

        dialog = tk.Toplevel(self)
        dialog.title("生成SSH密钥")
        dialog.transient(self)
        dialog.grab_set()
        dialog.resizable(False, False)
        set_window_icon(dialog)

        config = self._presenter.load_config()

        frame = ttk.Frame(dialog, padding=15)
        frame.pack(fill=tk.BOTH, expand=True)
        frame.columnconfigure(1, weight=1)

        # 服务器信息（使用窗体传入的值）
        ttk.Label(frame, text="服务器地址:").grid(row=0, column=0, sticky=tk.W, pady=5)
        host_var = tk.StringVar(value=host)
        host_entry = ttk.Entry(frame, textvariable=host_var, width=25)
        host_entry.grid(row=0, column=1, pady=5, padx=(5, 0))

        ttk.Label(frame, text="端口:").grid(row=1, column=0, sticky=tk.W, pady=5)
        port_var = tk.StringVar(value=port_str)
        port_entry = ttk.Entry(frame, textvariable=port_var, width=10)
        port_entry.grid(row=1, column=1, sticky=tk.W, pady=5, padx=(5, 0))

        ttk.Label(frame, text="用户名:").grid(row=2, column=0, sticky=tk.W, pady=5)
        user_var = tk.StringVar(value=user)
        user_entry = ttk.Entry(frame, textvariable=user_var, width=25)
        user_entry.grid(row=2, column=1, pady=5, padx=(5, 0))

        ttk.Label(frame, text="密码:").grid(row=3, column=0, sticky=tk.W, pady=5)
        password_var = tk.StringVar()
        password_entry = ttk.Entry(frame, textvariable=password_var, show="*", width=25)
        password_entry.grid(row=3, column=1, pady=5, padx=(5, 0))

        # 密钥类型
        ttk.Label(frame, text="密钥类型:").grid(row=4, column=0, sticky=tk.W, pady=5)
        key_type_var = tk.StringVar(value=config.keygen.key_type)
        key_type_combo = ttk.Combobox(frame, textvariable=key_type_var, width=15, state="readonly")
        key_type_combo["values"] = ("ed25519", "rsa")
        key_type_combo.grid(row=4, column=1, sticky=tk.W, pady=5, padx=(5, 0))

        # 密钥注释
        ttk.Label(frame, text="密钥注释:").grid(row=5, column=0, sticky=tk.W, pady=5)
        key_comment_var = tk.StringVar(value=config.keygen.comment)
        key_comment_entry = ttk.Entry(frame, textvariable=key_comment_var, width=25)
        key_comment_entry.grid(row=5, column=1, pady=5, padx=(5, 0))

        # 状态标签
        status_var = tk.StringVar(value="")
        status_label = ttk.Label(frame, textvariable=status_var, foreground="blue")
        status_label.grid(row=6, column=0, columnspan=2, pady=10)

        # 按钮框架
        btn_frame = ttk.Frame(frame)
        btn_frame.grid(row=7, column=0, columnspan=2, pady=(15, 0))
        ok_btn = ttk.Button(btn_frame, text="确定", width=10)
        ok_btn.pack(side=tk.LEFT, padx=5)
        cancel_btn = ttk.Button(btn_frame, text="取消", width=10)
        cancel_btn.pack(side=tk.LEFT, padx=5)

        def set_ui_enabled(enabled: bool):
            state = tk.NORMAL if enabled else tk.DISABLED
            host_entry.config(state=state)
            port_entry.config(state=state)
            user_entry.config(state=state)
            password_entry.config(state=state)
            key_type_combo.config(state=state)
            key_comment_entry.config(state=state)
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
            host_val = host_var.get().strip()
            port_str_val = port_var.get().strip()
            user_val = user_var.get().strip()
            password_val = password_var.get()

            if not host_val:
                messagebox.showerror("错误", "请输入服务器地址", parent=dialog)
                return
            if not port_str_val.isdigit():
                messagebox.showerror("错误", "端口必须是数字", parent=dialog)
                return
            if not user_val:
                messagebox.showerror("错误", "请输入用户名", parent=dialog)
                return
            if not password_val:
                messagebox.showerror("错误", "请输入密码", parent=dialog)
                return

            port_val = int(port_str_val)
            set_ui_enabled(False)

            def run():
                try:
                    from services.key_service import KeyManager

                    # 创建密钥管理器
                    key_manager = KeyManager(
                        key_path=config.ssh.key_path,
                        key_type=key_type_var.get(),
                        comment=key_comment_var.get().strip(),
                    )

                    # 检查密钥是否存在
                    if key_manager.key_exists():
                        update_status("密钥已存在，等待确认...")
                        # 需要在主线程显示确认对话框
                        if not dialog.winfo_exists():
                            return

                        def check_and_proceed():
                            if not messagebox.askyesno("确认", "密钥已存在，是否覆盖？", parent=dialog):
                                set_ui_enabled(True)
                                status_var.set("")
                                return
                            # 备份并删除旧密钥，然后生成新密钥
                            backup_and_generate(key_manager, host_val, port_val, user_val, password_val)

                        dialog.after(0, check_and_proceed)
                        return

                    # 直接生成
                    proceed_generate(key_manager, host_val, port_val, user_val, password_val)

                except Exception as e:
                    show_error(f"初始化失败: {str(e)}")

            def backup_and_generate(key_manager, host_val, port_val, user_val, password_val):
                """备份旧密钥后生成新密钥"""
                def do_backup_and_generate():
                    try:
                        # 1. 备份旧密钥
                        update_status("正在备份旧密钥...")
                        backup_success, backup_msg = key_manager.backup_key()
                        if not backup_success:
                            show_error(f"备份失败: {backup_msg}")
                            return

                        update_status(f"已备份: {backup_msg}")

                        # 2. 删除旧密钥
                        update_status("正在删除旧密钥...")
                        delete_success, delete_msg = key_manager.delete_key()
                        if not delete_success:
                            show_error(f"删除失败: {delete_msg}")
                            return

                        # 3. 生成新密钥
                        proceed_generate(key_manager, host_val, port_val, user_val, password_val)

                    except Exception as e:
                        show_error(f"备份并生成失败: {str(e)}")

                threading.Thread(target=do_backup_and_generate, daemon=True).start()

            def proceed_generate(key_manager, host_val, port_val, user_val, password_val):
                def do_work():
                    try:
                        update_status("正在生成密钥...")
                        result = key_manager.generate_and_deploy(
                            host=host_val,
                            port=port_val,
                            user=user_val,
                            password=password_val,
                            overwrite=True,
                            progress_callback=update_status,
                        )

                        if not dialog.winfo_exists():
                            return

                        if result.success:
                            # 测试密钥连接
                            update_status("正在测试密钥连接...")
                            test_success, test_msg = key_manager.test_key_connection(host_val, port_val, user_val)

                            if not dialog.winfo_exists():
                                return

                            if test_success:
                                # 成功：保存配置并关闭
                                dialog.after(0, lambda: on_success(host_val, port_val, user_val))
                            else:
                                show_error(f"密钥连接测试失败: {test_msg}")
                        else:
                            error_msg = result.message
                            if result.error_detail:
                                error_msg += f"\n{result.error_detail}"
                            show_error(error_msg)

                    except Exception as e:
                        if dialog.winfo_exists():
                            show_error(f"操作失败: {str(e)}")

                threading.Thread(target=do_work, daemon=True).start()

            def on_success(host_val, port_val, user_val):
                # 保存配置
                config.ssh.host = host_val
                config.ssh.port = port_val
                config.ssh.user = user_val
                # 保存密钥类型和注释配置
                config.keygen.key_type = key_type_var.get()
                config.keygen.comment = key_comment_var.get().strip()
                self._presenter.save_config(config)
                self._load_config()
                self._update_key_display()

                messagebox.showinfo("成功", "密钥生成并部署成功", parent=dialog)
                dialog.destroy()

            threading.Thread(target=run, daemon=True).start()

        def on_cancel():
            dialog.destroy()

        ok_btn.config(command=on_ok)
        cancel_btn.config(command=on_cancel)
        dialog.bind("<Return>", on_ok)
        dialog.bind("<Escape>", lambda _e: on_cancel())

        # 居中
        dialog.update_idletasks()
        x = self.winfo_x() + (self.winfo_width() - dialog.winfo_width()) // 2
        y = self.winfo_y() + (self.winfo_height() - dialog.winfo_height()) // 2
        dialog.geometry(f"+{x}+{y}")

        password_entry.focus_set()
        dialog.wait_window()

    def _test_connection(self) -> None:
        """测试连接"""
        self._save_config()
        config = self._presenter.load_config()

        def on_result(success: bool, message: str):
            if success:
                messagebox.showinfo("成功", message, parent=self)
            else:
                messagebox.showerror("失败", message, parent=self)

        self._presenter.test_connection_async(
            host=config.ssh.host,
            port=config.ssh.port,
            user=config.ssh.user,
            key_path=config.ssh.key_path,
            callback=on_result,
        )

    def _on_mapping_change(self) -> None:
        """端口映射变更回调"""
        pass
