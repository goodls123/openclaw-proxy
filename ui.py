import os
import sys
import logging
import threading
import webbrowser
from typing import Optional, Callable

import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk

from config_manager import ConfigManager, PortMapping
from key_manager import KeyManager
from ssh_tunnel import SSHTunnel
from utils import (
    can_connect,
    check_ssh_available,
    expand_path,
    enable_high_dpi,
    setup_tk_dpi,
    get_scaled_font_size,
    get_dpi_info,
)
from updater import check_for_update, check_for_update_force, UpdateCheckResult, GITHUB_RELEASES_URL
from version import __version__

logger = logging.getLogger("openclaw_proxy")

# 默认字体
DEFAULT_FONT_FAMILY = "Microsoft YaHei UI"

# 窗口图标路径
_ICON_PATH = os.path.join(os.path.dirname(__file__), "assets", "images", "favicon.ico")
_OPENCLAW_LOGO_PATH = os.path.join(os.path.dirname(__file__), "assets", "images", "openclaw.png")


def _load_logo_image(size: int = 512) -> Optional[ImageTk.PhotoImage]:
    """加载并调整Logo图片大小"""
    try:
        if os.path.exists(_OPENCLAW_LOGO_PATH):
            img = Image.open(_OPENCLAW_LOGO_PATH)
            img = img.resize((size, size), Image.Resampling.LANCZOS)
            return ImageTk.PhotoImage(img)
    except Exception as e:
        logger.warning(f"加载Logo图片失败: {e}")
    return None


def _set_window_icon(window):
    """设置窗口图标"""
    if os.path.exists(_ICON_PATH):
        window.iconbitmap(_ICON_PATH)


def create_tk_root(title: str = "龙虾代理") -> tk.Tk:
    """
    创建支持高分屏的Tkinter根窗口

    Args:
        title: 窗口标题

    Returns:
        配置好的Tk根窗口
    """
    # 启用DPI感知（必须在创建窗口前）
    success, message = enable_high_dpi()
    logger.info(f"DPI感知: {message}")

    # 创建根窗口
    root = tk.Tk()
    root.title(title)

    # 设置窗口图标
    _set_window_icon(root)

    # 设置Tk DPI缩放
    success, message = setup_tk_dpi(root)
    logger.info(f"Tk DPI: {message}")

    # 记录DPI信息
    dpi_info = get_dpi_info()
    logger.debug(f"DPI信息: {dpi_info}")

    return root


def get_font(size: int = 10, bold: bool = False) -> tuple:
    """获取适合当前DPI的字体"""
    scaled_size = get_scaled_font_size(size)
    weight = "bold" if bold else "normal"
    return (DEFAULT_FONT_FAMILY, scaled_size, weight)


class PortMappingFrame(ttk.LabelFrame):
    """端口映射列表管理组件"""

    def __init__(self, parent, on_change: Optional[Callable] = None):
        super().__init__(parent, text="端口映射", padding=8)
        self.on_change = on_change
        self.mapping_rows: list[dict] = []  # 存储每行的控件和变量
        self._create_widgets()

    def _create_widgets(self):
        """创建组件"""
        # 表头：远程地址 | 远程端口 | 本地端口 | 操作
        header_frame = ttk.Frame(self)
        header_frame.pack(fill=tk.X, pady=(0, 5))

        headers = ["远程地址", "远程端口", "本地端口", "操作"]
        widths = [14, 10, 10, 6]
        for col, (header, width) in enumerate(zip(headers, widths)):
            ttk.Label(header_frame, text=header, font=get_font(9, bold=True), width=width).grid(
                row=0, column=col, padx=2
            )
        # "+" 按钮用于快速添加映射
        ttk.Button(header_frame, text="+", width=3, command=self._add_mapping).grid(row=0, column=len(headers), padx=2)

        # 映射列表区域（带滚动条）
        list_frame = ttk.Frame(self)
        list_frame.pack(fill=tk.BOTH, expand=True)

        # 使用 Canvas 和 Frame 实现滚动
        self.canvas = tk.Canvas(list_frame, highlightthickness=0, height=120)
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.canvas.yview)
        self.scroll_frame = ttk.Frame(self.canvas)

        self.canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.canvas_window = self.canvas.create_window((0, 0), window=self.scroll_frame, anchor="nw")
        self.scroll_frame.bind("<Configure>", self._on_frame_configure)
        self.canvas.bind("<Configure>", self._on_canvas_configure)

        # 按钮区域
        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill=tk.X, pady=(8, 0))

        ttk.Button(btn_frame, text="添加映射", command=self._add_mapping, width=10).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="添加常用", command=self._show_presets, width=10).pack(side=tk.LEFT, padx=2)

    def _on_frame_configure(self, event=None):
        """更新滚动区域"""
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _on_canvas_configure(self, event):
        """调整内部框架宽度"""
        self.canvas.itemconfig(self.canvas_window, width=event.width)

    def _add_mapping(self, mapping: Optional[PortMapping] = None):
        """添加一行映射配置"""
        if mapping is None:
            mapping = PortMapping()

        row_index = len(self.mapping_rows)

        # 创建变量（本地地址固定为 127.0.0.1）
        local_port_var = tk.StringVar(value=str(mapping.local_port))
        remote_host_var = tk.StringVar(value=mapping.remote_host)
        remote_port_var = tk.StringVar(value=str(mapping.remote_port))

        vars_dict = {
            "local_host": tk.StringVar(value="127.0.0.1"),  # 固定本地地址
            "local_port": local_port_var,
            "remote_host": remote_host_var,
            "remote_port": remote_port_var,
            "row_index": row_index,
            "row_frame": None,  # 稍后设置
        }
        self.mapping_rows.append(vars_dict)

        # 创建控件：远程地址 | 远程端口 | 本地端口 | 操作
        row_frame = ttk.Frame(self.scroll_frame)
        row_frame.grid(row=row_index, column=0, sticky="ew", pady=2)
        vars_dict["row_frame"] = row_frame

        ttk.Entry(row_frame, textvariable=remote_host_var, width=14).grid(row=0, column=0, padx=2)
        ttk.Entry(row_frame, textvariable=remote_port_var, width=10).grid(row=0, column=1, padx=2)
        ttk.Entry(row_frame, textvariable=local_port_var, width=10).grid(row=0, column=2, padx=2)

        # 删除按钮
        ttk.Button(row_frame, text="删除", width=5,
                   command=lambda: self._remove_mapping(vars_dict)).grid(row=0, column=3, padx=2)

        # 更新滚动区域
        self._on_frame_configure()

        if self.on_change:
            self.on_change()

    def _remove_mapping(self, vars_dict: dict):
        """删除一行映射"""
        # 找到对应的 row_frame 并销毁
        for widget in self.scroll_frame.winfo_children():
            if widget.grid_info().get("row") == vars_dict["row_index"]:
                widget.destroy()
                break

        self.mapping_rows.remove(vars_dict)
        self._refresh_row_indices()

        if self.on_change:
            self.on_change()

    def _refresh_row_indices(self):
        """刷新行索引"""
        for i, vars_dict in enumerate(self.mapping_rows):
            vars_dict["row_index"] = i

    def _show_presets(self):
        """显示常用端口映射预设"""
        presets = [
            ("HTTP (80)", PortMapping("127.0.0.1", 80, "127.0.0.1", 80)),
            ("HTTPS (443)", PortMapping("127.0.0.1", 443, "127.0.0.1", 443)),
            ("MySQL (3306)", PortMapping("127.0.0.1", 3306, "127.0.0.1", 3306)),
            ("PostgreSQL (5432)", PortMapping("127.0.0.1", 5432, "127.0.0.1", 5432)),
            ("Redis (6379)", PortMapping("127.0.0.1", 6379, "127.0.0.1", 6379)),
            ("MongoDB (27017)", PortMapping("127.0.0.1", 27017, "127.0.0.1", 27017)),
        ]

        # 创建预设选择对话框
        dialog = tk.Toplevel(self)
        dialog.title("选择预设")
        dialog.transient(self.winfo_toplevel())
        dialog.grab_set()
        dialog.resizable(False, False)
        _set_window_icon(dialog)

        frame = ttk.Frame(dialog, padding=15)
        frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frame, text="选择要添加的预设映射:", font=get_font(10, bold=True)).grid(
            row=0, column=0, columnspan=2, pady=(0, 10)
        )

        for i, (name, mapping) in enumerate(presets):
            ttk.Button(
                frame, text=name, width=20,
                command=lambda m=mapping, d=dialog: self._add_preset(m, d)
            ).grid(row=i + 1, column=0, columnspan=2, pady=2)

        ttk.Button(frame, text="取消", width=20, command=dialog.destroy).grid(
            row=len(presets) + 1, column=0, columnspan=2, pady=(10, 0)
        )

    def _add_preset(self, mapping: PortMapping, dialog: tk.Toplevel):
        """添加预设映射"""
        self._add_mapping(mapping)
        dialog.destroy()

    def get_mappings(self) -> list[PortMapping]:
        """获取所有端口映射"""
        mappings = []
        for vars_dict in self.mapping_rows:
            try:
                local_port = int(vars_dict["local_port"].get() or 0)
                remote_port = int(vars_dict["remote_port"].get() or 0)
                if local_port > 0 and remote_port > 0:
                    mapping = PortMapping(
                        local_bind_host="127.0.0.1",  # 固定本地地址
                        local_port=local_port,
                        remote_host=vars_dict["remote_host"].get().strip() or "127.0.0.1",
                        remote_port=remote_port,
                    )
                    mappings.append(mapping)
            except ValueError:
                pass  # 忽略无效的端口
        return mappings

    def set_mappings(self, mappings: list[PortMapping]):
        """设置端口映射列表"""
        # 清空现有行
        for widget in self.scroll_frame.winfo_children():
            widget.destroy()
        self.mapping_rows.clear()

        # 添加新映射
        for mapping in mappings:
            self._add_mapping(mapping)

    def clear(self):
        """清空所有映射"""
        for widget in self.scroll_frame.winfo_children():
            widget.destroy()
        self.mapping_rows.clear()


class ConfigWindow(tk.Toplevel):
    """配置窗口"""

    def __init__(self, parent, config_manager: ConfigManager, on_save: Optional[Callable] = None):
        super().__init__(parent)
        self.config_manager = config_manager
        self.on_save = on_save

        self.title("OpenClaw代理配置")
        self.resizable(True, True)
        self.transient(parent)
        _set_window_icon(self)

        self._create_widgets()
        self._load_config()

        # 设置最小尺寸和居中（与主窗口一致）
        self.minsize(600, 500)
        self._center_window(600, 500)

    def _center_window(self, width: int, height: int):
        self.update_idletasks()
        x = self.master.winfo_x() + (self.master.winfo_width() - width) // 2
        y = self.master.winfo_y() + (self.master.winfo_height() - height) // 2
        self.geometry(f"{width}x{height}+{x}+{y}")

    def _create_widgets(self):
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
        ttk.Button(btn_frame, text="保存并关闭", command=self._on_save, width=12).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="恢复备份", command=self._restore_backup, width=12).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="取消", command=self.destroy, width=12).pack(side=tk.LEFT, padx=5)

    def _create_ssh_frame(self, parent):
        parent.columnconfigure(1, weight=1)

        # 服务器配置
        server_group = ttk.LabelFrame(parent, text="服务器配置", padding=8)
        server_group.grid(row=0, column=0, columnspan=2, sticky="ew", pady=5)
        server_group.columnconfigure(1, weight=1)

        ttk.Label(server_group, text="服务器地址:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.host_var = tk.StringVar()
        ttk.Entry(server_group, textvariable=self.host_var).grid(row=0, column=1, sticky="ew", pady=2)

        ttk.Label(server_group, text="SSH端口:").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.port_var = tk.StringVar()
        ttk.Entry(server_group, textvariable=self.port_var, width=10).grid(row=1, column=1, sticky=tk.W, pady=2)

        ttk.Label(server_group, text="用户名:").grid(row=2, column=0, sticky=tk.W, pady=2)
        self.user_var = tk.StringVar()
        ttk.Entry(server_group, textvariable=self.user_var).grid(row=2, column=1, sticky="ew", pady=2)

        # 密钥配置行
        ttk.Label(server_group, text="密钥:").grid(row=3, column=0, sticky=tk.W, pady=2)

        key_frame = ttk.Frame(server_group)
        key_frame.grid(row=3, column=1, sticky="ew", pady=2)
        key_frame.columnconfigure(0, weight=1)

        # 密钥路径输入框（只读）
        self.key_display_var = tk.StringVar()
        key_entry = ttk.Entry(key_frame, textvariable=self.key_display_var, state="readonly")
        key_entry.grid(row=0, column=0, sticky="ew", padx=(0, 5))

        # 生成/重新生成按钮
        self.generate_key_btn = ttk.Button(key_frame, text="生成密钥", command=self._generate_key, width=12)
        self.generate_key_btn.grid(row=0, column=1, padx=2)

        # 测试按钮
        ttk.Button(key_frame, text="测试", command=self._test_connection, width=6).grid(row=0, column=2, padx=2)

        # 端口转发配置（多端口映射）
        self.port_mapping_frame = PortMappingFrame(parent, on_change=self._on_mapping_change)
        self.port_mapping_frame.grid(row=2, column=0, columnspan=2, sticky="ew", pady=5)

    def _create_security_frame(self, parent):
        parent.columnconfigure(1, weight=1)

        # 密钥配置
        key_group = ttk.LabelFrame(parent, text="密钥配置", padding=8)
        key_group.grid(row=0, column=0, columnspan=2, sticky="ew", pady=5)
        key_group.columnconfigure(1, weight=1)

        ttk.Label(key_group, text="私钥路径:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.key_path_var = tk.StringVar()
        ttk.Entry(key_group, textvariable=self.key_path_var).grid(row=0, column=1, sticky="ew", pady=2)

        ttk.Label(key_group, text="已知主机文件:").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.known_hosts_var = tk.StringVar()
        ttk.Entry(key_group, textvariable=self.known_hosts_var).grid(row=1, column=1, sticky="ew", pady=2)

        # 连接选项
        conn_group = ttk.LabelFrame(parent, text="连接选项", padding=8)
        conn_group.grid(row=1, column=0, columnspan=2, sticky="ew", pady=5)
        conn_group.columnconfigure(1, weight=1)

        ttk.Label(conn_group, text="主机密钥校验:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.strict_host_key_var = tk.StringVar()
        strict_combo = ttk.Combobox(conn_group, textvariable=self.strict_host_key_var, width=15, state="readonly")
        strict_combo["values"] = ("accept-new", "yes", "no")
        strict_combo.grid(row=0, column=1, sticky=tk.W, pady=2)

        ttk.Label(conn_group, text="连接超时(秒):").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.connect_timeout_var = tk.StringVar()
        ttk.Entry(conn_group, textvariable=self.connect_timeout_var, width=10).grid(row=1, column=1, sticky=tk.W, pady=2)

        ttk.Label(conn_group, text="保活间隔(秒):").grid(row=2, column=0, sticky=tk.W, pady=2)
        self.alive_interval_var = tk.StringVar()
        ttk.Entry(conn_group, textvariable=self.alive_interval_var, width=10).grid(row=2, column=1, sticky=tk.W, pady=2)

        self.compression_var = tk.BooleanVar()
        ttk.Checkbutton(conn_group, text="启用压缩", variable=self.compression_var).grid(row=3, column=0, columnspan=2, pady=5)

    def _create_browser_frame(self, parent):
        parent.columnconfigure(0, weight=1)

        self.auto_open_var = tk.BooleanVar()
        ttk.Checkbutton(parent, text="自动打开浏览器", variable=self.auto_open_var).grid(row=0, column=0, sticky=tk.W, pady=5)

        ttk.Label(parent, text="访问地址:").grid(row=1, column=0, sticky=tk.W, pady=(10, 2))
        self.browser_url_var = tk.StringVar()
        ttk.Entry(parent, textvariable=self.browser_url_var).grid(row=2, column=0, sticky="ew", pady=2)

        ttk.Label(parent, text="打开超时(秒):").grid(row=3, column=0, sticky=tk.W, pady=(10, 2))
        self.open_timeout_var = tk.StringVar()
        ttk.Entry(parent, textvariable=self.open_timeout_var, width=10).grid(row=4, column=0, sticky=tk.W)

    def _create_update_frame(self, parent):
        """创建更新配置页"""
        parent.columnconfigure(0, weight=1)

        # 版本信息组
        version_group = ttk.LabelFrame(parent, text="版本信息", padding=10)
        version_group.grid(row=0, column=0, sticky="ew", pady=5)

        ttk.Label(
            version_group,
            text=f"当前版本: {__version__}",
            font=get_font(11)
        ).grid(row=0, column=0, sticky=tk.W, pady=5)

        # 更新设置组
        settings_group = ttk.LabelFrame(parent, text="更新设置", padding=10)
        settings_group.grid(row=1, column=0, sticky="ew", pady=10)

        # 自动检查更新选项
        self.auto_check_update_var = tk.BooleanVar()
        ttk.Checkbutton(
            settings_group,
            text="启动时自动检查更新",
            variable=self.auto_check_update_var
        ).grid(row=0, column=0, sticky=tk.W, pady=5)

        # 手动检查按钮
        btn_frame = ttk.Frame(parent)
        btn_frame.grid(row=2, column=0, pady=15)

        self.check_update_btn = ttk.Button(
            btn_frame,
            text="立即检查更新",
            command=self._manual_check_update,
            width=15
        )
        self.check_update_btn.pack(side=tk.LEFT, padx=5)

        # 检查状态标签（初始为空）
        self.update_status_var = tk.StringVar()
        self.update_status_label = ttk.Label(
            parent,
            textvariable=self.update_status_var,
            font=get_font(9),
            foreground="gray"
        )
        self.update_status_label.grid(row=3, column=0, pady=5)

    def _load_config(self):
        config = self.config_manager.config

        self.host_var.set(config.ssh.host)
        self.port_var.set(str(config.ssh.port))
        self.user_var.set(config.ssh.user)

        self.key_path_var.set(config.ssh.key_path)
        self.known_hosts_var.set(config.ssh.known_hosts)
        self.strict_host_key_var.set(config.ssh.strict_host_key_checking)
        self.connect_timeout_var.set(str(config.ssh.connect_timeout))
        self.alive_interval_var.set(str(config.ssh.server_alive_interval))
        self.compression_var.set(config.ssh.compression)

        self.auto_open_var.set(config.browser.auto_open)
        self.browser_url_var.set(config.browser.url)
        self.open_timeout_var.set(str(config.browser.open_timeout))

        # 加载端口映射
        if config.ssh.port_mappings:
            self.port_mapping_frame.set_mappings(config.ssh.port_mappings)

        # 加载更新配置
        self.auto_check_update_var.set(config.update.auto_check)

        # 更新密钥显示
        self._update_key_display()


    def _on_mapping_change(self):
        """端口映射变更时的回调"""
        pass

    def _save_config(self):
        config = self.config_manager.config

        config.ssh.host = self.host_var.get().strip()
        config.ssh.port = int(self.port_var.get() or 22)
        config.ssh.user = self.user_var.get().strip()
        config.ssh.key_path = self.key_path_var.get().strip()
        config.ssh.known_hosts = self.known_hosts_var.get().strip()
        config.ssh.strict_host_key_checking = self.strict_host_key_var.get()
        config.ssh.connect_timeout = int(self.connect_timeout_var.get() or 10)
        config.ssh.server_alive_interval = int(self.alive_interval_var.get() or 30)
        config.ssh.compression = self.compression_var.get()

        # 保存多端口映射
        config.ssh.port_mappings = self.port_mapping_frame.get_mappings()

        config.browser.auto_open = self.auto_open_var.get()
        config.browser.url = self.browser_url_var.get().strip()
        config.browser.open_timeout = int(self.open_timeout_var.get() or 10)

        # 保存更新配置
        config.update.auto_check = self.auto_check_update_var.get()

    def _on_save(self):
        self._save_config()
        if self.config_manager.save():
            if self.on_save:
                self.on_save()
            self.destroy()
        else:
            messagebox.showerror("错误", "保存配置失败", parent=self)

    def _restore_backup(self):
        """恢复备份配置"""
        if not self.config_manager.has_backup():
            messagebox.showwarning("提示", "没有可恢复的备份文件", parent=self)
            return

        result = messagebox.askyesno(
            "确认恢复",
            "确定要恢复备份配置吗？\n当前未保存的修改将丢失。",
            parent=self,
        )
        if result:
            if self.config_manager.restore_backup():
                self._load_config()
                messagebox.showinfo("成功", "已恢复备份配置", parent=self)
            else:
                messagebox.showerror("错误", "恢复备份失败", parent=self)

    def _manual_check_update(self):
        """手动检查更新"""
        self.check_update_btn.config(state="disabled")
        self.update_status_var.set("正在检查更新...")

        def do_check():
            try:
                config_dir = os.path.dirname(self.config_manager.config_file)
                # 使用强制检查，忽略24小时间隔
                result = check_for_update_force(config_dir)
                self.after(0, lambda: self._on_update_check_complete(result))
            except Exception as e:
                logger.debug(f"更新检查异常: {e}")
                self.after(0, lambda: self._on_update_check_error(str(e)))

        threading.Thread(target=do_check, daemon=True).start()

    def _on_update_check_complete(self, result: UpdateCheckResult):
        """更新检查完成回调"""
        self.check_update_btn.config(state="normal")

        if result.error:
            self.update_status_var.set(f"检查失败: {result.error}")
            messagebox.showerror(
                "检查更新",
                f"检查更新失败:\n{result.error}",
                parent=self
            )
        elif result.has_update:
            self.update_status_var.set(f"发现新版本: {result.latest_version}")
            # 显示更新对话框
            UpdateDialog(self, result)
        else:
            self.update_status_var.set("当前已是最新版本")
            messagebox.showinfo(
                "检查更新",
                f"当前已是最新版本 ({__version__})",
                parent=self
            )

    def _on_update_check_error(self, error: str):
        """更新检查错误回调"""
        self.check_update_btn.config(state="normal")
        self.update_status_var.set(f"检查失败: {error}")
        messagebox.showerror(
            "检查更新",
            f"检查更新失败:\n{error}",
            parent=self
        )

    def _update_key_display(self):
        """更新密钥显示状态（仅显示文件名）"""
        key_path = expand_path(self.key_path_var.get())
        if os.path.exists(key_path):
            # 仅显示文件名
            self.key_display_var.set(os.path.basename(key_path))
            self.generate_key_btn.config(text="重新生成")
        else:
            self.key_display_var.set("")
            self.generate_key_btn.config(text="生成密钥")

    def _generate_key(self):
        """打开生成密钥对话框"""
        # 从窗体获取服务器配置参数
        host = self.host_var.get().strip()
        port_str = self.port_var.get().strip()
        user = self.user_var.get().strip()

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
        _set_window_icon(dialog)

        config = self.config_manager.config

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
            dialog.after(0, lambda: (
                status_var.set(f"✗ {msg}"),
                status_label.config(foreground="red"),
                messagebox.showerror("失败", msg, parent=dialog),
                set_ui_enabled(True),
                dialog.after(100, lambda: status_label.config(foreground="blue"))
            ))

        def on_ok(_event=None):
            host = host_var.get().strip()
            port_str = port_var.get().strip()
            user = user_var.get().strip()
            password = password_var.get()

            if not host:
                messagebox.showerror("错误", "请输入服务器地址", parent=dialog)
                return
            if not port_str.isdigit():
                messagebox.showerror("错误", "端口必须是数字", parent=dialog)
                return
            if not user:
                messagebox.showerror("错误", "请输入用户名", parent=dialog)
                return
            if not password:
                messagebox.showerror("错误", "请输入密码", parent=dialog)
                return

            port = int(port_str)
            set_ui_enabled(False)

            def run():
                try:
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
                            backup_and_generate(key_manager, host, port, user, password)

                        dialog.after(0, check_and_proceed)
                        return

                    # 直接生成
                    proceed_generate(key_manager, host, port, user, password)

                except Exception as e:
                    show_error(f"初始化失败: {str(e)}")

            def backup_and_generate(key_manager, host, port, user, password):
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
                        proceed_generate(key_manager, host, port, user, password)

                    except Exception as e:
                        show_error(f"备份并生成失败: {str(e)}")

                threading.Thread(target=do_backup_and_generate, daemon=True).start()

            def proceed_generate(key_manager, host, port, user, password):
                def do_work():
                    try:
                        update_status("正在生成密钥...")
                        result = key_manager.generate_and_deploy(
                            host=host,
                            port=port,
                            user=user,
                            password=password,
                            overwrite=True,
                            progress_callback=update_status,
                        )

                        if not dialog.winfo_exists():
                            return

                        if result.success:
                            # 测试密钥连接
                            update_status("正在测试密钥连接...")
                            test_success, test_msg = key_manager.test_key_connection(host, port, user)

                            if not dialog.winfo_exists():
                                return

                            if test_success:
                                # 成功：保存配置并关闭
                                dialog.after(0, lambda: on_success(host, port, user))
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

            def on_success(host, port, user):
                # 保存配置
                config.ssh.host = host
                config.ssh.port = port
                config.ssh.user = user
                # 保存密钥类型和注释配置
                config.keygen.key_type = key_type_var.get()
                config.keygen.comment = key_comment_var.get().strip()
                self.config_manager.save()
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

    def _test_connection(self):
        self._save_config()
        key_manager = KeyManager(key_path=self.config_manager.config.ssh.key_path)

        def do_test():
            success, message = key_manager.test_key_connection(
                host=self.config_manager.config.ssh.host,
                port=self.config_manager.config.ssh.port,
                user=self.config_manager.config.ssh.user,
            )
            self.after(0, lambda: self._on_test_complete(success, message))

        threading.Thread(target=do_test, daemon=True).start()

    def _on_test_complete(self, success: bool, message: str):
        if success:
            messagebox.showinfo("成功", message, parent=self)
        else:
            messagebox.showerror("失败", message, parent=self)


class StatusWindow:
    """代理运行状态窗口"""

    def __init__(self, config_manager: ConfigManager, tunnel: SSHTunnel):
        self.config_manager = config_manager
        self.tunnel = tunnel
        self.token: str = ""  # 缓存token

        # 创建支持高分屏的根窗口
        self.root = create_tk_root("OpenClaw代理 - 运行中")
        self.root.resizable(True, True)
        self.root.minsize(800, 430)

        self._create_widgets()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        # 居中显示
        self._center_window(800, 430)

        # 自动获取token
        logger.info(f"[Token] auto_fetch_token配置: {config_manager.config.browser.auto_fetch_token}")
        if config_manager.config.browser.auto_fetch_token:
            logger.info("[Token] 开始调用_fetch_token_async")
            self._fetch_token_async()
        else:
            logger.info("[Token] auto_fetch_token已禁用，跳过自动获取")

    def _center_window(self, width: int, height: int):
        self.root.update_idletasks()
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = (screen_width - width) // 2
        y = (screen_height - height) // 2
        self.root.geometry(f"{width}x{height}+{x}+{y}")

    def _create_widgets(self):
        main_frame = ttk.Frame(self.root, padding=15)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 标题（Logo + 文字水平布局）
        header_frame = ttk.Frame(main_frame)
        header_frame.pack(pady=(0, 8))

        # Logo图片
        self.logo_image = _load_logo_image(128)
        if self.logo_image:
            logo_label = ttk.Label(header_frame, image=self.logo_image)
            logo_label.pack(side=tk.LEFT, padx=(0, 10))
        ttk.Label(header_frame, text="虾代理", font=get_font(14, bold=True)).pack(side=tk.LEFT, padx=(10, 0))

        # 状态
        status_frame = ttk.LabelFrame(main_frame, text="状态", padding=8)
        status_frame.pack(fill=tk.X, pady=5)

        self.status_var = tk.StringVar(value="✓ 代理运行中")
        ttk.Label(status_frame, textvariable=self.status_var, font=get_font(11), foreground="green").pack()

        # 连接信息
        self.info_var = tk.StringVar()
        self._update_info_text()
        info_frame = ttk.LabelFrame(main_frame, text="连接信息", padding=8)
        info_frame.pack(fill=tk.X, pady=5)
        ttk.Label(info_frame, textvariable=self.info_var, justify=tk.LEFT).pack(anchor=tk.W)

        # 按钮
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(pady=12)

        self.browser_btn = ttk.Button(btn_frame, text="打开浏览器", command=self._open_browser, width=14)
        self.browser_btn.pack(side=tk.LEFT, padx=5)
        self.stop_btn = ttk.Button(btn_frame, text="停止代理", command=self._stop_tunnel, width=14)
        self.stop_btn.pack(side=tk.LEFT, padx=5)
        self.start_btn = ttk.Button(btn_frame, text="重新代理", command=self._restart_tunnel, width=14, state=tk.DISABLED)
        self.start_btn.pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="查看配置", command=self._open_config, width=14).pack(side=tk.LEFT, padx=5)

    def _update_info_text(self):
        """更新连接信息文本"""
        config = self.config_manager.config
        info_text = f"本地地址: http://{config.ssh.local_bind_host}:{config.ssh.local_port}\n"
        info_text += f"服务器: {config.ssh.user}@{config.ssh.host}:{config.ssh.port}"
        self.info_var.set(info_text)

    def _fetch_token_async(self):
        """异步获取远程token"""
        def fetch():
            from ssh_tunnel import fetch_remote_config, extract_gateway_token
            config = self.config_manager.config

            logger.info(f"[Token] 开始异步获取token...")
            logger.debug(f"[Token] 远程配置路径: {config.browser.remote_config_path}")

            try:
                success, remote_config, error_msg = fetch_remote_config(
                    host=config.ssh.host,
                    port=config.ssh.port,
                    user=config.ssh.user,
                    key_path=config.ssh.key_path,
                    remote_config_path=config.browser.remote_config_path,
                )

                if not success:
                    logger.warning(f"[Token] 获取远程配置失败: {error_msg}")
                    return

                logger.debug(f"[Token] 远程配置内容长度: {len(remote_config) if remote_config else 0}")

                token_success, token, token_error = extract_gateway_token(remote_config)
                if token_success:
                    self.token = token
                    # 缓存token到配置并保存到配置文件
                    config.browser.token = token
                    self.config_manager.save()
                    logger.info(f"[Token] 成功获取token并保存: {token[:8]}...")
                    self.root.after(0, lambda: self.status_var.set("✓ 代理运行中"))
                else:
                    logger.warning(f"[Token] 提取token失败: {token_error}")
            except Exception as e:
                logger.error(f"[Token] 异步获取token异常: {e}")

        threading.Thread(target=fetch, daemon=True).start()

    def _get_browser_url(self) -> str:
        """获取带token的浏览器URL"""
        config = self.config_manager.config
        base_url = f"http://{config.ssh.local_bind_host}:{config.ssh.local_port}"

        # 优先使用缓存的token
        token = self.token or config.browser.token
        if token:
            return f"{base_url}/#token={token}"
        return base_url

    def _fetch_token_sync(self) -> bool:
        """同步获取token，返回是否成功"""
        from ssh_tunnel import fetch_remote_config, extract_gateway_token
        config = self.config_manager.config

        logger.info(f"[Token] 开始同步获取token...")
        logger.debug(f"[Token] 远程配置路径: {config.browser.remote_config_path}")

        try:
            success, remote_config, error_msg = fetch_remote_config(
                host=config.ssh.host,
                port=config.ssh.port,
                user=config.ssh.user,
                key_path=config.ssh.key_path,
                remote_config_path=config.browser.remote_config_path,
            )

            if not success:
                logger.warning(f"[Token] 获取远程配置失败: {error_msg}")
                return False

            logger.debug(f"[Token] 远程配置内容长度: {len(remote_config) if remote_config else 0}")

            token_success, token, token_error = extract_gateway_token(remote_config)
            if token_success:
                self.token = token
                # 缓存token到配置并保存到配置文件
                config.browser.token = token
                self.config_manager.save()
                logger.info(f"[Token] 成功获取token并保存: {token[:8]}...")
                return True
            else:
                logger.warning(f"[Token] 提取token失败: {token_error}")
                return False
        except Exception as e:
            logger.error(f"[Token] 同步获取token异常: {e}")
            return False

    def _open_browser(self):
        """打开浏览器，如果没有token则先获取"""
        config = self.config_manager.config
        token = self.token or config.browser.token

        if not token:
            # 没有token，先获取
            self.status_var.set("正在获取token...")
            self.root.update()

            def fetch_and_open():
                try:
                    if self._fetch_token_sync():
                        self.root.after(0, self._do_open_browser)
                    else:
                        self.root.after(0, lambda: (
                            self.status_var.set("✗ 获取token失败"),
                            messagebox.showwarning("提示", "无法获取token，请检查远程配置", parent=self.root)
                        ))
                except Exception as e:
                    logger.error(f"获取token失败: {e}")
                    self.root.after(0, lambda: self.status_var.set("✓ 代理运行中"))

            threading.Thread(target=fetch_and_open, daemon=True).start()
        else:
            self._do_open_browser()

    def _do_open_browser(self):
        """实际执行打开浏览器"""
        url = self._get_browser_url()
        logger.info(f"打开浏览器: {url[:50]}...")
        self.status_var.set("✓ 代理运行中")
        webbrowser.open(url)

    def _stop_tunnel(self):
        """停止隧道但不关闭窗口"""
        if self.tunnel:
            self.tunnel.stop()
            self.tunnel = None

        self.status_var.set("○ 代理已停止")
        self.stop_btn.config(state=tk.DISABLED)
        self.start_btn.config(state=tk.NORMAL)
        self.browser_btn.config(state=tk.DISABLED)

    def _restart_tunnel(self):
        """重新启动隧道"""
        from ssh_tunnel import SSHTunnel
        config = self.config_manager.config

        self.status_var.set("正在重新连接...")
        self.start_btn.config(state=tk.DISABLED)
        self.root.update()

        self.tunnel = SSHTunnel(
            host=config.ssh.host,
            port=config.ssh.port,
            user=config.ssh.user,
            key_path=config.ssh.key_path,
            known_hosts=config.ssh.known_hosts,
            strict_host_key_checking=config.ssh.strict_host_key_checking,
            connect_timeout=config.ssh.connect_timeout,
            server_alive_interval=config.ssh.server_alive_interval,
            server_alive_count_max=config.ssh.server_alive_count_max,
            compression=config.ssh.compression,
            port_mappings=config.ssh.port_mappings,
        )

        success, error = self.tunnel.check_prerequisites()
        if not success:
            self.status_var.set("✗ 启动失败")
            self.start_btn.config(state=tk.NORMAL)
            messagebox.showerror("错误", error, parent=self.root)
            return

        success, message = self.tunnel.start()
        if not success:
            self.status_var.set("✗ 启动失败")
            self.start_btn.config(state=tk.NORMAL)
            messagebox.showerror("错误", message, parent=self.root)
            return

        success, message = self.tunnel.wait_for_connection(timeout=config.browser.open_timeout)
        if not success:
            self.status_var.set("✗ 连接失败")
            self.start_btn.config(state=tk.NORMAL)
            self.tunnel.stop()
            messagebox.showerror("错误", message, parent=self.root)
            return

        self.status_var.set("✓ 代理运行中")
        self.stop_btn.config(state=tk.NORMAL)
        self.start_btn.config(state=tk.DISABLED)
        self.browser_btn.config(state=tk.NORMAL)

        if config.browser.auto_open:
            self._open_browser()

    def _open_config(self):
        """打开配置窗口"""
        ConfigWindow(self.root, self.config_manager, on_save=self._refresh_status)

    def _refresh_status(self):
        """刷新状态显示（配置保存后调用）"""
        # 重新加载配置
        self.config_manager.load()
        # 更新连接信息显示
        self._update_info_text()
        # 更新状态显示
        self.status_var.set("✓ 配置已更新")

    def _on_close(self):
        if self.tunnel:
            self.tunnel.stop()
        self.root.quit()
        self.root.destroy()

    def run(self):
        self.root.mainloop()


class MainWindow:
    """主窗口（配置界面）"""

    def __init__(self, config_manager: ConfigManager, title: str = "OpenClaw代理配置"):
        self.config_manager = config_manager
        self.tunnel: Optional[SSHTunnel] = None
        self.token: str = ""  # 缓存token

        # 创建支持高分屏的根窗口
        self.root = create_tk_root(title)
        self.root.resizable(True, True)
        self.root.minsize(620, 310)

        self._create_widgets()
        self._check_prerequisites()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        # 居中显示
        self._center_window(800, 460)

        # 启动时后台检查更新
        self._check_update_async()

    def _center_window(self, width: int, height: int):
        self.root.update_idletasks()
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = (screen_width - width) // 2
        y = (screen_height - height) // 2
        self.root.geometry(f"{width}x{height}+{x}+{y}")

    def _create_widgets(self):
        main_frame = ttk.Frame(self.root, padding=15)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 标题（Logo + 文字水平布局）
        header_frame = ttk.Frame(main_frame)
        header_frame.pack(pady=(0, 12))

        self.logo_image = _load_logo_image(128)
        if self.logo_image:
            logo_label = ttk.Label(header_frame, image=self.logo_image)
            logo_label.pack(side=tk.LEFT, padx=(0, 10))
        ttk.Label(header_frame, text="OpenClaw 代理工具", font=get_font(14, bold=True)).pack(side=tk.LEFT, padx=(10, 0))

        # 状态
        status_frame = ttk.LabelFrame(main_frame, text="状态", padding=8)
        status_frame.pack(fill=tk.X, pady=5)

        self.status_var = tk.StringVar(value="未连接")
        ttk.Label(status_frame, textvariable=self.status_var, font=get_font(10)).pack()

        # 连接信息
        config = self.config_manager.config
        info_text = f"服务器: {config.ssh.user}@{config.ssh.host}:{config.ssh.port}\n"
        info_text += f"本地端口: {config.ssh.local_bind_host}:{config.ssh.local_port}\n"
        info_text += f"远程目标: {config.ssh.remote_host}:{config.ssh.remote_port}"

        info_frame = ttk.LabelFrame(main_frame, text="连接信息", padding=8)
        info_frame.pack(fill=tk.X, pady=5)
        ttk.Label(info_frame, text=info_text, justify=tk.LEFT).pack(anchor=tk.W)

        # 按钮
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(pady=12)

        self.browser_btn = ttk.Button(btn_frame, text="打开浏览器", command=self._open_browser, width=12, state=tk.DISABLED)
        self.browser_btn.pack(side=tk.LEFT, padx=5)

        self.start_btn = ttk.Button(btn_frame, text="启动代理", command=self._start_tunnel, width=12)
        self.start_btn.pack(side=tk.LEFT, padx=5)

        self.stop_btn = ttk.Button(btn_frame, text="停止代理", command=self._stop_tunnel, width=12, state=tk.DISABLED)
        self.stop_btn.pack(side=tk.LEFT, padx=5)

        ttk.Button(btn_frame, text="配置设置", command=self._open_config, width=12).pack(side=tk.LEFT, padx=5)

    def _check_prerequisites(self):
        available, error = check_ssh_available()
        if not available:
            messagebox.showerror("错误", error)
            self.root.quit()
            return

        # 异步测试连接
        self._test_connection_async()

    def _test_connection_async(self):
        """异步测试SSH连接"""
        self.status_var.set("正在检测连接...")
        self.start_btn.config(state=tk.DISABLED)

        def do_test():
            config = self.config_manager.config
            key_manager = KeyManager(key_path=config.ssh.key_path)
            success, message = key_manager.test_key_connection(
                host=config.ssh.host,
                port=config.ssh.port,
                user=config.ssh.user,
                timeout=5,
            )
            self.root.after(0, lambda: self._on_connection_test_complete(success, message))

        threading.Thread(target=do_test, daemon=True).start()

    def _on_connection_test_complete(self, success: bool, message: str):
        """连接测试完成回调"""
        if success:
            self.status_var.set("✓ 连接就绪")
            self.start_btn.config(state=tk.NORMAL)
        else:
            self.status_var.set(f"✗ {message}")
            self.start_btn.config(state=tk.DISABLED)
            # 失败时直接打开配置窗口
            self._open_config()

    def _start_tunnel(self):
        config = self.config_manager.config

        self.tunnel = SSHTunnel(
            host=config.ssh.host,
            port=config.ssh.port,
            user=config.ssh.user,
            key_path=config.ssh.key_path,
            known_hosts=config.ssh.known_hosts,
            strict_host_key_checking=config.ssh.strict_host_key_checking,
            connect_timeout=config.ssh.connect_timeout,
            server_alive_interval=config.ssh.server_alive_interval,
            server_alive_count_max=config.ssh.server_alive_count_max,
            compression=config.ssh.compression,
            port_mappings=config.ssh.port_mappings,
        )

        success, error = self.tunnel.check_prerequisites()
        if not success:
            self.status_var.set(f"✗ {error}")
            self._open_config()
            return

        self.status_var.set("正在启动隧道...")
        self.start_btn.config(state=tk.DISABLED)
        self.root.update()

        success, message = self.tunnel.start()
        if not success:
            self.status_var.set("启动失败")
            self.start_btn.config(state=tk.NORMAL)
            messagebox.showerror("错误", message, parent=self.root)
            return

        success, message = self.tunnel.wait_for_connection(timeout=config.browser.open_timeout)
        if not success:
            self.status_var.set("连接失败")
            self.start_btn.config(state=tk.NORMAL)
            self.tunnel.stop()
            messagebox.showerror("错误", message, parent=self.root)
            return

        self.status_var.set("✓ 代理运行中")
        self.start_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        self.browser_btn.config(state=tk.NORMAL)

        # 自动获取token
        if config.browser.auto_fetch_token:
            self._fetch_token_async()

        if config.browser.auto_open:
            self._open_browser()

    def _stop_tunnel(self):
        if self.tunnel:
            self.tunnel.stop()
            self.tunnel = None

        self.status_var.set("未连接")
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        self.browser_btn.config(state=tk.DISABLED)

    def _open_browser(self):
        """打开浏览器，如果没有token则先获取"""
        config = self.config_manager.config
        token = self.token or config.browser.token

        if not token:
            # 没有token，先获取
            self.status_var.set("正在获取token...")
            self.root.update()

            def fetch_and_open():
                try:
                    if self._fetch_token_sync():
                        self.root.after(0, self._do_open_browser)
                    else:
                        self.root.after(0, lambda: (
                            self.status_var.set("✗ 获取token失败"),
                            messagebox.showwarning("提示", "无法获取token，请检查远程配置", parent=self.root)
                        ))
                except Exception as e:
                    logger.error(f"获取token失败: {e}")
                    self.root.after(0, lambda: self.status_var.set("✓ 代理运行中"))

            threading.Thread(target=fetch_and_open, daemon=True).start()
        else:
            self._do_open_browser()

    def _do_open_browser(self):
        """实际执行打开浏览器"""
        url = self._get_browser_url()
        logger.info(f"打开浏览器: {url[:50]}...")
        self.status_var.set("✓ 代理运行中")
        webbrowser.open(url)

    def _get_browser_url(self) -> str:
        """获取带token的浏览器URL"""
        config = self.config_manager.config
        base_url = f"http://{config.ssh.local_bind_host}:{config.ssh.local_port}"

        # 优先使用缓存的token
        token = self.token or config.browser.token
        if token:
            return f"{base_url}/#token={token}"
        return base_url

    def _fetch_token_async(self):
        """异步获取远程token"""
        def fetch():
            from ssh_tunnel import fetch_remote_config, extract_gateway_token
            config = self.config_manager.config

            logger.info(f"[Token] 开始异步获取token...")
            logger.debug(f"[Token] 远程配置路径: {config.browser.remote_config_path}")

            try:
                success, remote_config, error_msg = fetch_remote_config(
                    host=config.ssh.host,
                    port=config.ssh.port,
                    user=config.ssh.user,
                    key_path=config.ssh.key_path,
                    remote_config_path=config.browser.remote_config_path,
                )

                if not success:
                    logger.warning(f"[Token] 获取远程配置失败: {error_msg}")
                    return

                logger.debug(f"[Token] 远程配置内容长度: {len(remote_config) if remote_config else 0}")

                token_success, token, token_error = extract_gateway_token(remote_config)
                if token_success:
                    self.token = token
                    # 缓存token到配置并保存到配置文件
                    config.browser.token = token
                    self.config_manager.save()
                    logger.info(f"[Token] 成功获取token并保存: {token[:8]}...")
                    self.root.after(0, lambda: self.status_var.set("✓ 代理运行中"))
                else:
                    logger.warning(f"[Token] 提取token失败: {token_error}")
            except Exception as e:
                logger.error(f"[Token] 异步获取token异常: {e}")

        threading.Thread(target=fetch, daemon=True).start()

    def _fetch_token_sync(self) -> bool:
        """同步获取token，返回是否成功"""
        from ssh_tunnel import fetch_remote_config, extract_gateway_token
        config = self.config_manager.config

        logger.info(f"[Token] 开始同步获取token...")
        logger.debug(f"[Token] 远程配置路径: {config.browser.remote_config_path}")

        try:
            success, remote_config, error_msg = fetch_remote_config(
                host=config.ssh.host,
                port=config.ssh.port,
                user=config.ssh.user,
                key_path=config.ssh.key_path,
                remote_config_path=config.browser.remote_config_path,
            )

            if not success:
                logger.warning(f"[Token] 获取远程配置失败: {error_msg}")
                return False

            logger.debug(f"[Token] 远程配置内容长度: {len(remote_config) if remote_config else 0}")

            token_success, token, token_error = extract_gateway_token(remote_config)
            if token_success:
                self.token = token
                # 缓存token到配置并保存到配置文件
                config.browser.token = token
                self.config_manager.save()
                logger.info(f"[Token] 成功获取token并保存: {token[:8]}...")
                return True
            else:
                logger.warning(f"[Token] 提取token失败: {token_error}")
                return False
        except Exception as e:
            logger.error(f"[Token] 同步获取token异常: {e}")
            return False

    def _open_config(self):
        """打开配置窗口"""
        ConfigWindow(self.root, self.config_manager, on_save=self._check_prerequisites)

    def _check_update_async(self):
        """异步检查更新"""
        # 检查是否启用自动检查
        if not self.config_manager.config.update.auto_check:
            return

        def do_check():
            try:
                config_dir = os.path.dirname(self.config_manager.config_file)
                result = check_for_update(config_dir)
                if result.has_update:
                    self.root.after(0, lambda: self._show_update_dialog(result))
            except Exception as e:
                logger.debug(f"更新检查异常: {e}")

        threading.Thread(target=do_check, daemon=True).start()

    def _show_update_dialog(self, result: UpdateCheckResult):
        """显示更新对话框"""
        UpdateDialog(self.root, result)

    def _on_close(self):
        if self.tunnel:
            self.tunnel.stop()
        self.root.quit()
        self.root.destroy()

    def run(self):
        self.root.mainloop()


class UpdateDialog(tk.Toplevel):
    """更新提示对话框"""

    def __init__(self, parent, result: UpdateCheckResult):
        super().__init__(parent)
        self.result = result
        self.title("发现新版本")
        self.transient(parent)
        self.grab_set()
        self.resizable(False, False)
        _set_window_icon(self)

        self._create_widgets()
        self._center_window()

    def _center_window(self):
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = self.master.winfo_x() + (self.master.winfo_width() - width) // 2
        y = self.master.winfo_y() + (self.master.winfo_height() - height) // 2
        self.geometry(f"+{x}+{y}")

    def _create_widgets(self):
        main_frame = ttk.Frame(self, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 标题
        title_label = ttk.Label(
            main_frame,
            text="有新版本可用!",
            font=get_font(14, bold=True),
            foreground="green"
        )
        title_label.pack(pady=(0, 15))

        # 版本信息
        version_frame = ttk.Frame(main_frame)
        version_frame.pack(fill=tk.X, pady=5)

        ttk.Label(
            version_frame,
            text=f"当前版本: {self.result.current_version}",
            font=get_font(10)
        ).pack()
        ttk.Label(
            version_frame,
            text=f"最新版本: {self.result.latest_version}",
            font=get_font(11, bold=True),
            foreground="blue"
        ).pack(pady=(5, 0))

        # 更新说明（如果有）
        if self.result.release_info and self.result.release_info.body:
            notes_frame = ttk.LabelFrame(main_frame, text="更新说明", padding=10)
            notes_frame.pack(fill=tk.BOTH, expand=True, pady=(15, 5))

            # 使用Text组件显示多行文本
            notes_text = tk.Text(
                notes_frame,
                width=50,
                height=8,
                wrap=tk.WORD,
                font=get_font(9)
            )
            notes_text.insert(tk.END, self.result.release_info.body[:500])  # 限制长度
            notes_text.config(state=tk.DISABLED)
            notes_text.pack(fill=tk.BOTH, expand=True)

        # 按钮
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(pady=(20, 0))

        ttk.Button(
            btn_frame,
            text="前往下载",
            command=self._go_download,
            width=12
        ).pack(side=tk.LEFT, padx=5)

        ttk.Button(
            btn_frame,
            text="稍后提醒",
            command=self.destroy,
            width=12
        ).pack(side=tk.LEFT, padx=5)

    def _go_download(self):
        """打开下载页面"""
        url = self.result.release_info.url if self.result.release_info else GITHUB_RELEASES_URL
        webbrowser.open(url)
        self.destroy()
