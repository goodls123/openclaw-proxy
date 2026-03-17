#!/usr/bin/env python3
"""
OpenClaw代理工具
一键启动SSH端口转发并自动打开浏览器

启动顺序：
1. 初始化日志
2. 启用Windows DPI感知（UI模式时）
3. 加载配置
4. 创建UI/启动代理
"""

import os
import sys
import argparse
import time
import webbrowser
import logging
from typing import Optional

from utils import setup_logging, check_ssh_available, can_connect, expand_path
from config_manager import ConfigManager
from key_manager import KeyManager
from ssh_tunnel import SSHTunnel
from version import __version__

# 全局变量
logger: Optional[logging.Logger] = None
config_manager: Optional[ConfigManager] = None
tunnel: Optional[SSHTunnel] = None


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
    parser.add_argument("--config-file", default="config.ini", help="配置文件路径")
    parser.add_argument("--verbose", "-v", action="store_true", help="详细输出")

    return parser.parse_args()


def check_environment() -> tuple[bool, str]:
    """检查运行环境"""
    available, error = check_ssh_available()
    if not available:
        return False, f"{error}\n\n请在Windows设置中启用OpenSSH客户端:\n设置 > 应用 > 可选功能 > 添加功能 > OpenSSH客户端"
    return True, ""


def check_key_exists() -> bool:
    """检查密钥是否存在"""
    key_path = expand_path(config_manager.config.ssh.key_path)
    return os.path.exists(key_path)


def start_tunnel() -> tuple[bool, str]:
    """启动SSH隧道"""
    global tunnel
    config = config_manager.config

    # 创建隧道（使用多端口映射）
    tunnel = SSHTunnel(
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

    # 检查前置条件
    success, error = tunnel.check_prerequisites()
    if not success:
        return False, error

    # 启动隧道
    success, message = tunnel.start()
    if not success:
        return False, message

    # 等待连接建立
    success, message = tunnel.wait_for_connection(timeout=config.browser.open_timeout)
    if not success:
        tunnel.stop()
        return False, message

    return True, "隧道连接成功"


def stop_tunnel():
    """停止SSH隧道"""
    global tunnel
    if tunnel:
        tunnel.stop()
        tunnel = None


def run_gui_mode(title: str = "OpenClaw代理配置"):
    """运行图形界面模式"""
    from ui import MainWindow
    app = MainWindow(config_manager, title=title)
    app.run()
    return 0


def run_auto_mode():
    """
    自动模式：
    1. 检查配置，无配置则打开配置界面
    2. 测试SSH连接
    3. 失败则打开配置界面
    4. 成功则启动代理并打开浏览器
    """
    config = config_manager.config

    # 检查环境
    success, error = check_environment()
    if not success:
        from tkinter import messagebox
        messagebox.showerror("环境错误", error)
        return 1

    # 检查密钥是否存在
    if not check_key_exists():
        logger.info("密钥不存在，打开配置界面")
        return run_gui_mode("首次使用 - 请配置SSH密钥")

    # 先测试SSH连接（使用BatchMode，避免密码提示）
    logger.info("正在测试SSH连接...")
    from key_manager import KeyManager
    key_manager = KeyManager(key_path=config.ssh.key_path)

    success, message = key_manager.test_key_connection(
        host=config.ssh.host,
        port=config.ssh.port,
        user=config.ssh.user,
        timeout=5,
    )

    if not success:
        logger.error(f"SSH连接测试失败: {message}")
        return run_gui_mode("配置 - SSH连接失败")

    # 测试成功，启动隧道
    logger.info("正在启动SSH隧道...")
    success, message = start_tunnel()

    if not success:
        logger.error(f"启动失败: {message}")
        stop_tunnel()
        return run_gui_mode("配置 - 代理启动失败")

    # 隧道启动成功，打开浏览器
    logger.info("隧道启动成功")
    if config.browser.auto_open:
        logger.info(f"正在打开浏览器: {config.browser.url}")
        webbrowser.open(config.browser.url)

    # 显示运行状态窗口
    from ui import StatusWindow
    app = StatusWindow(config_manager, tunnel)
    app.run()

    return 0


def main():
    """主函数"""
    global logger, config_manager

    args = parse_args()

    # 确定用户配置目录 ~/.openclaw-proxy/
    user_config_dir = os.path.join(os.path.expanduser("~"), ".openclaw-proxy")
    if not os.path.exists(user_config_dir):
        os.makedirs(user_config_dir)

    # 配置文件和日志目录都放在用户配置目录下
    config_file = os.path.join(user_config_dir, "config.ini")
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

    # 2. 加载配置
    config_manager = ConfigManager(config_file)
    config_manager.load()
    config_manager.update_from_args(args)

    # 3. 强制打开配置界面
    if args.config:
        return run_gui_mode()

    # 4. 打开配置文件编辑
    if args.edit_config:
        if not os.path.exists(config_file):
            config_manager.save()
        if sys.platform == "win32":
            os.startfile(config_file)
        return 0

    # 5. 自动模式（会自动处理DPI设置）
    return run_auto_mode()


if __name__ == "__main__":
    sys.exit(main())
