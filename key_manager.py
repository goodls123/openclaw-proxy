"""
密钥管理模块
负责SSH密钥的生成、公钥部署、连接测试
"""

import os
import sys
import subprocess
import logging
from typing import Optional, Callable
from dataclasses import dataclass

from utils import (
    expand_path,
    ensure_dir,
    check_ssh_keygen_available,
    check_ssh_available,
    get_default_ssh_dir,
)

logger = logging.getLogger("openclaw_proxy")


@dataclass
class KeyDeployResult:
    """密钥部署结果"""
    success: bool
    message: str
    error_detail: Optional[str] = None


class KeyManager:
    """密钥管理器"""

    def __init__(
        self,
        key_path: str,
        key_type: str = "ed25519",
        comment: str = "openclaw-proxy",
    ):
        """
        初始化密钥管理器

        Args:
            key_path: 私钥文件路径
            key_type: 密钥类型 (ed25519 或 rsa)
            comment: 密钥注释
        """
        self.key_path = expand_path(key_path)
        self.public_key_path = self.key_path + ".pub"
        self.key_type = key_type
        self.comment = comment

    def key_exists(self) -> bool:
        """
        检查私钥文件是否存在

        Returns:
            私钥是否存在
        """
        return os.path.exists(self.key_path)

    def backup_key(self) -> tuple[bool, str]:
        """
        备份现有密钥

        Returns:
            (是否成功, 备份路径或错误消息)
        """
        import shutil
        from datetime import datetime

        if not self.key_exists():
            return False, "密钥不存在，无需备份"

        try:
            # 生成备份文件名（带时间戳）
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_dir = os.path.dirname(self.key_path)

            # 备份私钥
            key_backup = f"{self.key_path}.bak_{timestamp}"
            shutil.copy2(self.key_path, key_backup)

            # 备份公钥（如果存在）
            if os.path.exists(self.public_key_path):
                pub_backup = f"{self.public_key_path}.bak_{timestamp}"
                shutil.copy2(self.public_key_path, pub_backup)

            logger.info(f"密钥已备份到: {key_backup}")
            return True, key_backup

        except Exception as e:
            logger.error(f"备份密钥失败: {e}")
            return False, f"备份失败: {str(e)}"

    def delete_key(self) -> tuple[bool, str]:
        """
        删除现有密钥

        Returns:
            (是否成功, 消息)
        """
        if not self.key_exists():
            return True, "密钥不存在"

        try:
            # 删除私钥
            if os.path.exists(self.key_path):
                os.remove(self.key_path)

            # 删除公钥（如果存在）
            if os.path.exists(self.public_key_path):
                os.remove(self.public_key_path)

            logger.info(f"密钥已删除: {self.key_path}")
            return True, "密钥已删除"

        except Exception as e:
            logger.error(f"删除密钥失败: {e}")
            return False, f"删除失败: {str(e)}"

    def generate_key(
        self,
        overwrite: bool = False,
        passphrase: str = "",
    ) -> tuple[bool, str]:
        """
        生成SSH密钥对

        Args:
            overwrite: 是否覆盖已存在的密钥
            passphrase: 密钥密码（可选）

        Returns:
            (是否成功, 消息)
        """
        # 检查ssh-keygen是否可用
        available, path_or_error = check_ssh_keygen_available()
        if not available:
            return False, path_or_error

        # 检查密钥是否已存在
        if self.key_exists() and not overwrite:
            return False, f"密钥文件已存在: {self.key_path}"

        # 确保目录存在
        key_dir = os.path.dirname(self.key_path)
        if not ensure_dir(key_dir):
            return False, f"无法创建目录: {key_dir}"

        # 构建ssh-keygen命令
        cmd = [
            "ssh-keygen",
            "-t", self.key_type,
            "-f", self.key_path,
            "-C", self.comment,
            "-N", passphrase,  # 密码，空字符串表示无密码
        ]

        # 如果是RSA类型，指定位数
        if self.key_type == "rsa":
            cmd.extend(["-b", "4096"])

        try:
            # Windows下隐藏控制台窗口
            kwargs = {
                "capture_output": True,
                "text": True,
                "timeout": 30,
            }
            if sys.platform == "win32":
                kwargs["creationflags"] = 0x08000000  # CREATE_NO_WINDOW

            result = subprocess.run(cmd, **kwargs)

            if result.returncode == 0:
                logger.info(f"密钥生成成功: {self.key_path}")
                return True, f"密钥生成成功: {self.key_path}"
            else:
                error_msg = result.stderr.strip() or result.stdout.strip()
                logger.error(f"密钥生成失败: {error_msg}")
                return False, f"密钥生成失败: {error_msg}"

        except subprocess.TimeoutExpired:
            return False, "密钥生成超时"
        except Exception as e:
            logger.error(f"密钥生成异常: {e}")
            return False, f"密钥生成异常: {str(e)}"

    def get_public_key_content(self) -> Optional[str]:
        """
        读取公钥内容

        Returns:
            公钥内容，失败返回None
        """
        if not os.path.exists(self.public_key_path):
            return None

        try:
            with open(self.public_key_path, "r", encoding="utf-8") as f:
                return f.read().strip()
        except Exception:
            return None

    def deploy_public_key(
        self,
        host: str,
        port: int,
        user: str,
        password: str,
        progress_callback: Optional[Callable[[str], None]] = None,
    ) -> KeyDeployResult:
        """
        将公钥部署到远程服务器

        Args:
            host: 服务器地址
            port: SSH端口
            user: 用户名
            password: 密码
            progress_callback: 进度回调函数

        Returns:
            KeyDeployResult对象
        """
        try:
            import paramiko
        except ImportError:
            return KeyDeployResult(
                success=False,
                message="缺少paramiko库，请运行: pip install paramiko",
            )

        def report(message: str):
            if progress_callback:
                progress_callback(message)
            logger.info(message)

        # 检查公钥是否存在
        public_key = self.get_public_key_content()
        if not public_key:
            report("读取公钥失败，请先生成密钥")
            return KeyDeployResult(
                success=False,
                message="公钥文件不存在，请先生成密钥",
            )

        try:
            report("正在连接服务器...")
            client = paramiko.SSHClient()

            # 自动添加主机密钥（首次连接）
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

            # 连接服务器（增加banner_timeout防止握手阶段超时）
            try:
                client.connect(
                    hostname=host,
                    port=port,
                    username=user,
                    password=password,
                    timeout=30,
                    banner_timeout=30,
                    auth_timeout=60,  # 增加认证超时
                    allow_agent=False,
                    look_for_keys=False,
                )

                # 启用SSH保活机制，防止连接被服务器关闭
                transport = client.get_transport()
                if transport:
                    transport.set_keepalive(10)  # 每10秒发送保活包
            except paramiko.ssh_exception.SSHException as e:
                if "Error reading SSH protocol banner" in str(e):
                    return KeyDeployResult(
                        success=False,
                        message="SSH握手失败，请检查服务器SSH服务是否正常",
                        error_detail=str(e),
                    )
                raise
            except paramiko.ssh_exception.AuthenticationException as e:
                return KeyDeployResult(
                    success=False,
                    message="认证失败，请检查用户名和密码",
                    error_detail=str(e),
                )
            except Exception as e:
                error_name = type(e).__name__
                if "timeout" in str(e).lower() or "Timeout" in error_name:
                    return KeyDeployResult(
                        success=False,
                        message=f"连接超时，请检查服务器地址和端口是否正确",
                        error_detail=f"{error_name}: {str(e)}",
                    )
                raise

            report("已连接，正在检查远程.ssh目录...")

            # 确保远程.ssh目录存在并设置正确权限
            commands = [
                "mkdir -p ~/.ssh",
                "chmod 700 ~/.ssh",
            ]

            for cmd in commands:
                stdin, stdout, stderr = client.exec_command(cmd)
                stdout.channel.recv_exit_status()

            report("正在读取远程authorized_keys...")

            # 读取远程已有的authorized_keys
            stdin, stdout, stderr = client.exec_command(
                "cat ~/.ssh/authorized_keys 2>/dev/null || echo ''"
            )
            existing_keys = stdout.read().decode("utf-8").strip()

            # 检查公钥是否已存在
            if public_key in existing_keys:
                client.close()
                report("公钥已存在，无需重复部署")
                return KeyDeployResult(
                    success=True,
                    message="公钥已存在于远程服务器",
                )

            report("正在部署公钥...")

            # 追加公钥（带重试机制）
            append_cmd = f'echo "{public_key}" >> ~/.ssh/authorized_keys'
            max_retries = 3
            last_error = None

            for attempt in range(max_retries):
                try:
                    stdin, stdout, stderr = client.exec_command(append_cmd)
                    exit_status = stdout.channel.recv_exit_status()

                    if exit_status != 0:
                        error = stderr.read().decode("utf-8")
                        client.close()
                        return KeyDeployResult(
                            success=False,
                            message="写入authorized_keys失败",
                            error_detail=error,
                        )
                    break  # 成功则退出重试循环
                except Exception as cmd_error:
                    last_error = cmd_error
                    if attempt < max_retries - 1:
                        report(f"命令执行失败，正在重试 ({attempt + 2}/{max_retries})...")
                        # 检查连接是否仍然活跃
                        transport = client.get_transport()
                        if not transport or not transport.is_active():
                            report("连接已断开，正在重新连接...")
                            client.close()
                            client = paramiko.SSHClient()
                            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                            client.connect(
                                hostname=host,
                                port=port,
                                username=user,
                                password=password,
                                timeout=30,
                                banner_timeout=30,
                                auth_timeout=60,
                                allow_agent=False,
                                look_for_keys=False,
                            )
                            new_transport = client.get_transport()
                            if new_transport:
                                new_transport.set_keepalive(10)
                    else:
                        raise last_error

            # 设置权限
            report("正在设置权限...")
            stdin, stdout, stderr = client.exec_command("chmod 600 ~/.ssh/authorized_keys")
            stdout.channel.recv_exit_status()

            client.close()
            report("公钥部署成功")

            return KeyDeployResult(
                success=True,
                message="公钥部署成功",
            )

        except paramiko.AuthenticationException:
            report("认证失败：用户名或密码错误")
            return KeyDeployResult(
                success=False,
                message="认证失败：用户名或密码错误",
            )
        except paramiko.SSHException as e:
            report(f"SSH连接错误: {str(e)}")
            return KeyDeployResult(
                success=False,
                message=f"SSH连接错误",
                error_detail=str(e),
            )
        except OSError as e:
            # 处理网络相关的错误（如连接被重置、超时等）
            error_code = getattr(e, 'winerror', getattr(e, 'errno', None))
            if error_code == 10054 or 'connection reset' in str(e).lower():
                report("连接被服务器重置，可能是网络不稳定或服务器超时")
                return KeyDeployResult(
                    success=False,
                    message="连接被服务器重置，请检查网络连接或稍后重试",
                    error_detail=str(e),
                )
            elif 'timeout' in str(e).lower():
                report("连接超时")
                return KeyDeployResult(
                    success=False,
                    message="连接超时，请检查服务器是否可达",
                    error_detail=str(e),
                )
            else:
                report(f"网络错误: {str(e)}")
                return KeyDeployResult(
                    success=False,
                    message="网络连接错误",
                    error_detail=str(e),
                )
        except Exception as e:
            report(f"部署异常: {str(e)}")
            return KeyDeployResult(
                success=False,
                message="部署过程中发生错误",
                error_detail=str(e),
            )

    def test_key_connection(
        self,
        host: str,
        port: int,
        user: str,
        timeout: int = 10,
    ) -> tuple[bool, str]:
        """
        测试使用密钥连接远程服务器

        Args:
            host: 服务器地址
            port: SSH端口
            user: 用户名
            timeout: 超时时间

        Returns:
            (是否成功, 消息)
        """
        # 检查ssh命令是否可用
        available, _ = check_ssh_available()
        if not available:
            return False, "系统ssh命令不可用"

        # 检查私钥是否存在
        if not self.key_exists():
            return False, f"私钥文件不存在: {self.key_path}"

        # 构建测试命令（使用BatchMode禁止密码提示）
        cmd = [
            "ssh",
            "-o", "BatchMode=yes",
            "-o", "StrictHostKeyChecking=accept-new",
            "-o", f"ConnectTimeout={timeout}",
            "-i", self.key_path,
            "-p", str(port),
            f"{user}@{host}",
            "echo 'connection_test_success'",
        ]

        try:
            # Windows下隐藏控制台窗口
            kwargs = {
                "capture_output": True,
                "text": True,
                "timeout": timeout + 5,
            }
            if sys.platform == "win32":
                kwargs["creationflags"] = 0x08000000  # CREATE_NO_WINDOW

            result = subprocess.run(cmd, **kwargs)

            if result.returncode == 0 and "connection_test_success" in result.stdout:
                logger.info(f"密钥连接测试成功: {user}@{host}")
                return True, "连接测试成功"
            else:
                error_msg = result.stderr.strip()
                if "Permission denied" in error_msg:
                    return False, "认证失败：密钥可能未正确部署"
                return False, f"连接失败: {error_msg}"

        except subprocess.TimeoutExpired:
            return False, "连接超时"
        except Exception as e:
            return False, f"测试异常: {str(e)}"

    @staticmethod
    def test_host_reachable(host: str, port: int, timeout: int = 5) -> tuple[bool, str]:
        """
        测试SSH主机是否可达（仅测试TCP连接，不验证认证）

        Args:
            host: 服务器地址
            port: SSH端口
            timeout: 超时时间

        Returns:
            (是否可达, 消息)
        """
        import socket

        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            result = sock.connect_ex((host, port))
            sock.close()

            if result == 0:
                return True, "主机可达"
            else:
                return False, f"无法连接到 {host}:{port}"
        except socket.timeout:
            return False, "连接超时"
        except socket.gaierror as e:
            return False, f"主机名解析失败: {str(e)}"
        except Exception as e:
            return False, f"连接失败: {str(e)}"

    def generate_and_deploy(
        self,
        host: str,
        port: int,
        user: str,
        password: str,
        overwrite: bool = True,
        progress_callback: Optional[Callable[[str], None]] = None,
    ) -> KeyDeployResult:
        """
        生成密钥并部署到远程服务器（一站式操作）

        Args:
            host: 服务器地址
            port: SSH端口
            user: 用户名
            password: 密码
            overwrite: 是否覆盖已存在的密钥
            progress_callback: 进度回调函数

        Returns:
            KeyDeployResult对象
        """
        def report(message: str):
            if progress_callback:
                progress_callback(message)
            logger.info(message)

        # 步骤1：生成密钥
        report("正在生成密钥...")
        success, message = self.generate_key(overwrite=overwrite)
        if not success:
            return KeyDeployResult(success=False, message=message)

        # 步骤2：部署公钥
        report("正在部署公钥到远程服务器...")
        result = self.deploy_public_key(
            host=host,
            port=port,
            user=user,
            password=password,
            progress_callback=progress_callback,
        )
        if not result.success:
            return result

        # 步骤3：测试连接
        report("正在测试免密连接...")
        success, message = self.test_key_connection(
            host=host,
            port=port,
            user=user,
        )
        if success:
            report("部署完成，后续可直接使用密钥登录")
            return KeyDeployResult(
                success=True,
                message="密钥生成并部署成功，可免密登录",
            )
        else:
            return KeyDeployResult(
                success=False,
                message=f"密钥已部署但测试连接失败: {message}",
                error_detail=message,
            )
