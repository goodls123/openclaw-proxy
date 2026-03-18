"""
TokenService 单元测试
"""

import pytest
import threading
from unittest.mock import Mock, patch, MagicMock
from typing import Tuple

from services.token_service import TokenService
from models import Config, SSHConfig, BrowserConfig


class TestTokenServiceGetToken:
    """测试 get_token 方法"""

    def test_get_token_from_memory_cache(self, mock_config_repo, mock_remote_config_repo):
        """从内存缓存获取token"""
        service = TokenService(mock_config_repo, mock_remote_config_repo)

        # 先设置内存缓存
        service._token = "cached_token_123"

        # 应该返回缓存的token，不应该调用config_repo
        token = service.get_token()

        assert token == "cached_token_123"
        mock_config_repo.load.assert_not_called()

    def test_get_token_from_config_when_no_cache(self, mock_config_repo, mock_remote_config_repo):
        """当没有内存缓存时，从配置文件获取token"""
        service = TokenService(mock_config_repo, mock_remote_config_repo)

        # 配置文件中有token
        token = service.get_token()

        assert token == "existing_token_12345"
        mock_config_repo.load.assert_called_once()

    def test_get_token_caches_after_loading_from_config(self, mock_config_repo, mock_remote_config_repo):
        """从配置加载后应该缓存到内存"""
        service = TokenService(mock_config_repo, mock_remote_config_repo)

        # 第一次调用
        token1 = service.get_token()
        # 第二次调用
        token2 = service.get_token()

        assert token1 == token2 == "existing_token_12345"
        # 只调用一次load，第二次从内存缓存获取
        assert mock_config_repo.load.call_count == 1

    def test_get_token_returns_none_when_no_token(self, mock_config_repo_without_token, mock_remote_config_repo):
        """当没有token时返回None"""
        service = TokenService(mock_config_repo_without_token, mock_remote_config_repo)

        token = service.get_token()

        assert token == "" or token is None


class TestTokenServiceFetchTokenSync:
    """测试 fetch_token_sync 方法"""

    def test_fetch_token_sync_success(self, mock_config_repo, mock_remote_config_repo):
        """同步获取token成功"""
        service = TokenService(mock_config_repo, mock_remote_config_repo)

        success, token = service.fetch_token_sync()

        assert success is True
        assert token == "new_fetched_token_xyz"
        mock_remote_config_repo.fetch.assert_called_once()
        mock_remote_config_repo.extract_token.assert_called_once()

    def test_fetch_token_sync_updates_memory_cache(self, mock_config_repo, mock_remote_config_repo):
        """同步获取token后更新内存缓存"""
        service = TokenService(mock_config_repo, mock_remote_config_repo)

        service.fetch_token_sync()

        assert service._token == "new_fetched_token_xyz"

    def test_fetch_token_sync_saves_to_config(self, mock_config_repo, mock_remote_config_repo):
        """同步获取token后保存到配置文件"""
        service = TokenService(mock_config_repo, mock_remote_config_repo)

        service.fetch_token_sync()

        mock_config_repo.save.assert_called_once()
        # 验证保存的配置中包含新token
        saved_config = mock_config_repo.save.call_args[0][0]
        assert saved_config.browser.token == "new_fetched_token_xyz"

    def test_fetch_token_sync_fetch_failure(self, mock_config_repo, mock_remote_config_repo_failure):
        """获取远程配置失败"""
        service = TokenService(mock_config_repo, mock_remote_config_repo_failure)

        success, error = service.fetch_token_sync()

        assert success is False
        assert "Connection refused" in error or error != ""

    def test_fetch_token_sync_extract_failure(self, mock_config_repo, sample_remote_config_without_token):
        """从配置中提取token失败"""
        mock_remote = Mock()
        mock_remote.fetch.return_value = (True, sample_remote_config_without_token, "")
        mock_remote.extract_token.return_value = (False, "Token not found in config")

        service = TokenService(mock_config_repo, mock_remote)

        success, error = service.fetch_token_sync()

        assert success is False
        assert "Token not found" in error


class TestTokenServiceFetchTokenAsync:
    """测试 fetch_token_async 方法"""

    def test_fetch_token_async_success(self, mock_config_repo, mock_remote_config_repo):
        """异步获取token成功"""
        service = TokenService(mock_config_repo, mock_remote_config_repo)

        result = {"called": False, "success": None, "token": None}

        def callback(success, token):
            result["called"] = True
            result["success"] = success
            result["token"] = token

        service.fetch_token_async(callback)

        # 等待异步线程完成
        max_wait = 2.0  # 最多等待2秒
        waited = 0.0
        while not result["called"] and waited < max_wait:
            threading.Event().wait(0.05)
            waited += 0.05

        assert result["called"] is True
        assert result["success"] is True
        assert result["token"] == "new_fetched_token_xyz"

    def test_fetch_token_async_failure(self, mock_config_repo, mock_remote_config_repo_failure):
        """异步获取token失败"""
        service = TokenService(mock_config_repo, mock_remote_config_repo_failure)

        result = {"called": False, "success": None, "token": None}

        def callback(success, token):
            result["called"] = True
            result["success"] = success
            result["token"] = token

        service.fetch_token_async(callback)

        # 等待异步线程完成
        max_wait = 2.0
        waited = 0.0
        while not result["called"] and waited < max_wait:
            threading.Event().wait(0.05)
            waited += 0.05

        assert result["called"] is True
        assert result["success"] is False
        assert result["token"] == ""


class TestTokenServiceGetBrowserUrl:
    """测试 get_browser_url 方法"""

    def test_get_browser_url_with_token(self, mock_config_repo, mock_remote_config_repo):
        """生成带token的URL"""
        service = TokenService(mock_config_repo, mock_remote_config_repo)

        url = service.get_browser_url()

        # 应该包含token参数
        assert "#token=" in url
        assert "existing_token_12345" in url

    def test_get_browser_url_without_token(self, mock_config_repo_without_token, mock_remote_config_repo):
        """没有token时生成不带token的URL"""
        service = TokenService(mock_config_repo_without_token, mock_remote_config_repo)

        url = service.get_browser_url()

        # 不应该包含token参数
        assert "#token=" not in url

    def test_get_browser_url_uses_config_values(self, mock_config_repo, mock_remote_config_repo):
        """URL应该使用配置中的host和port"""
        service = TokenService(mock_config_repo, mock_remote_config_repo)

        url = service.get_browser_url()

        # 检查使用了配置中的local_bind_host和local_port
        assert "127.0.0.1" in url
        assert "18789" in url


class TestTokenServiceClearCache:
    """测试 clear_cache 方法"""

    def test_clear_cache(self, mock_config_repo, mock_remote_config_repo):
        """清除缓存"""
        service = TokenService(mock_config_repo, mock_remote_config_repo)

        # 先设置缓存
        service._token = "cached_token"
        assert service.token == "cached_token"

        # 清除缓存
        service.clear_cache()

        assert service.token is None

    def test_clear_cache_then_reload_from_config(self, mock_config_repo, mock_remote_config_repo):
        """清除缓存后重新从配置加载"""
        service = TokenService(mock_config_repo, mock_remote_config_repo)

        # 先加载一次
        token1 = service.get_token()
        assert token1 == "existing_token_12345"

        # 清除缓存
        service.clear_cache()

        # 再次获取应该从配置重新加载
        token2 = service.get_token()
        assert token2 == "existing_token_12345"
        # 应该调用两次load
        assert mock_config_repo.load.call_count >= 2


class TestTokenServiceTokenProperty:
    """测试 token 属性"""

    def test_token_property_returns_none_initially(self, mock_config_repo, mock_remote_config_repo):
        """初始时token属性为None"""
        service = TokenService(mock_config_repo, mock_remote_config_repo)

        assert service.token is None

    def test_token_property_returns_cached_value(self, mock_config_repo, mock_remote_config_repo):
        """token属性返回缓存的值"""
        service = TokenService(mock_config_repo, mock_remote_config_repo)

        service._token = "test_token_value"

        assert service.token == "test_token_value"
