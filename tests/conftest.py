"""
pytest配置和共享fixtures
"""

import os
import tempfile
import pytest
from unittest.mock import Mock, MagicMock
from typing import Tuple, Any

from models import Config, SSHConfig, BrowserConfig, KeygenConfig, AppConfig, UpdateConfig
from repositories.interfaces import IConfigRepository, IRemoteConfigRepository


@pytest.fixture
def temp_config_file(tmp_path):
    """创建临时配置文件路径"""
    return str(tmp_path / "test_config.json")


@pytest.fixture
def sample_config():
    """示例配置对象"""
    return Config(
        ssh=SSHConfig(
            host="test.example.com",
            port=2222,
            user="testuser",
            local_bind_host="127.0.0.1",
            local_port=18789,
            remote_host="127.0.0.1",
            remote_port=18789,
            key_path="/home/testuser/.ssh/test_key",
            known_hosts="/home/testuser/.ssh/known_hosts",
        ),
        browser=BrowserConfig(
            auto_open=True,
            url="http://127.0.0.1:18789",
            open_timeout=10,
            auto_fetch_token=True,
            remote_config_path="~/.openclaw/openclaw.json",
            token="existing_token_12345",
        ),
        keygen=KeygenConfig(
            key_type="ed25519",
            comment="test-comment",
        ),
        app=AppConfig(
            log_level="DEBUG",
            log_dir="test_logs",
        ),
        update=UpdateConfig(
            auto_check=False,
        ),
    )


@pytest.fixture
def sample_config_without_token():
    """没有token的示例配置"""
    config = Config(
        ssh=SSHConfig(
            host="notoken.example.com",
            port=22,
            user="notokenuser",
        ),
        browser=BrowserConfig(
            auto_open=True,
            url="http://127.0.0.1:18789",
            token="",
        ),
    )
    return config


@pytest.fixture
def mock_config_repo(sample_config):
    """Mock配置仓库"""
    repo = Mock(spec=IConfigRepository)
    repo.load.return_value = sample_config
    repo.save.return_value = True
    repo.config_file = "/tmp/test_config.json"
    repo.has_backup.return_value = False
    repo.restore_backup.return_value = False
    return repo


@pytest.fixture
def mock_config_repo_without_token(sample_config_without_token):
    """没有token的Mock配置仓库"""
    repo = Mock(spec=IConfigRepository)
    repo.load.return_value = sample_config_without_token
    repo.save.return_value = True
    repo.config_file = "/tmp/test_config.json"
    return repo


@pytest.fixture
def mock_remote_config_repo():
    """Mock远程配置仓库"""
    repo = Mock(spec=IRemoteConfigRepository)
    # 默认返回成功
    repo.fetch.return_value = (
        True,
        {"gateway": {"auth": {"token": "new_fetched_token_xyz"}}},
        ""
    )
    repo.extract_token.return_value = (True, "new_fetched_token_xyz")
    return repo


@pytest.fixture
def mock_remote_config_repo_failure():
    """失败的Mock远程配置仓库"""
    repo = Mock(spec=IRemoteConfigRepository)
    repo.fetch.return_value = (False, None, "Connection refused")
    repo.extract_token.return_value = (False, "Token not found")
    return repo


@pytest.fixture
def sample_remote_config_dict():
    """示例远程配置字典"""
    return {
        "gateway": {
            "auth": {
                "token": "test_token_abc123"
            },
            "server": {
                "host": "0.0.0.0",
                "port": 18789
            }
        }
    }


@pytest.fixture
def sample_remote_config_without_token():
    """没有token的示例远程配置"""
    return {
        "gateway": {
            "server": {
                "host": "0.0.0.0",
                "port": 18789
            }
        }
    }
