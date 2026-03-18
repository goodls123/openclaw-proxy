# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.
使用中文与用户交互

## 项目概述

OpenClaw 代理工具 - 一键启动 SSH 端口转发并自动打开浏览器访问远程 OpenClaw 服务。

## 常用命令

### 开发运行
```bash
# 安装依赖
pip install -r requirements.txt

# 运行程序（自动模式）
python main.py

# 强制打开配置界面
python main.py --config

# 详细输出模式
python main.py --verbose

# 指定服务器运行
python main.py --host 192.168.1.100 --user admin
```

### 打包发布
```bash
# 使用打包脚本
build.bat

# 或手动打包
pyinstaller build.spec --clean
```

输出文件位于 `dist/虾代理.exe`

## 架构设计

项目采用分层架构 + 依赖注入模式：

```
┌─────────────────────────────────────────────────────┐
│                    main.py                          │
│              (入口 + 命令行参数解析)                  │
└─────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────┐
│              app/container.py                       │
│           (ServiceContainer 依赖注入容器)            │
└─────────────────────────────────────────────────────┘
                         │
        ┌────────────────┼────────────────┐
        ▼                ▼                ▼
┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│ repositories │ │   services   │ │  presenters  │
│  (数据访问)   │ │  (业务逻辑)   │ │  (MVP控制)   │
└──────────────┘ └──────────────┘ └──────────────┘
        │                │                │
        └────────────────┼────────────────┘
                         ▼
┌─────────────────────────────────────────────────────┐
│              ui/ + components/                      │
│               (Tkinter 图形界面)                     │
└─────────────────────────────────────────────────────┘
```

### 核心模块

| 目录 | 职责 |
|------|------|
| `models/` | 数据模型定义 (Config, PortMapping, TunnelState) |
| `services/` | 业务逻辑服务，通过接口定义 (ITunnelService, IKeyService 等) |
| `repositories/` | 配置和数据持久化 (ConfigRepository, RemoteConfigRepository) |
| `presenters/` | MVP 模式的 Presenter，连接 UI 和 Service |
| `ui/windows/` | 主窗口实现 (MainWindow, StatusWindow, ConfigWindow) |
| `ui/dialogs/` | 对话框组件 |
| `components/` | 可复用 UI 组件 (StatusPanel, HeaderPanel, PortMappingFrame) |
| `app/` | 依赖注入容器和启动引导 |
| `config/` | 常量和设置 |

### 依赖注入

所有服务通过 `ServiceContainer` 懒加载创建，便于测试和解耦：

```python
# 创建容器
container = ServiceContainer.create(config_file)

# 访问服务
container.tunnel_service.start()
container.key_service.generate_key(...)
container.browser_service.open()
```

## 配置管理

- 配置文件位置: `~/.openclaw-proxy/config.ini`
- 使用 INI 格式，通过 `ConfigRepository` 读写
- 配置结构见 `models/config.py` (SSHConfig, BrowserConfig 等)
- 支持多端口映射 (`port_mappings` 列表)

## UI 开发

- 使用 Tkinter + ttk 组件
- 窗口基类: `ui/base.py`
- Presenter 基类: `presenters/base.py`
- DPI 适配: `utils/dpi_utils.py`

## 测试

测试目录结构:
```
tests/
├── conftest.py           # pytest fixtures
├── test_services/        # 服务层测试
├── test_repositories/    # 仓库层测试
├── test_presenters/      # Presenter 测试
└── test_ui/              # UI 测试
```
