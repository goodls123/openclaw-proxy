"""
端口映射组件
可复用的端口映射列表管理组件
"""

import tkinter as tk
from tkinter import ttk
from typing import Optional, Callable, List

from ui.base import get_font
from models import PortMapping


class PortMappingFrame(ttk.LabelFrame):
    """
    端口映射列表管理组件

    功能：
    1. 显示和管理多个端口映射
    2. 添加/删除端口映射
    3. 预设端口映射选择
    """

    def __init__(
        self,
        parent,
        on_change: Optional[Callable] = None,
        title: str = "端口映射",
    ):
        """
        初始化端口映射组件

        Args:
            parent: 父组件
            on_change: 变化回调
            title: 组件标题
        """
        super().__init__(parent, text=title, padding=8)
        self.on_change = on_change
        self.mapping_rows: List[dict] = []  # 存储每行的控件和变量
        self._create_widgets()

    def _create_widgets(self) -> None:
        """创建组件"""
        # 表头：远程地址 | 远程端口 | 本地端口 | OpenClaw | 操作
        header_frame = ttk.Frame(self)
        header_frame.pack(fill=tk.X, pady=(0, 5))

        headers = ["远程地址", "远程端口", "本地端口", "OpenClaw", "操作"]
        widths = [12, 10, 10, 10, 6]
        for col, (header, width) in enumerate(zip(headers, widths)):
            ttk.Label(
                header_frame,
                text=header,
                font=get_font(9, bold=True),
                width=width,
            ).grid(row=0, column=col, padx=2)

        # "+" 按钮用于快速添加映射
        ttk.Button(
            header_frame,
            text="+",
            width=3,
            command=self._add_mapping,
        ).grid(row=0, column=len(headers), padx=2)

        # 映射列表区域（直接使用Frame，滚动由父组件处理）
        self._list_frame = ttk.Frame(self)
        self._list_frame.pack(fill=tk.BOTH, expand=True)

    def _add_mapping(self, mapping: Optional[PortMapping] = None) -> None:
        """
        添加一行映射配置

        Args:
            mapping: 初始映射配置
        """
        if mapping is None:
            mapping = PortMapping()

        row_index = len(self.mapping_rows)

        # 创建变量（本地地址固定为 127.0.0.1）
        local_port_var = tk.StringVar(value=str(mapping.local_port))
        remote_host_var = tk.StringVar(value=mapping.remote_host)
        remote_port_var = tk.StringVar(value=str(mapping.remote_port))
        is_openclaw_var = tk.BooleanVar(value=mapping.is_openclaw)

        vars_dict = {
            "local_host": tk.StringVar(value="127.0.0.1"),  # 固定本地地址
            "local_port": local_port_var,
            "remote_host": remote_host_var,
            "remote_port": remote_port_var,
            "is_openclaw": is_openclaw_var,
            "row_index": row_index,
            "row_frame": None,  # 稍后设置
        }
        self.mapping_rows.append(vars_dict)

        # 创建控件：远程地址 | 远程端口 | 本地端口 | OpenClaw | 操作
        row_frame = ttk.Frame(self._list_frame)
        row_frame.grid(row=row_index, column=0, sticky="ew", pady=2)
        vars_dict["row_frame"] = row_frame

        ttk.Entry(row_frame, textvariable=remote_host_var, width=14).grid(row=0, column=0, padx=2)
        ttk.Entry(row_frame, textvariable=remote_port_var, width=10).grid(row=0, column=1, padx=2)
        ttk.Entry(row_frame, textvariable=local_port_var, width=10).grid(row=0, column=2, padx=2)

        # OpenClaw 复选框
        ttk.Checkbutton(row_frame, variable=is_openclaw_var).grid(row=0, column=3, padx=2)

        # 删除按钮
        ttk.Button(
            row_frame,
            text="删除",
            width=5,
            command=lambda: self._remove_mapping(vars_dict),
        ).grid(row=0, column=4, padx=2)

        if self.on_change:
            self.on_change()

    def _remove_mapping(self, vars_dict: dict) -> None:
        """删除一行映射"""
        # 找到对应的 row_frame 并销毁
        for widget in self._list_frame.winfo_children():
            if widget.grid_info().get("row") == vars_dict["row_index"]:
                widget.destroy()
                break

        self.mapping_rows.remove(vars_dict)
        self._refresh_row_indices()

        if self.on_change:
            self.on_change()

    def _refresh_row_indices(self) -> None:
        """刷新行索引"""
        for i, vars_dict in enumerate(self.mapping_rows):
            vars_dict["row_index"] = i

    def _show_presets(self) -> None:
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

        from ui.base import set_window_icon
        set_window_icon(dialog)

        frame = ttk.Frame(dialog, padding=15)
        frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(
            frame,
            text="选择要添加的预设映射:",
            font=get_font(10, bold=True),
        ).grid(row=0, column=0, columnspan=2, pady=(0, 10))

        for i, (name, mapping) in enumerate(presets):
            ttk.Button(
                frame,
                text=name,
                width=20,
                command=lambda m=mapping, d=dialog: self._add_preset(m, d),
            ).grid(row=i + 1, column=0, columnspan=2, pady=2)

        ttk.Button(
            frame,
            text="取消",
            width=20,
            command=dialog.destroy,
        ).grid(row=len(presets) + 1, column=0, columnspan=2, pady=(10, 0))

    def _add_preset(self, mapping: PortMapping, dialog: tk.Toplevel) -> None:
        """添加预设映射"""
        self._add_mapping(mapping)
        dialog.destroy()

    def get_mappings(self) -> List[PortMapping]:
        """
        获取所有端口映射

        Returns:
            端口映射列表
        """
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
                        is_openclaw=vars_dict["is_openclaw"].get(),
                    )
                    mappings.append(mapping)
            except ValueError:
                pass  # 忽略无效的端口
        return mappings

    def set_mappings(self, mappings: List[PortMapping]) -> None:
        """
        设置端口映射列表

        Args:
            mappings: 端口映射列表
        """
        # 清空现有行
        for widget in self._list_frame.winfo_children():
            widget.destroy()
        self.mapping_rows.clear()

        # 添加新映射
        for mapping in mappings:
            self._add_mapping(mapping)

    def clear(self) -> None:
        """清空所有映射"""
        for widget in self._list_frame.winfo_children():
            widget.destroy()
        self.mapping_rows.clear()
