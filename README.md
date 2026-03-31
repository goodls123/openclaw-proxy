# openclaw-proxy

> Windows 桌面应用 - 多服务器SSH隧道代理/配置管理/浏览器自动打开/更新检查

[![Version](https://img.shields.io/badge/version-0.0.2.0320-blue)](https://github.com/goodls123/openclaw-proxy)
[![Platform](https://img.shields.io/badge/platform-Windows%2010/11-lightgrey)](https://github.com/goodls123/openclaw-proxy)
[![Python](https://img.shields.io/badge/python-3.8%2B-yellow)](https://github.com/goodls123/openclaw-proxy)

---

## 项目概述

`openclaw-proxy` 是一个基于 **Tkinter** 的 Windows 桌面应用程序，提供以下核心能力：

- **多服务器管理** - 支持管理多个远程SSH服务器配置
- **SSH 隧道建立与管理** - 自动建立和管理 SSH 隧道连接，支持多端口映射
- **密钥生成与部署** - 统一的密钥管理，自动生成 SSH 密钥并部署到远程服务器
- **Token 获取与管理** - 管理认证令牌
- **浏览器自动打开** - 隧道建立后自动打开配置的浏览器URL
- **版本更新检查** - 自动检查 GitHub Releases 更新
- **Windows 桌面界面** - 直观的图形界面，服务器列表可视化展示

---

## 功能特性

### 多服务器支持

- 横向服务器列表展示，一目了然
- 左键点击服务器图标启动/停止代理
- 右键菜单快速访问配置和浏览器
- 状态指示器显示连接状态

### 统一密钥管理

- 所有服务器共用一套全局密钥配置
- 支持 ed25519 和 RSA 密钥类型
- 一键生成和部署公钥到远程服务器
- 公钥/私钥内容预览

### 端口映射

- 支持单服务器多端口映射
- 可视化端口映射配置
- 启用/禁用单个映射

---

## 系统要求

### 必需条件

- **操作系统**: Windows 10 / Windows 11
- **系统组件**: 必须启用 **OpenSSH 客户端**
- **Python**: Python 3.8 或更高版本（开发运行）

### OpenSSH 客户端启用方式

1. 打开"设置" → "应用" → "可选功能"
2. 搜索"OpenSSH 客户端"
3. 点击安装

---

## 技术栈

| 层级 | 技术 |
|------|------|
| **GUI 框架** | Tkinter + ttk + PIL |
| **架构模式** | 分层架构 + MVP 模式 |
| **依赖管理** | 依赖注入 (Dependency Injection) |
| **接口约束** | Protocol (PEP 544) |
| **测试框架** | pytest |
| **打包工具** | PyInstaller |
| **配置格式** | JSON |

---

## 项目结构

```
openclaw-proxy/
├── main.py                    # 程序入口，命令行参数解析
├── version.py                 # 版本信息
├── requirements.txt           # Python 依赖
├── build.spec                 # PyInstaller 打包配置
├── build.bat                  # Windows 打包脚本
├── config.json                # 默认配置文件
├── dpi.manifest              # DPI 感知清单
│
├── app/                       # 应用启动与容器
│   ├── container.py          # 依赖注入容器
│   └── bootstrap.py          # 应用启动引导
│
├── config/                    # 配置管理
│   ├── constants.py          # 常量定义
│   └── settings.py           # 设置管理
│
├── models/                    # 数据模型
│   ├── config.py             # 旧版配置模型（兼容）
│   ├── server_config.py      # 多服务器配置模型
│   ├── port_mapping.py       # 端口映射模型
│   ├── tunnel_state.py       # 隧道状态模型
│   └── update_info.py        # 更新信息模型
│
├── services/                  # 业务逻辑层
│   ├── interfaces.py         # 服务接口定义 (Protocol)
│   ├── tunnel_service.py     # SSH 隧道服务
│   ├── multi_tunnel_service.py  # 多隧道管理服务
│   ├── key_service.py        # 密钥管理服务
│   ├── token_service.py      # Token 管理服务
│   ├── browser_service.py    # 浏览器服务
│   └── update_service.py     # 更新检查服务
│
├── repositories/              # 数据访问层
│   ├── interfaces.py         # 仓库接口定义
│   ├── config_repository.py  # 本地配置仓库（兼容封装）
│   ├── json_config_repository.py  # JSON配置仓库
│   └── remote_config_repository.py  # 远程配置仓库
│
├── presenters/                # MVP 协调层
│   ├── base.py               # Presenter 基类
│   ├── main_presenter.py     # 主窗口 Presenter
│   ├── config_presenter.py   # 配置 Presenter
│   └── status_presenter.py   # 状态 Presenter
│
├── ui/                        # 用户界面层
│   ├── base.py               # UI 基类
│   ├── windows/              # 窗口
│   │   └── main_window.py    # 主窗口
│   └── dialogs/              # 对话框
│       ├── update_dialog.py  # 更新对话框
│       ├── add_server_dialog.py  # 添加服务器对话框
│       ├── config_dialog.py  # SSH配置对话框
│       └── security_dialog.py  # 密钥管理对话框
│
├── components/                # 可复用 UI 组件
│   ├── header_panel.py       # 头部面板
│   ├── status_panel.py       # 状态面板
│   ├── server_list_panel.py  # 服务器列表面板
│   └── port_mapping_frame.py # 端口映射框架
│
├── utils/                     # 工具模块
│   ├── dpi_utils.py          # DPI 适配工具
│   ├── logging_utils.py      # 日志工具
│   ├── network_utils.py      # 网络工具
│   └── path_utils.py         # 路径工具
│
├── resources/                 # 资源文件
│   └── images/               # 图片资源（favicon.ico, pc.png, run.png, stop.png, add.png）
│
├── tests/                     # 测试文件
│   ├── test_services/        # 服务测试
│   ├── test_repositories/    # 仓库测试
│   ├── test_presenters/      # Presenter 测试
│   └── test_ui/              # UI 测试
│
└── logs/                      # 日志输出
```

---

## 架构设计

### 分层架构

```
┌─────────────────────────────────────────┐
│           UI Layer (Tkinter)            │  窗口、对话框、组件
├─────────────────────────────────────────┤
│        Presenter Layer (MVP)            │  UI 与 Service 协调
├─────────────────────────────────────────┤
│         Service Layer (业务逻辑)         │  隧道、密钥、Token等
├─────────────────────────────────────────┤
│       Repository Layer (数据访问)        │  配置、远程数据
├─────────────────────────────────────────┤
│            Model Layer (数据)            │  配置、状态、更新信息
├─────────────────────────────────────────┤
│      Container (依赖注入与组装)          │  ServiceContainer
└─────────────────────────────────────────┘
```

### MVP 模式约束

**强制规则**:

- **UI 层**: 显示界面、收集用户事件
- **Presenter 层**: 接收 UI 事件、调用 Service、更新 UI 状态
  - 禁止直接导入 tkinter
- **Service 层**: 实现业务逻辑
  - 禁止依赖具体 UI 类
- **Repository 层**: 配置和远程数据访问
  - 禁止依赖 Presenter / UI

### 依赖注入

所有核心服务通过 `ServiceContainer` 懒加载创建:

```python
container = ServiceContainer.create(config_file)
container.multi_tunnel_service.start_server(server_id)
container.key_service.generate_key(...)
container.browser_service.open()
```

---

## 目录职责

| 目录 | 职责 |
|------|------|
| `main.py` | 程序入口、命令行参数解析、自动/手动模式路由 |
| `app/container.py` | 依赖注入容器、所有服务/仓库的懒加载入口 |
| `repositories/` | 配置文件读写、远程配置获取，只负责数据访问 |
| `services/` | 业务逻辑实现，必须围绕 Protocol 接口开发 |
| `presenters/` | MVP 核心协调层，**不得直接导入 tkinter** |
| `ui/` | 视图和交互入口，应依赖 Presenter |
| `components/` | 可复用 UI 组件，保持高内聚、低耦合 |
| `models/` | 数据模型定义，结构稳定、清晰 |
| `utils/` | DPI、日志、路径、网络等工具 |

---

## 配置管理

### 配置位置

- **默认路径**: `~/.openclaw-proxy/config.json`
- **格式**: JSON (v2.0)
- **读写**: 通过 `JsonConfigRepository`

### 配置结构

```json
{
  "version": "2.0",
  "global_config": {
    "app": { "log_level": "INFO", "log_dir": "logs" },
    "update": { "auto_check": true },
    "keygen": {
      "key_type": "ed25519",
      "key_path": "~/.ssh/openclaw_proxy_ed25519",
      "known_hosts": "~/.ssh/known_hosts"
    }
  },
  "servers": [
    {
      "id": "srv-xxx",
      "name": "服务器名称",
      "enabled": true,
      "is_default": true,
      "ssh": {
        "host": "192.168.1.100",
        "port": 22,
        "user": "root"
      },
      "port_mappings": [
        {
          "id": "pm-xxx",
          "name": "主映射",
          "enabled": true,
          "local_bind_host": "127.0.0.1",
          "local_port": 18789,
          "remote_host": "127.0.0.1",
          "remote_port": 18789
        }
      ],
      "browser": {
        "enabled": true,
        "auto_open": true,
        "url_template": "http://{local_host}:{local_port}"
      }
    }
  ]
}
```

---

## 验证与测试

### 常用命令

```bash
# 安装依赖
pip install -r requirements.txt

# 运行程序
python main.py
python main.py --config       # 打开配置窗口
python main.py --verbose      # 详细日志

# 运行测试
pytest -v
pytest tests/test_services -v
pytest tests/test_repositories -v

# 编译检查
python -m compileall .

# 打包
build.bat
pyinstaller build.spec --clean
```

---

## 核心服务接口

### IMultiTunnelService

- `start_server(server_id)` - 启动指定服务器隧道
- `stop_server(server_id)` - 停止指定服务器隧道
- `start_all()` - 启动所有启用的服务器
- `stop_all()` - 停止所有运行中的隧道
- `get_all_statuses()` - 获取所有服务器状态

### IKeyService

- `generate_key()` - 生成 SSH 密钥
- `deploy_key()` - 部署密钥到远程

### ITokenService

- `get_token()` - 获取认证令牌
- `refresh_token()` - 刷新令牌

### IBrowserService

- `open()` - 打开浏览器

### IUpdateService

- `check()` - 检查更新

---

## 开发规范

### 代码规范

- 遵循 **PEP 8**
- 使用**类型提示**
- 为主要类/函数添加**文档字符串**
- 保持**最小改动**
- 保持**公开接口稳定**

### 线程安全

- Tkinter UI 更新必须在主线程
- 耗时操作委托到 Service / 后台执行
- 使用 `after()` 方法回写 UI 状态

---

## 发布流程

### 自动发布 (推荐)

项目使用 GitHub Actions 自动构建和发布，支持 Windows 和 macOS 双平台。

#### 触发方式

1. **推送标签** (推荐)
   ```bash
   # 创建并推送标签
   git tag v1.0.0
   git push origin v1.0.0
   ```

2. **手动触发**
   - 进入 GitHub Actions 页面
   - 选择 "Build and Release" 工作流
   - 点击 "Run workflow"
   - 可选：输入版本号

#### 产物

| 平台 | 文件名 | 说明 |
|------|--------|------|
| Windows | `xia_proxy_win.exe` | Windows 10/11 (64-bit) |
| macOS Intel | `xia_proxy_macos-x86_64` | macOS Intel (x86_64) |
| macOS Apple Silicon | `xia_proxy_macos-arm64` | macOS M1/M2/M3 (arm64) |

### 本地构建

#### Windows
```bash
# 安装依赖
pip install -r requirements.txt
pip install pyinstaller

# 打包
build.bat

# 产物位置
dist\xia_proxy_win.exe
```

#### macOS
```bash
# 安装依赖
pip3 install -r requirements.txt
pip3 install pyinstaller

# 打包 (当前架构)
./scripts/build-macos.sh

# 打包 Intel 版本
ARCH=x86_64 ./scripts/build-macos.sh

# 打包 Apple Silicon 版本
ARCH=arm64 ./scripts/build-macos.sh

# 产物位置
dist/xia_proxy_macos-{arch}
```

### 版本号规则

版本号格式: `MAJOR.MINOR.PATCH.BUILD`

- **MAJOR**: 重大版本更新
- **MINOR**: 功能更新
- **PATCH**: Bug 修复
- **BUILD**: 构建号 (可选)

版本来源优先级:
1. Git 标签 (如 `v1.0.0`)
2. `version.py` 文件
3. 默认值 `0.0.0`

---

## 版本历史

### 当前版本: 0.0.2.0320

详见 [CHANGELOG.md](CHANGELOG.md)

---

## 仓库信息

- **仓库**: [goodls123/openclaw-proxy](https://github.com/goodls123/openclaw-proxy.git)
- **发布**: GitHub Releases
- **问题反馈**: GitHub Issues

---
