# openclaw-proxy

> Windows 桌面应用 - SSH隧道代理/配置管理/浏览器自动打开/更新检查

[![Version](https://img.shields.io/badge/version-0.0.2.0319-blue)](https://github.com/goodls123/openclaw-proxy)
[![Platform](https://img.shields.io/badge/platform-Windows%2010/11-lightgrey)](https://github.com/goodls123/openclaw-proxy)
[![Python](https://img.shields.io/badge/python-3.8%2B-yellow)](https://github.com/goodls123/openclaw-proxy)

---

## 项目概述

`openclaw-proxy` 是一个基于 **Tkinter** 的 Windows 桌面应用程序，提供以下核心能力：

- **SSH 隧道建立与管理** - 自动建立和管理 SSH 隧道连接
- **密钥生成与部署** - 自动生成 SSH 密钥并部署到远程服务器
- **Token 获取与管理** - 管理认证令牌
- **浏览器自动打开** - 自动打开配置的浏览器URL
- **远程配置获取** - 从远程服务器获取配置信息
- **本地配置读写** - 管理本地配置文件
- **版本更新检查** - 自动检查 GitHub Releases 更新
- **Windows 桌面界面** - 提供直观的 GUI 配置与状态展示

---

## 系统要求

### 必需条件

- **操作系统**: Windows 10 / Windows 11
- **系统组件**: 必须启用 **OpenSSH 客户端**
- **Python**: Python 3.8 或更高版本

### OpenSSH 客户端启用方式

1. 打开"设置" → "应用" → "可选功能"
2. 搜索"OpenSSH 客户端"
3. 点击安装

---

## 技术栈

| 层级 | 技术 |
|------|------|
| **GUI 框架** | Tkinter + ttk |
| **架构模式** | 分层架构 + MVP 模式 |
| **依赖管理** | 依赖注入 (Dependency Injection) |
| **接口约束** | Protocol (PEP 544) |
| **测试框架** | pytest |
| **打包工具** | PyInstaller |
| **配置格式** | INI |

---

## 项目结构

```
openclaw-proxy/
├── main.py                    # 程序入口，命令行参数解析
├── version.py                 # 版本信息
├── requirements.txt           # Python 依赖
├── build.spec                 # PyInstaller 打包配置
├── build.bat                  # Windows 打包脚本
├── config.ini                 # 默认配置文件
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
│   ├── config.py             # 配置模型
│   ├── port_mapping.py       # 端口映射模型
│   ├── tunnel_state.py       # 隧道状态模型
│   └── update_info.py        # 更新信息模型
│
├── services/                  # 业务逻辑层
│   ├── interfaces.py         # 服务接口定义 (Protocol)
│   ├── tunnel_service.py     # SSH 隧道服务
│   ├── key_service.py        # 密钥管理服务
│   ├── token_service.py      # Token 管理服务
│   ├── browser_service.py    # 浏览器服务
│   └── update_service.py     # 更新检查服务
│
├── repositories/              # 数据访问层
│   ├── interfaces.py         # 仓库接口定义
│   ├── config_repository.py  # 本地配置仓库
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
│   │   ├── main_window.py    # 主窗口
│   │   └── config_window.py  # 配置窗口
│   └── dialogs/              # 对话框
│       └── update_dialog.py  # 更新对话框
│
├── components/                # 可复用 UI 组件
│   ├── header_panel.py       # 头部面板
│   ├── status_panel.py       # 状态面板
│   └── port_mapping_frame.py # 端口映射框架
│
├── utils/                     # 工具模块
│   ├── dpi_utils.py          # DPI 适配工具
│   ├── logging_utils.py      # 日志工具
│   ├── network_utils.py      # 网络工具
│   └── path_utils.py         # 路径工具
│
├── resources/                 # 资源文件
│   └── images/               # 图片资源
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
  - ❌ **禁止直接导入 tkinter**
- **Service 层**: 实现业务逻辑
  - ❌ **禁止依赖具体 UI 类**
- **Repository 层**: 配置和远程数据访问
  - ❌ **禁止依赖 Presenter / UI**

### Protocol 约束

所有服务与仓库通过 **Protocol 接口**约束:

- `services/interfaces.py` - 服务接口
- `repositories/interfaces.py` - 仓库接口

**开发原则**: 接口优先，不随意修改现有 Protocol 方法签名

### 依赖注入

所有核心服务通过 `ServiceContainer` 懒加载创建:

```python
container = ServiceContainer.create(config_file)
container.tunnel_service.start()
container.key_service.generate_key(...)
container.browser_service.open()
```

**规则**: 不在任意模块中直接散乱实例化核心服务

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

## Windows 平台特性

### DPI 适配

- 使用 `utils/dpi_utils.py`
- 配置 `dpi.manifest`
- 所有窗口必须考虑 DPI 缩放

### 路径处理

- Windows 路径分隔符兼容
- 用户配置目录: `~/.openclaw-proxy/`

### 打包

- **工具**: PyInstaller
- **配置**: `build.spec`
- **脚本**: `build.bat`
- **输出**: `dist/openclaw-proxy.exe`
- **注意事项**:
  - 资源文件路径兼容 PyInstaller
  - `resources/images/` 正确打包
  - 图标和 manifest 文件正确配置
  - 不硬编码开发环境绝对路径

---

## 样式约定

### GUI 样式

- 优先使用 **ttk** 组件
- 使用统一样式组件:
  - `StyledFrame`
  - `StyledLabel`
  - `StyledButton`
  - `StyledEntry`
- 字体优先: `Microsoft YaHei UI`

### 布局规范

- 同一父容器中不要混用 `pack` 与 `grid`
- 优先延续现有文件中的布局风格
- 新布局必须考虑窗口缩放与 DPI

---

## 配置管理

### 配置位置

- **默认路径**: `~/.openclaw-proxy/config.ini`
- **格式**: INI
- **读写**: 通过 `ConfigRepository`

### 配置来源

配置结构参考:
- `models/config.py` - 配置模型
- `config/constants.py` - 默认值常量

**规则**: 默认值应集中来自 `config/constants.py`，不在多个模块中硬编码

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
python main.py --host 192.168.1.100 --user admin

# 运行测试
pytest -v
pytest tests/test_services -v
pytest tests/test_repositories -v
pytest tests/test_presenters -v
pytest tests/test_ui -v

# 编译检查
python -m compileall .

# 打包
build.bat
pyinstaller build.spec --clean
```

### 分层测试策略

| 层级 | 测试重点 |
|------|----------|
| **Service** | 纯逻辑测试，不依赖 UI |
| **Repository** | 配置读写、默认值、边界条件 |
| **Presenter** | 事件输入与状态输出，不导入 tkinter |
| **UI** | 控件存在、窗口初始化、基础交互 |

---

## 核心服务接口

### ITunnelService
- `start()` - 启动 SSH 隧道
- `stop()` - 停止隧道
- `get_status()` - 获取隧道状态

### IKeyService
- `generate_key()` - 生成 SSH 密钥
- `deploy_key()` - 部署密钥到远程

### ITokenService
- `get_token()` - 获取认证令牌
- `refresh_token()` - 刷新令牌

### IBrowserService
- `open()` - 打开浏览器
- `get_config()` - 获取浏览器配置

### IUpdateService
- `check()` - 检查更新
- `get_update_info()` - 获取更新信息

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

### 禁止行为

- ❌ 在 Presenter 中导入 tkinter
- ❌ 在 UI 中堆积复杂业务逻辑
- ❌ 绕过 ServiceContainer 随意创建服务
- ❌ 绕过 ConfigRepository 直接写配置文件
- ❌ 修改 Protocol 签名而不报告
- ❌ 未验证就标记完成

---

## 版本历史

### 当前版本: 0.0.2.0319

- 初始版本发布
- 基础 SSH 隧道功能
- 配置管理
- 浏览器自动打开
- 更新检查

---

## 仓库信息

- **仓库**: [goodls123/openclaw-proxy](https://github.com/goodls123/openclaw-proxy.git)
- **发布**: GitHub Releases
- **问题反馈**: GitHub Issues

---
