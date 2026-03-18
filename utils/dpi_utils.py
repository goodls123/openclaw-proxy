"""
DPI工具函数
"""

import sys
import ctypes
from typing import Tuple, Dict, Any


# DPI信息缓存
_dpi_info: Dict[str, Any] = {
    "enabled": False,
    "awareness_level": None,
    "system_dpi": 96,
    "scale_factor": 1.0,
}


def enable_high_dpi() -> Tuple[bool, str]:
    """
    启用Windows高分屏DPI感知

    在创建Tkinter窗口前调用此函数。

    Returns:
        (是否成功, 消息)
    """
    global _dpi_info

    if sys.platform != "win32":
        _dpi_info["enabled"] = True
        return True, "非Windows系统，跳过DPI设置"

    messages = []

    # 尝试设置 Per Monitor DPI Aware V2 (Windows 10 1703+)
    try:
        # PROCESS_PER_MONITOR_DPI_AWARE = 2
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
        _dpi_info["awareness_level"] = "PerMonitorV2"
        messages.append("已启用 PerMonitorV2 DPI感知")
    except Exception:
        # 尝试设置 System DPI Aware (Windows 8.1+)
        try:
            # PROCESS_SYSTEM_DPI_AWARE = 1
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
            _dpi_info["awareness_level"] = "System"
            messages.append("已启用 System DPI感知")
        except Exception:
            # 回退到老版本API (Windows Vista/7)
            try:
                ctypes.windll.user32.SetProcessDPIAware()
                _dpi_info["awareness_level"] = "Legacy"
                messages.append("已启用 Legacy DPI感知")
            except Exception as e:
                _dpi_info["awareness_level"] = "None"
                messages.append(f"DPI感知设置失败: {e}")

    _dpi_info["enabled"] = True
    return True, "; ".join(messages)


def setup_tk_dpi(root) -> Tuple[bool, str]:
    """
    设置Tkinter的DPI缩放

    在创建Tkinter窗口后调用此函数。

    Args:
        root: Tkinter根窗口

    Returns:
        (是否成功, 消息)
    """
    global _dpi_info

    if sys.platform != "win32":
        return True, "非Windows系统，跳过Tk DPI设置"

    messages = []

    try:
        # 获取系统DPI
        dpi = root.winfo_fpixels('1i')
        if dpi > 0:
            _dpi_info["system_dpi"] = int(dpi)
            _dpi_info["scale_factor"] = dpi / 96.0

            # 设置Tk缩放比例
            scale = dpi / 72.0  # Tk默认72 DPI
            root.tk.call('tk', 'scaling', scale)
            messages.append(f"DPI: {int(dpi)}, 缩放: {scale:.2f}x")
        else:
            messages.append("无法获取DPI，使用默认值")
    except Exception as e:
        messages.append(f"DPI设置异常: {e}")

    return True, "; ".join(messages)


def get_dpi_scale(root=None) -> Tuple[float, int]:
    """
    获取DPI缩放比例

    Args:
        root: Tkinter根窗口（可选，用于获取实际DPI）

    Returns:
        (缩放比例, DPI值)
    """
    global _dpi_info

    if root is not None:
        try:
            # 获取实际DPI
            dpi = root.winfo_fpixels('1i')
            if dpi > 0:
                _dpi_info["system_dpi"] = int(dpi)
                _dpi_info["scale_factor"] = dpi / 96.0
                return _dpi_info["scale_factor"], _dpi_info["system_dpi"]
        except Exception:
            pass

    # 默认值
    return _dpi_info["scale_factor"], _dpi_info["system_dpi"]


def get_scaled_font_size(base_size: int = 10) -> int:
    """
    获取字体大小

    注意：tk scaling 已经处理了 DPI 缩放，不需要手动缩放字体大小，
    否则会导致双重缩放，字体过大。

    Args:
        base_size: 基础字体大小

    Returns:
        字体大小（不进行额外缩放）
    """
    return base_size


def get_dpi_info() -> Dict[str, Any]:
    """
    获取DPI信息（用于日志记录）

    Returns:
        DPI信息字典
    """
    return _dpi_info.copy()
