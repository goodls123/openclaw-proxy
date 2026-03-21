# 更新日志

All notable changes to this project will be documented in this file.

## [0.0.2.0320] - 2026-03-20

### 新增功能

#### 多服务器支持
- **多服务器配置管理**: 支持管理多个远程SSH服务器配置
  - 新增 `MultiServerConfig` 和 `ServerConfig` 数据模型
  - 新增 `JsonConfigRepository` 处理JSON格式配置
  - 配置文件从INI格式升级为JSON格式（v2.0）
  - 支持自动从旧版INI配置迁移

- **多隧道管理服务**: `MultiTunnelService`
  - 按服务器ID启动/停止隧道
  - 批量操作（全部启动/停止）
  - 状态监控
  - 异步启动/停止支持

- **服务器列表界面**: `ServerListPanel`
  - 横向滚动展示服务器列表
  - 左键点击启动/停止代理
  - 右键菜单：连接配置、浏览器打开
  - 状态指示器（run.png/stop.png）显示连接状态
  - "新增连接"按钮快速添加服务器

#### 统一密钥管理
- **全局密钥配置**: 所有服务器共用一套密钥
  - 密钥类型选择（ed25519/rsa）
  - 密钥路径和已知主机文件配置
  - 公钥/私钥内容预览

- **密钥管理对话框**: `SecurityDialog`
  - 独立的密钥管理界面
  - 生成/重置密钥功能
  - 密钥内容实时显示

#### 新增对话框
- `ConfigDialog`: SSH配置对话框（支持新建/编辑模式）
  - 服务器地址、端口、用户名配置
  - 连接选项配置（超时、保活、压缩）
  - 端口映射配置
  - 密钥测试和部署
  - 配置验证（重复检查、端口冲突检测）

- `AddServerDialog`: 快速添加服务器对话框

### 改进

#### 主窗口重构
- 界面重新设计，采用服务器列表横向展示
- 合并按钮：启动/停止代理合并为单个切换按钮
- 状态控制：`_is_tunnel_running` 变量跟踪隧道状态
- 窗口标题统一为 "OpenClaw连接代理"
- 最小窗口尺寸调整为 600x300

#### 配置保存增强
- 保存配置后自动重启代理（如果隧道正在运行）
- 保存配置后自动获取 Token（如果启用）
- 保存配置时错误弹窗提示

#### 其他改进
- 服务器地址变更自动匹配密钥
- 窗体状态配置修复
- DPI适配优化

### 修复

#### 密钥测试弹窗不显示
- **问题**: 在配置窗口点击密钥"测试"按钮后，日志显示连接成功但没有弹窗提示
- **原因**: `_run_on_ui_thread` 方法只检查 `view.root` 属性，但 `ConfigWindow` 是 `tk.Toplevel`
- **修复**: 优先使用 `view.root`，如果没有则直接使用 `view` 本身
- **文件**: `presenters/base.py`

#### 重启代理后实际访问失败
- **问题**: 保存配置后重启代理显示"连接就绪"，但实际代理访问失败
- **原因**: `restart()` 停止隧道后没有将 `self._tunnel` 设为 `None`
- **修复**: 在 `restart()` 中停止隧道后添加 `self._tunnel = None`
- **文件**: `services/tunnel_service.py`

### 删除

- 移除 `config.ini` 旧配置格式
- 移除 `ui/windows/config_window.py` 旧配置窗口（替换为 `ConfigDialog`）

### 文件变更

#### 新增文件
- `models/server_config.py` - 多服务器配置模型
- `services/multi_tunnel_service.py` - 多隧道管理服务
- `repositories/json_config_repository.py` - JSON配置仓库
- `components/server_list_panel.py` - 服务器列表面板
- `ui/dialogs/add_server_dialog.py` - 添加服务器对话框
- `ui/dialogs/config_dialog.py` - SSH配置对话框
- `ui/dialogs/security_dialog.py` - 密钥管理对话框
- `resources/images/add.png` - 添加按钮图标
- `resources/images/pc.png` - 服务器图标
- `resources/images/run.png` - 运行状态图标
- `resources/images/stop.png` - 停止状态图标

#### 修改文件
- `main.py` - 入口调整
- `app/container.py` - 添加 MultiTunnelService
- `app/bootstrap.py` - 启动流程调整
- `config/settings.py` - 设置管理更新
- `models/__init__.py` - 导出更新
- `presenters/main_presenter.py` - 主窗口Presenter重构
- `repositories/config_repository.py` - 封装 JsonConfigRepository
- `repositories/interfaces.py` - 接口更新
- `services/browser_service.py` - 服务更新
- `services/key_service.py` - 服务更新
- `services/token_service.py` - 服务更新
- `ui/__init__.py` - 导出更新
- `ui/windows/__init__.py` - 导出更新
- `ui/windows/main_window.py` - 主窗口重构

#### 删除文件
- `config.ini` - 旧配置格式
- `ui/windows/config_window.py` - 旧配置窗口

---

## [0.0.2.0319] - 2026-03-19

### 新增
- 初始版本发布
- 基础 SSH 隧道功能
- 配置管理
- 浏览器自动打开
- 更新检查

### 新增功能（2026-03-19 补充）
- 保存配置后自动重启代理
- 保存配置后自动获取 Token
- 服务器地址变更自动匹配密钥
- 保存配置时错误弹窗提示

---

## 版本说明

版本号格式: `主版本.次版本.修订.日期`

- **主版本**: 重大架构变更
- **次版本**: 新功能添加
- **修订**: Bug修复和小改进
- **日期**: 发布日期 (MMDD)
