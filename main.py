#!/usr/bin/env python3
"""
OpenClaw代理工具
一键启动SSH端口转发并自动打开浏览器

启动顺序：
1. 初始化日志
2. 启用Windows DPI感知（UI模式时）
3. 加载配置
4. 创建UI/启动代理

架构：使用 ServiceContainer 进行依赖注入，UI层使用 Presenter 模式
"""

import os
import sys
import argparse
import logging
from typing import Optional

from utils import setup_logging, check_ssh_available
from version import __version__

# 全局变量
logger: Optional[logging.Logger] = None
_container = None


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description="OpenClaw代理工具 - 一键启动SSH端口转发",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  openclaw-proxy.exe                    # 自动模式：有配置则启动代理，否则打开配置
  openclaw-proxy.exe --config           # 强制打开配置界面
  openclaw-proxy.exe --host 1.2.3.4     # 指定服务器地址
        """,
    )

    # SSH连接参数
    parser.add_argument("--host", help="SSH服务器地址")
    parser.add_argument("--port", type=int, help="SSH端口")
    parser.add_argument("--user", help="SSH用户名")
    parser.add_argument("--local-bind-host", help="本地绑定地址")
    parser.add_argument("--local-port", type=int, help="本地监听端口")
    parser.add_argument("--remote-host", help="远程目标地址")
    parser.add_argument("--remote-port", type=int, help="远程目标端口")

    # SSH安全参数
    parser.add_argument("--key-path", help="私钥文件路径")
    parser.add_argument("--known-hosts", help="已知主机文件路径")
    parser.add_argument(
        "--strict-host-key-checking",
        choices=["yes", "no", "accept-new"],
        help="主机密钥校验策略",
    )
    parser.add_argument("--connect-timeout", type=int, help="连接超时(秒)")
    parser.add_argument("--server-alive-interval", type=int, help="保活间隔(秒)")
    parser.add_argument("--server-alive-count-max", type=int, help="保活失败次数")
    parser.add_argument("--compression", action="store_true", help="启用压缩")

    # 浏览器参数
    parser.add_argument("--no-browser", action="store_true", help="不自动打开浏览器")
    parser.add_argument("--browser-url", help="浏览器访问地址")

    # 特殊操作
    parser.add_argument("--config", "-c", action="store_true", help="打开配置界面")
    parser.add_argument("--edit-config", action="store_true", help="打开配置文件编辑")

    # 其他参数
    parser.add_argument("--config-file", default="config.json", help="配置文件路径")
    parser.add_argument("--verbose", "-v", action="store_true", help="详细输出")

    return parser.parse_args()


def check_environment() -> tuple[bool, str]:
    """检查运行环境"""
    available, error = check_ssh_available()
    if not available:
        return False, f"{error}\n\n请在Windows设置中启用OpenSSH客户端:\n设置 > 应用 > 可选功能 > 添加功能 > OpenSSH客户端"
    return True, ""


def run_gui_mode(title: str = "OpenClaw连接代理"):
    """运行图形界面模式 """
    from ui.windows import MainWindow

    window = MainWindow(_container, title=title)
    window.run()
    return 0


def run_gui_mode_with_check(title: str = "OpenClaw连接代理"):
    """
    启动GUI模式（带环境检查）
    所有隧道由用户手动启动
    """
    # 检查环境
    success, error = check_environment()
    if not success:
        from tkinter import messagebox
        messagebox.showerror("环境错误", error)
        return 1

    return run_gui_mode(title)


def main():
    """主函数"""
    global logger, _container

    args = parse_args()

    # 确定用户配置目录 ~/.openclaw-proxy/
    user_config_dir = os.path.join(os.path.expanduser("~"), ".openclaw-proxy")
    if not os.path.exists(user_config_dir):
        os.makedirs(user_config_dir)

    # 配置文件和日志目录都放在用户配置目录下
    config_file = os.path.join(user_config_dir, "config.json")
    log_dir = os.path.join(user_config_dir, "logs")

    # 1. 初始化日志（最先）
    log_level = "DEBUG" if args.verbose else "INFO"
    logger = setup_logging(log_level, log_dir)
    logger.info("=" * 50)
    logger.info("OpenClaw代理工具启动")
    logger.info(f"版本: {__version__}")
    logger.info(f"Python版本: {sys.version}")
    logger.info(f"平台: {sys.platform}")
    logger.info(f"配置目录: {user_config_dir}")
    logger.info(f"配置文件: {config_file}")

    # 2. 创建服务容器（新架构）
    from app.container import ServiceContainer
    _container = ServiceContainer.create(user_config_dir)

    # 3. 加载配置并应用命令行参数
    _container.config_repo.load()
    _container.config_repo.update_from_args(args)

    # 4. 强制打开配置界面
    if args.config:
        return run_gui_mode()

    # 5. 打开配置文件编辑
    if args.edit_config:
        if not os.path.exists(config_file):
            config = _container.config_repo.load()
            _container.config_repo.save(config)
        if sys.platform == "win32":
            os.startfile(config_file)
        return 0

    # 6. 启动GUI模式（所有隧道由用户手动启动）
    return run_gui_mode_with_check()


if __name__ == "__main__":
    sys.exit(main())
