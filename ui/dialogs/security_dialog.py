"""
密钥管理弹窗
"""

import os
import tkinter as tk
from tkinter import ttk, messagebox
from typing import TYPE_CHECKING, Optional, Callable

from ui.base import set_window_icon
from models.server_config import MultiServerConfig

if TYPE_CHECKING:
    from app.container import ServiceContainer


class SecurityDialog(tk.Toplevel):
    """密钥管理弹窗"""

    def __init__(self, parent, container: "ServiceContainer", on_save: Optional[Callable] = None):
        super().__init__(parent)
        self.title("密钥管理")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        self._container = container
        self._on_save = on_save
        self._result = False

        # 加载配置
        self._config = self._load_config()

        set_window_icon(self)
        self._create_widgets()
        self._load_config_to_ui()
        self._center_window()

    def _load_config(self) -> MultiServerConfig:
        """加载配置"""
        from repositories.json_config_repository import JsonConfigRepository

        config_dir = os.path.join(os.path.expanduser("~"), ".openclaw-proxy")
        json_repo = JsonConfigRepository(config_dir)
        return json_repo.load_multi()

    def _center_window(self):
        """窗口居中"""
        self.update_idletasks()
        x = self.master.winfo_x() + (self.master.winfo_width() - 550) // 2
        y = self.master.winfo_y() + (self.master.winfo_height() - 360) // 2
        self.geometry(f"550x360+{x}+{y}")

    def _create_widgets(self):
        """创建组件"""
        main_frame = ttk.Frame(self, padding=15)
        main_frame.pack(fill=tk.BOTH, expand=True)
        main_frame.columnconfigure(1, weight=1)

        # 密钥类型
        ttk.Label(main_frame, text="密钥类型:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self._key_type_var = tk.StringVar(value="ed25519")
        key_type_combo = ttk.Combobox(main_frame, textvariable=self._key_type_var, state="readonly", width=12)
        key_type_combo["values"] = ("ed25519", "rsa")
        key_type_combo.grid(row=0, column=1, sticky=tk.W, pady=5)

        # 密钥路径
        ttk.Label(main_frame, text="密钥路径:").grid(row=2, column=0, sticky=tk.W, pady=5)
        self._key_path_var = tk.StringVar()
        key_path_entry = ttk.Entry(main_frame, textvariable=self._key_path_var)
        key_path_entry.grid(row=2, column=1, sticky="ew", pady=5)
        key_path_entry.bind("<FocusOut>", self._on_key_path_change)

        # 已知主机文件
        ttk.Label(main_frame, text="已知主机文件:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self._known_hosts_var = tk.StringVar()
        ttk.Entry(main_frame, textvariable=self._known_hosts_var).grid(row=1, column=1, sticky="ew", pady=5)

        # 公钥/私钥显示区域
        notebook = ttk.Notebook(main_frame)
        notebook.grid(row=3, column=0, columnspan=2, sticky="ew", pady=5)

        # 公钥标签页
        pub_frame = ttk.Frame(notebook, padding=5)
        notebook.add(pub_frame, text="公钥")
        self._pub_key_text = tk.Text(pub_frame, height=5, width=60, wrap=tk.CHAR)
        self._pub_key_text.pack(fill=tk.BOTH, expand=True)

        # 私钥标签页
        priv_frame = ttk.Frame(notebook, padding=5)
        notebook.add(priv_frame, text="私钥")
        self._priv_key_text = tk.Text(priv_frame, height=5, width=60, wrap=tk.CHAR)
        self._priv_key_text.pack(fill=tk.BOTH, expand=True)

        # 确定取消按钮
        btn_frame = ttk.Frame(main_frame)
        btn_frame.grid(row=4, column=0, columnspan=2, pady=15)
        self._generate_btn = ttk.Button(btn_frame, text="生成密钥", command=self._generate_key, width=12)
        self._generate_btn.pack(side=tk.LEFT)
        ttk.Button(btn_frame, text="保存", command=self._on_ok, width=10).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="取消", command=self._on_cancel, width=10).pack(side=tk.LEFT, padx=5)

    def _load_config_to_ui(self):
        """加载配置到界面"""
        # 加载全局密钥配置
        self._key_type_var.set(self._config.global_config.keygen.key_type)

        # 只有配置中存在密钥路径时才设置，否则保持为空
        if self._config.global_config.keygen.key_path:
            self._key_path_var.set(self._config.global_config.keygen.key_path)
        else:
            self._key_path_var.set("")

        if self._config.global_config.keygen.known_hosts:
            self._known_hosts_var.set(self._config.global_config.keygen.known_hosts)
        else:
            # 默认 known_hosts 路径
            ssh_dir = os.path.join(os.path.expanduser("~"), ".ssh")
            self._known_hosts_var.set(os.path.join(ssh_dir, "known_hosts"))

        # 加载密钥内容到文本框
        self._load_key_content()
        # 更新生成按钮文字
        self._update_generate_button_text()

    def _load_key_content(self):
        """加载密钥内容到文本框"""
        key_path = self._key_path_var.get().strip()

        # 清空文本框
        self._pub_key_text.delete("1.0", tk.END)
        self._priv_key_text.delete("1.0", tk.END)

        if not key_path:
            return

        # 加载私钥
        if os.path.exists(key_path):
            try:
                with open(key_path, "r", encoding="utf-8") as f:
                    self._priv_key_text.insert("1.0", f.read())
            except Exception as e:
                self._priv_key_text.insert("1.0", f"无法读取私钥: {e}")

        # 加载公钥
        pub_key_path = key_path + ".pub"
        if os.path.exists(pub_key_path):
            try:
                with open(pub_key_path, "r", encoding="utf-8") as f:
                    self._pub_key_text.insert("1.0", f.read())
            except Exception as e:
                self._pub_key_text.insert("1.0", f"无法读取公钥: {e}")

    def _update_generate_button_text(self):
        """根据密钥文件状态更新按钮文字"""
        key_path = self._key_path_var.get().strip()

        # 检查密钥文件是否存在且有内容
        if key_path and os.path.exists(key_path):
            try:
                with open(key_path, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                if content:
                    self._generate_btn.config(text="重置密钥")
                else:
                    self._generate_btn.config(text="生成密钥")
            except Exception:
                self._generate_btn.config(text="生成密钥")
        else:
            self._generate_btn.config(text="生成密钥")

    def _on_key_path_change(self, _event=None):
        """密钥路径变更时尝试加载密钥内容"""
        key_path = self._key_path_var.get().strip()

        # 更新按钮文字
        self._update_generate_button_text()

        if not key_path:
            return

        # 检查密钥文件是否存在
        if not os.path.exists(key_path):
            messagebox.showwarning("提示", f"密钥文件不存在:\n{key_path}", parent=self)
            return

        # 尝试加载密钥内容
        try:
            self._load_key_content()
        except Exception as e:
            messagebox.showwarning("提示", f"读取密钥失败:\n{str(e)}", parent=self)

    def _generate_key(self):
        """生成密钥"""
        key_path = self._key_path_var.get().strip()
        key_type = self._key_type_var.get()

        # 如果密钥路径为空，使用默认路径
        if not key_path:
            ssh_dir = os.path.join(os.path.expanduser("~"), ".ssh")
            key_path = os.path.join(ssh_dir, f"openclaw_proxy_{key_type}")
            self._key_path_var.set(key_path)

        # 检查是否已存在
        if os.path.exists(key_path):
            if not messagebox.askyesno("确认", f"检查到密钥已存在:\n{key_path}\n\n 是否重新生成？"):
                # 用户选择不重新生成，刷新密钥内容显示
                self._load_key_content()
                self._update_generate_button_text()
                return

        try:
            # 调用密钥服务生成密钥
            success, message = self._container.key_service.generate_key(
                key_path=key_path,
                key_type=key_type,
                comment="openclaw-proxy",
                overwrite=True,
            )

            if success:
                # 保存密钥路径到全局配置
                self._config.global_config.keygen.key_path = key_path
                self._config.global_config.keygen.key_type = key_type
                self._save_config()

                # 刷新密钥路径和内容显示
                self._key_path_var.set(key_path)
                self._load_key_content()
                self._update_generate_button_text()

                messagebox.showinfo("成功", f"生成成功!请在服务器SSH配置中部署公钥。")
            else:
                messagebox.showerror("失败", f"{message}")

        except Exception as e:
            messagebox.showerror("错误", f"生成密钥时发生错误:\n{str(e)}")

    def _save_config(self):
        """保存配置"""
        from repositories.json_config_repository import JsonConfigRepository

        config_dir = os.path.join(os.path.expanduser("~"), ".openclaw-proxy")
        json_repo = JsonConfigRepository(config_dir)
        json_repo.save(self._config)

    def _on_ok(self):
        """确定"""
        # 更新全局配置
        self._config.global_config.keygen.key_type = self._key_type_var.get()
        self._config.global_config.keygen.key_path = self._key_path_var.get().strip()
        self._config.global_config.keygen.known_hosts = self._known_hosts_var.get().strip()

        self._save_config()

        self._result = True
        if self._on_save:
            self._on_save()
        self.destroy()

    def _on_cancel(self):
        """取消"""
        self.destroy()

    def get_result(self) -> bool:
        """获取结果"""
        return self._result
