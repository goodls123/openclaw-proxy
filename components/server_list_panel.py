"""
服务器列表面板组件
"""

import tkinter as tk
from tkinter import ttk
from typing import Callable, Optional

from utils.path_utils import get_resource_path


class ServerItem(tk.Frame):
    """单个服务器项（上下布局：图标+名称）"""

    def __init__(
        self,
        parent,
        server_id: str,
        server_name: str,
        host: str,
        is_connected: bool = False,
        on_toggle: Optional[Callable[[str], None]] = None,
        on_config: Optional[Callable[[str], None]] = None,
        on_open_browser: Optional[Callable[[str], None]] = None,
    ):
        super().__init__(parent, bg="#f5f5f5", cursor="hand2")

        self._server_id = server_id
        self._server_name = server_name
        self._host = host
        self._is_connected = is_connected
        self._on_toggle = on_toggle  # 左键：开启/停止代理
        self._on_config = on_config  # 右键菜单：打开配置
        self._on_open_browser = on_open_browser  # 右键菜单：浏览器打开

        self._menu = None  # 右键菜单
        self._create_widgets()
        self._setup_bindings()

    def _create_widgets(self) -> None:
        """创建组件（上下布局）"""
        # 内部容器
        self._inner_frame = tk.Frame(self, bg="#f5f5f5", padx=10, pady=10)
        self._inner_frame.pack(fill=tk.NONE, expand=True)

        # 加载图标
        self._icon_image = self._load_icon()
        if self._icon_image:
            self._icon_label = tk.Label(self._inner_frame, image=self._icon_image, bg="#f5f5f5")
        else:
            # 如果图片加载失败，使用文字代替
            self._icon_label = tk.Label(self._inner_frame, text="🖥️", font=("Segoe UI Emoji", 24), bg="#f5f5f5")
        self._icon_label.pack(pady=(0, 5))

        # 服务器名称
        self._name_label = tk.Label(
            self._inner_frame,
            text=self._server_name,
            font=("Microsoft YaHei UI", 10, "bold"),
            bg="#f5f5f5",
        )
        self._name_label.pack()

    def _load_icon(self):
        """加载图标（带状态指示器）"""
        try:
            icon_path = get_resource_path("resources/images/pc.png")
            import os
            if os.path.exists(icon_path):
                try:
                    from PIL import Image, ImageTk
                    img = Image.open(icon_path)
                    img = img.resize((128, 128), Image.Resampling.LANCZOS)

                    # 添加状态指示器
                    img = self._add_status_indicator(img)

                    return ImageTk.PhotoImage(img)
                except ImportError:
                    image = tk.PhotoImage(file=icon_path)
                    return image
        except Exception:
            pass
        return None

    def _add_status_indicator(self, base_img):
        """在图标左上角添加状态指示器"""
        try:
            from PIL import Image
            import os

            # 状态图标路径
            status_icon_name = "run.png" if self._is_connected else "stop.png"
            status_path = get_resource_path(f"resources/images/{status_icon_name}")

            if os.path.exists(status_path):
                status_img = Image.open(status_path)
                # 状态图标大小
                status_size = 30
                status_img = status_img.resize((status_size, status_size), Image.Resampling.LANCZOS)

                # 确保基础图片是 RGBA 模式
                if base_img.mode != "RGBA":
                    base_img = base_img.convert("RGBA")

                # 确保状态图标也是 RGBA 模式
                if status_img.mode != "RGBA":
                    status_img = status_img.convert("RGBA")

                # 将状态图标粘贴到基础图片左上角（带偏移）
                offset = 3  # 距离边缘的偏移
                base_img.paste(status_img, (offset, offset), status_img)

            return base_img
        except Exception:
            return base_img

    def _update_status_indicator(self) -> None:
        """更新状态指示器"""
        # 重新加载并合成图标
        self._icon_image = self._load_icon()
        if self._icon_image:
            self._icon_label.config(image=self._icon_image)

    def _setup_bindings(self) -> None:
        """设置事件绑定"""
        widgets = [self, self._inner_frame, self._icon_label, self._name_label]

        for widget in widgets:
            widget.bind("<Button-1>", self._on_left_click_event)
            widget.bind("<Button-3>", self._on_right_click_event)
            widget.bind("<Enter>", self._on_enter)
            widget.bind("<Leave>", self._on_leave)

    def _on_left_click_event(self, event) -> None:
        """左键点击事件 - 开启/停止代理"""
        if self._on_toggle:
            self._on_toggle(self._server_id)

    def _on_right_click_event(self, event) -> None:
        """右键点击事件 - 显示上下文菜单"""
        self._show_context_menu(event.x_root, event.y_root)

    def _show_context_menu(self, x: int, y: int) -> None:
        """显示上下文菜单"""
        # 创建菜单
        self._menu = tk.Menu(self, tearoff=0)
        self._menu.add_command(label="连接配置", command=self._on_menu_config)
        self._menu.add_command(label="浏览器打开", command=self._on_menu_open_browser)

        # 显示菜单
        try:
            self._menu.tk_popup(x, y)
        finally:
            self._menu.grab_release()

    def _on_menu_config(self) -> None:
        """菜单：打开SSH配置"""
        if self._on_config:
            self._on_config(self._server_id)

    def _on_menu_open_browser(self) -> None:
        """菜单：浏览器打开"""
        if self._on_open_browser:
            self._on_open_browser(self._server_id)

    def _on_enter(self, event) -> None:
        """鼠标进入"""
        self.config(bg="#e0e0e0")
        self._inner_frame.config(bg="#e0e0e0")
        self._icon_label.config(bg="#e0e0e0")
        self._name_label.config(bg="#e0e0e0", font=("Microsoft YaHei UI", 11, "bold"))

    def _on_leave(self, event) -> None:
        """鼠标离开"""
        self.config(bg="#f5f5f5")
        self._inner_frame.config(bg="#f5f5f5")
        self._icon_label.config(bg="#f5f5f5")
        # 恢复字体大小，保持粗体
        if self._is_connected:
            self._name_label.config(bg="#f5f5f5", foreground="green", font=("Microsoft YaHei UI", 10, "normal"))
        else:
            self._name_label.config(bg="#f5f5f5", foreground="black", font=("Microsoft YaHei UI", 10, "normal"))

    def set_connected(self, connected: bool) -> None:
        """设置连接状态"""
        self._is_connected = connected
        # 更新状态指示器图标
        self._update_status_indicator()
        # 根据连接状态改变名称样式
        if connected:
            self._name_label.config(foreground="green", font=("Microsoft YaHei UI", 10, "bold"))
        else:
            self._name_label.config(foreground="black", font=("Microsoft YaHei UI", 10, "bold"))

    def get_server_id(self) -> str:
        """获取服务器ID"""
        return self._server_id

    def is_connected(self) -> bool:
        """获取连接状态"""
        return self._is_connected


class AddServerItem(tk.Frame):
    """添加服务器按钮项（上下布局：图标+名称）"""

    def __init__(
        self,
        parent,
        on_click: Optional[Callable[[], None]] = None,
    ):
        super().__init__(parent, bg="#f5f5f5", cursor="hand2")

        self._on_click = on_click

        self._create_widgets()
        self._setup_bindings()

    def _create_widgets(self) -> None:
        """创建组件（上下布局）"""
        # 内部容器
        self._inner_frame = tk.Frame(self, bg="#f5f5f5", padx=10, pady=10)
        self._inner_frame.pack(fill=tk.BOTH, expand=True)

        # 加载图标
        self._icon_image = self._load_icon()
        if self._icon_image:
            self._icon_label = tk.Label(self._inner_frame, image=self._icon_image, bg="#f5f5f5")
        else:
            # 如果图片加载失败，使用文字代替
            self._icon_label = tk.Label(self._inner_frame, text="➕", font=("Segoe UI Emoji", 24), bg="#f5f5f5")
        self._icon_label.pack(pady=(0, 5))

        # 按钮名称
        self._name_label = tk.Label(
            self._inner_frame,
            text="新增连接",
            font=("Microsoft YaHei UI", 10, "normal"),
            bg="#f5f5f5",
        )
        self._name_label.pack()

    def _load_icon(self):
        """加载图标"""
        try:
            icon_path = get_resource_path("resources/images/add.png")
            import os
            if os.path.exists(icon_path):
                try:
                    from PIL import Image, ImageTk
                    img = Image.open(icon_path)
                    img = img.resize((128, 128), Image.Resampling.LANCZOS)

                    return ImageTk.PhotoImage(img)
                except ImportError:
                    image = tk.PhotoImage(file=icon_path)
                    return image
        except Exception:
            pass
        return None

    def _setup_bindings(self) -> None:
        """设置事件绑定"""
        widgets = [self, self._inner_frame, self._icon_label, self._name_label]

        for widget in widgets:
            widget.bind("<Button-1>", self._on_click_event)
            widget.bind("<Enter>", self._on_enter)
            widget.bind("<Leave>", self._on_leave)

    def _on_click_event(self, event) -> None:
        """点击事件"""
        if self._on_click:
            self._on_click()

    def _on_enter(self, event) -> None:
        """鼠标进入"""
        self.config(bg="#e0e0e0")
        self._inner_frame.config(bg="#e0e0e0")
        self._icon_label.config(bg="#e0e0e0")
        self._name_label.config(bg="#e0e0e0", font=("Microsoft YaHei UI", 10, "bold"))

    def _on_leave(self, event) -> None:
        """鼠标离开"""
        self.config(bg="#f5f5f5")
        self._inner_frame.config(bg="#f5f5f5")
        self._icon_label.config(bg="#f5f5f5")
        self._name_label.config(bg="#f5f5f5", font=("Microsoft YaHei UI", 10, "normal"))


class ServerListPanel(ttk.Frame):
    """服务器列表面板"""

    def __init__(
        self,
        parent,
        on_server_toggle: Optional[Callable[[str], None]] = None,
        on_server_config: Optional[Callable[[str], None]] = None,
        on_server_open_browser: Optional[Callable[[str], None]] = None,
        on_add_server: Optional[Callable[[], None]] = None,
    ):
        super().__init__(parent)

        self._on_server_toggle = on_server_toggle  # 左键：开启/停止代理
        self._on_server_config = on_server_config  # 右键菜单：打开配置
        self._on_server_open_browser = on_server_open_browser  # 右键菜单：浏览器打开
        self._on_add_server = on_add_server
        self._server_items: dict[str, ServerItem] = {}
        self._selected_id: Optional[str] = None
        self._add_item: Optional[AddServerItem] = None

        self._create_widgets()

    def _create_widgets(self) -> None:
        """创建组件"""
        # 服务器列表容器（水平滚动）
        list_container = ttk.Frame(self)
        list_container.pack(fill=tk.BOTH, expand=True)

        self._canvas = tk.Canvas(
            list_container,
            highlightthickness=0,
            bg="#f5f5f5",
            height=200,
        )
        self._scrollbar = ttk.Scrollbar(
            list_container,
            orient=tk.HORIZONTAL,
            command=self._canvas.xview,
        )

        self._scrollable_frame = ttk.Frame(self._canvas)
        self._scrollable_frame.bind(
            "<Configure>",
            self._on_frame_configure
        )

        self._canvas.create_window((0, 0), window=self._scrollable_frame, anchor="nw")
        self._canvas.configure(xscrollcommand=self._scrollbar.set)

        # 绑定 canvas 大小变化事件
        self._canvas.bind("<Configure>", self._on_canvas_configure)

        self._canvas.pack(side=tk.TOP, fill=tk.X)
        # 初始不显示滚动条，需要时再显示
        self._scrollbar_visible = False

        # 绑定鼠标滚轮（水平滚动）
        self._canvas.bind_all("<MouseWheel>", self._on_mousewheel)

        # 创建"新增连接"按钮（稍后添加到列表末尾）
        self._add_item = AddServerItem(
            self._scrollable_frame,
            on_click=self._on_add_click,
        )
        self._add_item.pack(side=tk.LEFT, padx=5, pady=5)

    def _on_frame_configure(self, event) -> None:
        """更新滚动区域"""
        self._canvas.configure(scrollregion=self._canvas.bbox("all"))
        self._update_scrollbar_visibility()

    def _on_canvas_configure(self, event) -> None:
        """Canvas 大小变化时检查滚动条可见性"""
        self._update_scrollbar_visibility()

    def _update_scrollbar_visibility(self) -> None:
        """根据内容宽度决定是否显示滚动条"""
        self._canvas.update_idletasks()
        canvas_width = self._canvas.winfo_width()
        frame_width = self._scrollable_frame.winfo_reqwidth()

        if frame_width > canvas_width:
            if not self._scrollbar_visible:
                self._scrollbar.pack(side=tk.BOTTOM, fill=tk.X)
                self._scrollbar_visible = True
        else:
            if self._scrollbar_visible:
                self._scrollbar.pack_forget()
                self._scrollbar_visible = False

    def _on_mousewheel(self, event) -> None:
        """鼠标滚轮事件（水平滚动）"""
        self._canvas.xview_scroll(int(-1 * (event.delta / 120)), "units")

    def _on_add_click(self) -> None:
        """添加按钮点击"""
        if self._on_add_server:
            self._on_add_server()

    def add_server(
        self,
        server_id: str,
        name: str,
        host: str,
        is_connected: bool = False,
    ) -> None:
        """添加服务器"""
        # 先移除添加按钮
        if self._add_item:
            self._add_item.pack_forget()

        item = ServerItem(
            self._scrollable_frame,
            server_id=server_id,
            server_name=name,
            host=host,
            is_connected=is_connected,
            on_toggle=self._on_server_toggle_event,
            on_config=self._on_server_config_event,
            on_open_browser=self._on_server_open_browser_event,
        )
        item.pack(side=tk.LEFT, padx=5, pady=5)
        self._server_items[server_id] = item

        # 重新添加"新增连接"按钮到末尾
        if self._add_item:
            self._add_item.pack(side=tk.LEFT, padx=5, pady=5)

    def remove_server(self, server_id: str) -> None:
        """移除服务器"""
        if server_id in self._server_items:
            self._server_items[server_id].destroy()
            del self._server_items[server_id]

    def clear_servers(self) -> None:
        """清空服务器列表"""
        for item in self._server_items.values():
            item.destroy()
        self._server_items.clear()
        self._selected_id = None

        # 确保"新增连接"按钮仍然显示
        if self._add_item:
            self._add_item.pack(side=tk.LEFT, padx=5, pady=5)

    def set_server_connected(self, server_id: str, connected: bool) -> None:
        """设置服务器连接状态"""
        if server_id in self._server_items:
            self._server_items[server_id].set_connected(connected)

    def is_server_connected(self, server_id: str) -> bool:
        """检查服务器是否已连接"""
        if server_id in self._server_items:
            return self._server_items[server_id].is_connected()
        return False

    def select_server(self, server_id: str) -> None:
        """选中服务器"""
        self._selected_id = server_id

    def get_selected_server(self) -> Optional[str]:
        """获取选中的服务器ID"""
        return self._selected_id

    def _on_server_toggle_event(self, server_id: str) -> None:
        """服务器左键点击 - 开启/停止代理"""
        self.select_server(server_id)
        if self._on_server_toggle:
            self._on_server_toggle(server_id)

    def _on_server_config_event(self, server_id: str) -> None:
        """服务器右键菜单 - 打开配置"""
        if self._on_server_config:
            self._on_server_config(server_id)

    def _on_server_open_browser_event(self, server_id: str) -> None:
        """服务器右键菜单 - 浏览器打开"""
        if self._on_server_open_browser:
            self._on_server_open_browser(server_id)
