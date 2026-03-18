"""
UI基类和工具函数
"""

import os
import tkinter as tk
from tkinter import ttk
from typing import Optional, Tuple, TYPE_CHECKING

from PIL import Image, ImageTk

if TYPE_CHECKING:
    pass

# 默认字体
DEFAULT_FONT_FAMILY = "Microsoft YaHei UI"

# 资源路径
_RESOURCES_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "resources")
_ICON_PATH = os.path.join(_RESOURCES_DIR, "images", "favicon.ico")
_LOGO_PATH = os.path.join(_RESOURCES_DIR, "images", "openclaw.png")


def get_font(size: int = 10, bold: bool = False) -> Tuple[str, int, str]:
    """
    获取字体

    Args:
        size: 基础字体大小
        bold: 是否加粗

    Returns:
        字体元组 (family, size, weight)
    """
    weight = "bold" if bold else "normal"
    return (DEFAULT_FONT_FAMILY, size, weight)


def center_window(window: tk.Tk | tk.Toplevel, width: int, height: int) -> None:
    """
    窗口居中

    Args:
        window: 窗口对象
        width: 窗口宽度
        height: 窗口高度
    """
    window.update_idletasks()
    screen_width = window.winfo_screenwidth()
    screen_height = window.winfo_screenheight()
    x = (screen_width - width) // 2
    y = (screen_height - height) // 2
    window.geometry(f"{width}x{height}+{x}+{y}")


def center_on_parent(dialog: tk.Toplevel) -> None:
    """
    对话框在父窗口居中

    Args:
        dialog: 对话框对象
    """
    dialog.update_idletasks()
    parent = dialog.master
    x = parent.winfo_x() + (parent.winfo_width() - dialog.winfo_width()) // 2
    y = parent.winfo_y() + (parent.winfo_height() - dialog.winfo_height()) // 2
    dialog.geometry(f"+{x}+{y}")


def set_window_icon(window: tk.Tk | tk.Toplevel) -> None:
    """
    设置窗口图标

    Args:
        window: 窗口对象
    """
    if os.path.exists(_ICON_PATH):
        window.iconbitmap(_ICON_PATH)


def load_image(
    path: str,
    size: Optional[Tuple[int, int]] = None,
) -> Optional[ImageTk.PhotoImage]:
    """
    加载图片

    Args:
        path: 图片路径
        size: 可选的目标尺寸 (width, height)

    Returns:
        PhotoImage对象，失败返回None
    """
    try:
        if not os.path.exists(path):
            return None

        img = Image.open(path)

        if size:
            img = img.resize(size, Image.Resampling.LANCZOS)

        return ImageTk.PhotoImage(img)

    except Exception:
        return None


def load_logo(size: int = 128) -> Optional[ImageTk.PhotoImage]:
    """
    加载Logo图片

    Args:
        size: 目标尺寸（正方形）

    Returns:
        PhotoImage对象，失败返回None
    """
    return load_image(_LOGO_PATH, (size, size))


class BaseWindow:
    """
    窗口基类

    提供：
    1. DPI感知
    2. 窗口图标
    3. 窗口居中
    4. 统一的字体管理
    """

    def __init__(self, title: str = "OpenClaw代理"):
        """
        初始化窗口

        Args:
            title: 窗口标题
        """
        # 启用DPI感知（必须在创建窗口前）
        from utils.dpi_utils import enable_high_dpi, setup_tk_dpi

        enable_high_dpi()

        self.root = tk.Tk()
        self.root.title(title)

        # 设置窗口图标
        set_window_icon(self.root)

        # 设置Tk DPI缩放
        setup_tk_dpi(self.root)

        # 保存引用防止垃圾回收
        self._images: list = []

    def _center_window(self, width: int, height: int) -> None:
        """窗口居中"""
        center_window(self.root, width, height)

    def _load_logo(self, size: int = 128) -> Optional[ImageTk.PhotoImage]:
        """加载Logo"""
        img = load_logo(size)
        if img:
            self._images.append(img)
        return img

    def run(self) -> None:
        """运行窗口"""
        self.root.mainloop()


class BaseDialog(tk.Toplevel):
    """
    对话框基类

    提供：
    1. 模态对话框
    2. 窗口图标
    3. 在父窗口居中
    """

    def __init__(self, parent, title: str, modal: bool = True):
        """
        初始化对话框

        Args:
            parent: 父窗口
            title: 对话框标题
            modal: 是否模态
        """
        super().__init__(parent)
        self.title(title)
        self.transient(parent)

        if modal:
            self.grab_set()

        self.resizable(False, False)

        # 设置窗口图标
        set_window_icon(self)

        # 保存引用防止垃圾回收
        self._images: list = []

    def _center_on_parent(self) -> None:
        """在父窗口居中"""
        center_on_parent(self)

    def _load_image(
        self, path: str, size: Optional[Tuple[int, int]] = None
    ) -> Optional[ImageTk.PhotoImage]:
        """加载图片"""
        img = load_image(path, size)
        if img:
            self._images.append(img)
        return img


class StyledFrame(ttk.Frame):
    """带统一样式的Frame"""

    def __init__(self, parent, padding: int = 10, **kwargs):
        super().__init__(parent, padding=padding, **kwargs)


class StyledLabel(ttk.Label):
    """带统一样式的Label"""

    def __init__(self, parent, text: str, bold: bool = False, **kwargs):
        font = get_font(10, bold=bold)
        super().__init__(parent, text=text, font=font, **kwargs)


class StyledButton(ttk.Button):
    """带统一样式的Button"""

    def __init__(self, parent, text: str, width: int = 12, **kwargs):
        super().__init__(parent, text=text, width=width, **kwargs)


class StyledEntry(ttk.Entry):
    """带统一样式的Entry"""

    def __init__(self, parent, width: int = 20, **kwargs):
        super().__init__(parent, width=width, **kwargs)
