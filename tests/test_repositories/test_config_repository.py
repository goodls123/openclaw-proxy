"""
ConfigRepository 单元测试
测试 JSON 配置仓库
"""

import os
import json
import pytest
from unittest.mock import Mock

from repositories.config_repository import ConfigRepository
from models import Config, SSHConfig, BrowserConfig, PortMapping


class TestConfigRepositoryLoad:
    """测试 load 方法"""

    def test_load_creates_default_config_when_file_not_exists(self, tmp_path):
        """当配置文件不存在时创建默认配置"""
        config_dir = str(tmp_path)
        config_file = str(tmp_path / "config.json")
        repo = ConfigRepository(config_file)

        config = repo.load()

        assert config is not None
        assert isinstance(config, Config)
        assert config.ssh.host == "localhost"
        assert config.ssh.port == 22
        # 应该创建配置文件
        assert os.path.exists(config_file)

    def test_load_existing_config(self, tmp_path):
        """加载已存在的配置文件"""
        config_file = str(tmp_path / "config.json")

        # 创建一个 JSON 配置文件
        config_data = {
            "version": "2.0",
            "global": {
                "app": {"log_level": "DEBUG", "log_dir": "test_logs"},
                "update": {"auto_check": False},
                "keygen": {"key_type": "ed25519", "comment": "test-comment"}
            },
            "servers": [{
                "id": "srv-test",
                "name": "Test Server",
                "enabled": True,
                "auto_run": True,
                "ssh": {
                    "host": "test.example.com",
                    "port": 2222,
                    "user": "testuser"
                },
                "port_mappings": [{
                    "id": "pm-1",
                    "name": "Main",
                    "enabled": True,
                    "local_bind_host": "127.0.0.1",
                    "local_port": 18789,
                    "remote_host": "127.0.0.1",
                    "remote_port": 18789
                }],
                "browser": {
                    "enabled": True,
                    "auto_open": True,
                    "url_template": "http://{local_host}:{local_port}",
                    "open_timeout": 10,
                    "token": {
                        "auto_fetch": True,
                        "remote_config_path": "~/.openclaw/openclaw.json",
                        "cached_token": "test_token_123"
                    }
                }
            }]
        }

        with open(config_file, "w", encoding="utf-8") as f:
            json.dump(config_data, f)

        repo = ConfigRepository(config_file)
        config = repo.load()

        assert config.ssh.host == "test.example.com"
        assert config.ssh.port == 2222
        assert config.ssh.user == "testuser"
        assert config.browser.token == "test_token_123"
        assert config.app.log_level == "DEBUG"
        assert config.update.auto_check is False


class TestConfigRepositorySave:
    """测试 save 方法"""

    def test_save_creates_new_file(self, tmp_path, sample_config):
        """保存配置到新文件"""
        config_file = str(tmp_path / "config.json")
        repo = ConfigRepository(config_file)

        result = repo.save(sample_config)

        assert result is True
        assert os.path.exists(config_file)

    def test_save_preserves_existing_values(self, tmp_path):
        """保存配置保留现有值"""
        config_file = str(tmp_path / "config.json")

        # 先创建一个配置
        repo = ConfigRepository(config_file)
        config = repo.load()

        # 修改一些值
        config.ssh.host = "modified.example.com"
        config.ssh.port = 3333
        config.browser.token = "new_token_xyz"

        result = repo.save(config)

        assert result is True

        # 重新加载验证
        repo2 = ConfigRepository(config_file)
        loaded = repo2.load()

        assert loaded.ssh.host == "modified.example.com"
        assert loaded.ssh.port == 3333
        assert loaded.browser.token == "new_token_xyz"

    def test_save_creates_backup(self, tmp_path):
        """保存时创建备份"""
        config_file = str(tmp_path / "config.json")

        # 先创建一个配置
        repo = ConfigRepository(config_file)
        config = repo.load()
        repo.save(config)

        # 修改并保存
        config.ssh.host = "new.host.com"
        repo.save(config)

        # 应该有备份文件
        assert os.path.exists(config_file + ".bak")


class TestConfigRepositoryBackup:
    """测试备份和恢复"""

    def test_has_backup_returns_false_when_no_backup(self, tmp_path):
        """没有备份时返回False"""
        config_file = str(tmp_path / "config.json")
        repo = ConfigRepository(config_file)

        assert repo.has_backup() is False

    def test_has_backup_returns_true_when_backup_exists(self, tmp_path):
        """有备份时返回True"""
        config_file = str(tmp_path / "config.json")

        # 创建配置和备份
        repo = ConfigRepository(config_file)
        config = repo.load()
        repo.save(config)

        assert repo.has_backup() is True

    def test_restore_backup(self, tmp_path):
        """恢复备份"""
        config_file = str(tmp_path / "config.json")

        repo = ConfigRepository(config_file)
        config = repo.load()
        config.ssh.host = "original.host.com"
        repo.save(config)

        # 修改配置
        config.ssh.host = "modified.host.com"
        repo.save(config)

        # 恢复备份
        result = repo.restore_backup()

        assert result is True
        loaded = repo.load()
        assert loaded.ssh.host == "original.host.com"

    def test_restore_backup_returns_false_when_no_backup(self, tmp_path):
        """没有备份时恢复返回False"""
        config_file = str(tmp_path / "config.json")
        repo = ConfigRepository(config_file)

        result = repo.restore_backup()

        assert result is False


class TestConfigRepositoryPortMappings:
    """测试端口映射配置"""

    def test_load_port_mappings(self, tmp_path):
        """加载端口映射配置"""
        config_file = str(tmp_path / "config.json")

        config_data = {
            "version": "2.0",
            "global": {
                "app": {"log_level": "INFO", "log_dir": "logs"},
                "update": {"auto_check": True},
                "keygen": {"key_type": "ed25519", "comment": "openclaw-proxy"}
            },
            "servers": [{
                "id": "srv-test",
                "name": "Test",
                "enabled": True,
                "auto_run": True,
                "ssh": {
                    "host": "test.example.com",
                    "port": 22,
                    "user": "root"
                },
                "port_mappings": [
                    {
                        "id": "pm-1",
                        "name": "Port 8080",
                        "enabled": True,
                        "local_bind_host": "127.0.0.1",
                        "local_port": 8080,
                        "remote_host": "127.0.0.1",
                        "remote_port": 80
                    },
                    {
                        "id": "pm-2",
                        "name": "Port 9090",
                        "enabled": True,
                        "local_bind_host": "127.0.0.1",
                        "local_port": 9090,
                        "remote_host": "127.0.0.1",
                        "remote_port": 90
                    }
                ]
            }]
        }

        with open(config_file, "w", encoding="utf-8") as f:
            json.dump(config_data, f)

        repo = ConfigRepository(config_file)
        config = repo.load()

        assert len(config.ssh.port_mappings) == 2
        assert config.ssh.port_mappings[0].local_port == 8080
        assert config.ssh.port_mappings[1].local_port == 9090

    def test_save_port_mappings(self, tmp_path):
        """保存端口映射配置"""
        config_file = str(tmp_path / "config.json")
        repo = ConfigRepository(config_file)

        config = Config()
        config.ssh.port_mappings = [
            PortMapping(local_bind_host="127.0.0.1", local_port=8000, remote_host="127.0.0.1", remote_port=80),
            PortMapping(local_bind_host="127.0.0.1", local_port=9000, remote_host="127.0.0.1", remote_port=90),
        ]

        result = repo.save(config)

        assert result is True

        # 重新加载验证
        repo2 = ConfigRepository(config_file)
        loaded = repo2.load()

        assert len(loaded.ssh.port_mappings) == 2


class TestConfigRepositoryUpdateFromArgs:
    """测试从命令行参数更新配置"""

    def test_update_from_args_basic(self, tmp_path):
        """从命令行参数更新基本配置"""
        config_file = str(tmp_path / "config.json")
        repo = ConfigRepository(config_file)
        config = repo.load()

        args = Mock()
        args.host = "args.example.com"
        args.port = 3333
        args.user = "argsuser"

        repo.update_from_args(args)

        assert config.ssh.host == "args.example.com"
        assert config.ssh.port == 3333
        assert config.ssh.user == "argsuser"

    def test_update_from_args_none_values_ignored(self, tmp_path):
        """None值应该被忽略"""
        config_file = str(tmp_path / "config.json")
        repo = ConfigRepository(config_file)
        config = repo.load()

        original_host = config.ssh.host

        args = Mock()
        args.host = None
        args.port = 4444

        repo.update_from_args(args)

        # host不应该被修改
        assert config.ssh.host == original_host
        # port应该被修改
        assert config.ssh.port == 4444

    def test_update_from_args_no_browser(self, tmp_path):
        """--no-browser 参数应该禁用自动打开浏览器"""
        config_file = str(tmp_path / "config.json")
        repo = ConfigRepository(config_file)
        config = repo.load()

        assert config.browser.auto_open is True

        args = Mock()
        args.no_browser = True

        repo.update_from_args(args)

        assert config.browser.auto_open is False


class TestConfigRepositoryConfigFileProperty:
    """测试 config_file 属性"""

    def test_config_file_property(self, tmp_path):
        """config_file 属性应该返回正确的路径"""
        config_file = str(tmp_path / "config.json")
        repo = ConfigRepository(config_file)

        assert repo.config_file == config_file
