"""
添加服务器对话框
"""

import tkinter as tk
from tkinter import ttk, messagebox
from typing import TYPE_CHECKING

from ui.base import set_window_icon

if TYPE_CHECKING:
    from app.container import ServiceContainer


class AddServerDialog(tk.Toplevel):
    """添加服务器弹窗"""

    def __init__(self, parent, container: "ServiceContainer"):
        super().__init__(parent)
        self.title("添加服务器")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        self._container = container
        self._result = False

        set_window_icon(self)
        self._create_widgets()
        self._center_window()

    def _center_window(self):
        """窗口居中"""
        self.update_idletasks()
        x = self.master.winfo_x() + (self.master.winfo_width() - 400) // 2
        y = self.master.winfo_y() + (self.master.winfo_height() - 380) // 2
        self.geometry(f"400x380+{x}+{y}")

    def _create_widgets(self):
        """创建组件"""
        main_frame = ttk.Frame(self, padding=15)
        main_frame.pack(fill=tk.BOTH, expand=True)
        main_frame.columnconfigure(1, weight=1)

        # 基本信息
        ttk.Label(main_frame, text="服务器名称:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self._name_var = tk.StringVar()
        ttk.Entry(main_frame, textvariable=self._name_var, width=30).grid(row=0, column=1, sticky="ew", pady=5)

        # SSH 配置
        ttk.Label(main_frame, text="服务器地址:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self._host_var = tk.StringVar()
        ttk.Entry(main_frame, textvariable=self._host_var, width=30).grid(row=1, column=1, sticky="ew", pady=5)

        ttk.Label(main_frame, text="SSH端口:").grid(row=2, column=0, sticky=tk.W, pady=5)
        self._port_var = tk.StringVar(value="22")
        ttk.Entry(main_frame, textvariable=self._port_var, width=10).grid(row=2, column=1, sticky=tk.W, pady=5)

        ttk.Label(main_frame, text="用户名:").grid(row=3, column=0, sticky=tk.W, pady=5)
        self._user_var = tk.StringVar()
        ttk.Entry(main_frame, textvariable=self._user_var, width=30).grid(row=3, column=1, sticky="ew", pady=5)

        # 端口映射
        ttk.Label(main_frame, text="本地端口:").grid(row=4, column=0, sticky=tk.W, pady=5)
        self._local_port_var = tk.StringVar(value="18789")
        ttk.Entry(main_frame, textvariable=self._local_port_var, width=10).grid(row=4, column=1, sticky=tk.W, pady=5)

        ttk.Label(main_frame, text="远程端口:").grid(row=5, column=0, sticky=tk.W, pady=5)
        self._remote_port_var = tk.StringVar(value="18789")
        ttk.Entry(main_frame, textvariable=self._remote_port_var, width=10).grid(row=5, column=1, sticky=tk.W, pady=5)

        # OpenClaw 标记
        self._is_openclaw_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            main_frame,
            text="OpenClaw 服务",
            variable=self._is_openclaw_var,
        ).grid(row=6, column=0, columnspan=2, sticky=tk.W, pady=5)

        # 自动运行
        self._auto_run_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            main_frame,
            text="应用启动时自动运行",
            variable=self._auto_run_var,
        ).grid(row=7, column=0, columnspan=2, sticky=tk.W, pady=10)

        # 按钮
        btn_frame = ttk.Frame(main_frame)
        btn_frame.grid(row=8, column=0, columnspan=2, pady=15)
        ttk.Button(btn_frame, text="添加", command=self._on_add, width=10).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="取消", command=self._on_cancel, width=10).pack(side=tk.LEFT, padx=5)

    def _on_add(self):
        """添加服务器"""
        name = self._name_var.get().strip()
        host = self._host_var.get().strip()
        port = self._port_var.get().strip()
        user = self._user_var.get().strip()
        local_port = self._local_port_var.get().strip()
        remote_port = self._remote_port_var.get().strip()

        # 验证
        if not name:
            messagebox.showerror("错误", "请输入服务器名称", parent=self)
            return
        if not host:
            messagebox.showerror("错误", "请输入服务器地址", parent=self)
            return
        if not port.isdigit():
            messagebox.showerror("错误", "端口必须是数字", parent=self)
            return
        if not user:
            messagebox.showerror("错误", "请输入用户名", parent=self)
            return
        if not local_port.isdigit():
            messagebox.showerror("错误", "本地端口必须是数字", parent=self)
            return
        if not remote_port.isdigit():
            messagebox.showerror("错误", "远程端口必须是数字", parent=self)
            return

        # 保存到配置
        try:
            from repositories.json_config_repository import JsonConfigRepository
            from models.server_config import ServerConfig, SSHConfig, PortMappingConfig
            import os

            config_dir = os.path.join(os.path.expanduser("~"), ".openclaw-proxy")
            json_repo = JsonConfigRepository(config_dir)
            config = json_repo.load_multi()

            # 创建新服务器
            new_server = ServerConfig(
                name=name,
                enabled=True,
                auto_run=self._auto_run_var.get(),
                ssh=SSHConfig(
                    host=host,
                    port=int(port),
                    user=user,
                ),
                port_mappings=[
                    PortMappingConfig(
                        name="主映射",
                        enabled=True,
                        local_bind_host="127.0.0.1",
                        local_port=int(local_port),
                        remote_host="127.0.0.1",
                        remote_port=int(remote_port),
                        is_openclaw=self._is_openclaw_var.get(),
                    )
                ],
            )

            config.servers.append(new_server)
            json_repo.save(config)

            self._result = True
            self.destroy()

        except Exception as e:
            messagebox.showerror("错误", f"添加服务器失败: {str(e)}", parent=self)

    def _on_cancel(self):
        """取消"""
        self.destroy()

    def get_result(self) -> bool:
        """获取结果"""
        return self._result
