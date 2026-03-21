# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.
使用中文与用户交互

## 项目概述

OpenClaw 代理工具 - 一键启动 SSH 端口转发并自动打开浏览器访问远程 OpenClaw 服务。

- **版本**: 0.0.2.0320
- **仓库**: goodls123/openclaw-proxy
- **平台**: Windows 10/11（需启用 OpenSSH 客户端）

## 项目结构

```
openclaw-proxy/
├── main.py                    # 主程序入口，命令行参数解析
├── version.py                 # 版本信息
├── requirements.txt           # 依赖（paramiko, pyinstaller, Pillow）
├── build.spec / build.bat     # PyInstaller 打包配置
├── config.json                # 默认配置模板
├── dpi.manifest              # Windows DPI 清单
│
├── app/                       # 应用启动和依赖注入
│   ├── container.py           # ServiceContainer 依赖注入容器
│   └── bootstrap.py           # 应用启动引导
│
├── config/                    # 配置和常量
│   ├── constants.py           # 常量定义（默认值、GitHub信息）
│   └── settings.py            # 设置管理
│
├── models/                    # 数据模型
│   ├── config.py              # 旧版配置模型（兼容层）
│   ├── server_config.py       # 多服务器配置模型（MultiServerConfig, ServerConfig）
│   ├── port_mapping.py        # 端口映射模型
│   ├── tunnel_state.py        # 隧道状态模型
│   └── update_info.py         # 更新信息模型
│
├── services/                  # 业务逻辑服务（通过Protocol接口定义）
│   ├── interfaces.py          # 服务接口定义（ITunnelService等）
│   ├── tunnel_service.py      # 单隧道管理（兼容旧版）
│   ├── multi_tunnel_service.py  # 多隧道管理服务
│   ├── key_service.py         # 密钥生成与部署
│   ├── token_service.py       # Token获取与管理
│   ├── browser_service.py     # 浏览器自动打开
│   └── update_service.py      # 版本更新检查
│
├── repositories/              # 数据访问层
│   ├── interfaces.py          # 仓库接口定义
│   ├── config_repository.py   # 配置文件读写（封装JsonConfigRepository）
│   ├── json_config_repository.py  # JSON配置仓库
│   └── remote_config_repository.py  # 远程配置获取
│
├── presenters/                # MVP模式 - Presenter层
│   ├── base.py                # Presenter基类
│   ├── main_presenter.py      # 主窗口Presenter
│   ├── config_presenter.py    # 配置窗口Presenter
│   └── status_presenter.py    # 状态窗口Presenter
│
├── ui/                        # 图形界面（Tkinter）
│   ├── base.py                # UI基类（BaseWindow, BaseDialog）
│   ├── windows/               # 窗口
│   │   └── main_window.py     # 主窗口
│   └── dialogs/               # 对话框
│       ├── update_dialog.py   # 更新对话框
│       ├── add_server_dialog.py  # 添加服务器对话框
│       ├── config_dialog.py   # SSH配置对话框
│       └── security_dialog.py # 密钥管理对话框
│
├── components/                # 可复用UI组件
│   ├── header_panel.py        # 头部面板（Logo、标题）
│   ├── status_panel.py        # 状态显示面板
│   ├── server_list_panel.py   # 服务器列表面板
│   └── port_mapping_frame.py  # 端口映射配置框
│
├── utils/                     # 工具函数
│   ├── dpi_utils.py           # DPI适配
│   ├── logging_utils.py       # 日志配置
│   ├── network_utils.py       # 网络工具
│   └── path_utils.py          # 路径处理
│
├── resources/                 # 资源文件
│   └── images/                # 图片资源（favicon.ico, pc.png, run.png, stop.png, add.png）
│
├── tests/                     # 测试
│   ├── conftest.py            # pytest fixtures
│   ├── test_services/         # 服务层测试
│   ├── test_repositories/     # 仓库层测试
│   ├── test_presenters/       # Presenter测试
│   └── test_ui/               # UI测试
│
└── logs/                      # 日志文件目录
```

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

输出文件位于 `dist/openclaw-proxy.exe`

## 架构设计

项目采用分层架构 + MVP模式 + 依赖注入：

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

### 核心模块职责

| 模块 | 职责 |
|------|------|
| `main.py` | 入口、参数解析、自动/手动模式路由 |
| `app/container.py` | 依赖注入容器，懒加载创建所有服务 |
| `services/` | 业务逻辑，通过Protocol接口定义 |
| `repositories/` | 配置文件读写、远程配置获取 |
| `presenters/` | MVP模式Presenter，连接UI和Service |
| `ui/` | Tkinter界面，BaseWindow/BaseDialog基类 |
| `components/` | 可复用UI组件 |
| `models/` | 数据模型定义 |
| `utils/` | 工具函数（DPI、日志、网络、路径） |

### 依赖注入

所有服务通过 `ServiceContainer` 懒加载创建：

```python
# 创建容器
container = ServiceContainer.create(config_file)

# 访问服务（懒加载）
container.multi_tunnel_service.start_server(server_id)
container.key_service.generate_key(...)
container.browser_service.open()
```

### MVP模式

Presenter负责连接UI和Service：
- 接收UI事件
- 调用Service处理业务逻辑
- 更新UI状态
- 不直接导入tkinter

## 配置管理

- **配置文件位置**: `~/.openclaw-proxy/config.json`
- **格式**: JSON格式，通过 `JsonConfigRepository` 读写
- **配置结构**: 见 `models/server_config.py` (MultiServerConfig, ServerConfig)
- **旧版兼容**: `ConfigRepository` 封装 `JsonConfigRepository`，保持接口兼容
- **默认值**: 见 `config/constants.py`

### 多服务器配置

配置结构支持多服务器：
- `global_config`: 全局配置（应用、更新、密钥）
- `servers[]`: 服务器列表，每个服务器独立SSH配置和端口映射
- `migration`: 迁移信息（从INI格式迁移）

### 密钥管理

密钥配置统一在 `global_config.keygen` 中：
- `key_type`: 密钥类型 (ed25519/rsa)
- `key_path`: 密钥路径
- `known_hosts`: 已知主机文件

所有服务器共用同一套密钥配置。

## 服务接口

所有服务通过 `Protocol` 接口定义（`services/interfaces.py`）：

| 接口 | 职责 |
|------|------|
| `IConfigRepository` | 配置文件读写 |
| `IRemoteConfigRepository` | 远程配置获取 |
| `ITunnelService` | SSH隧道管理（单隧道，兼容旧版） |
| `IKeyService` | 密钥生成与部署 |
| `ITokenService` | Token获取与管理 |
| `IBrowserService` | 浏览器自动打开 |
| `IUpdateService` | 版本更新检查 |

### 多隧道服务

`MultiTunnelService` 提供多服务器隧道管理：
- `start_server(server_id)` - 启动指定服务器
- `stop_server(server_id)` - 停止指定服务器
- `start_all()` / `stop_all()` - 批量操作
- `get_all_statuses()` - 获取所有状态

## UI开发

- **框架**: Tkinter + ttk + PIL
- **基类**: `ui/base.py` (BaseWindow, BaseDialog)
- **Presenter基类**: `presenters/base.py`
- **DPI适配**: `utils/dpi_utils.py`
- **样式**: 统一样式组件（StyledFrame, StyledLabel, StyledButton, StyledEntry）
- **字体**: Microsoft YaHei UI

### 主要UI组件

- `MainWindow`: 主窗口，服务器列表展示
- `ServerListPanel`: 服务器列表面板（横向滚动）
- `ServerItem`: 单个服务器项（图标+名称+状态指示器）
- `ConfigDialog`: SSH配置对话框
- `SecurityDialog`: 密钥管理对话框
- `AddServerDialog`: 添加服务器对话框

## 测试

测试目录结构:
```
tests/
├── conftest.py               # pytest fixtures
├── test_services/            # 服务层测试
│   └── test_token_service.py
├── test_repositories/        # 仓库层测试
│   └── test_config_repository.py
├── test_presenters/          # Presenter 测试
└── test_ui/                  # UI 测试
```

## 版本信息

- 当前版本: 0.0.2.0320
- GitHub仓库: goodls123/openclaw-proxy
- 发布地址: https://github.com/goodls123/openclaw-proxy/releases
