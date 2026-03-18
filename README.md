
# OpenClaw 代理工具

![OpenClaw](resources/images/openclaw.png)

一键启动 SSH 端口转发，并自动打开浏览器访问 OpenClaw 服务。

该工具用于连接使用远程openclaw，大大简化 OpenClaw 的远程访问流程，通过自动化代理与浏览器拉起，帮助用户快速、稳定地连接并使用部署于独立主机或docker容器中的OpenClaw 服务。

> **一句话概括**  
> OpenClaw 代理工具让远程访问 OpenClaw 服务，像本地打开网页一样简单。

**Git 仓库**：https://github.com/goodls123/openclaw-proxy.git

---

## 功能概览

### 核心能力

- **一键启动 SSH 端口转发**  
  自动建立本地与远程设备之间的安全访问通道。
- **自动打开浏览器**  
  代理建立完成后，自动在浏览器中打开 OpenClaw 服务地址。
- **免去繁琐配置**  
  无需手动处理以下流程：
  - OpenClaw Token 查询
  - HTTPS 代理配置
  - 设备侧运行与连接细节处理
- **提升远程访问效率**  
  适合需要快速接入 OpenClaw 服务的开发、测试与运维场景。

### 功能特性

- 一键启动 SSH 端口转发隧道
- 自动打开浏览器访问代理地址
- 支持 SSH 密钥生成与自动部署
- 图形化配置界面
- 可打包为独立 EXE 程序
- 无配置或代理失败时自动打开配置界面

---

## 适用场景

- 远程访问部署在服务器或设备端的 OpenClaw 服务
- 本地快速调试 OpenClaw 相关功能
- 减少重复性的代理与访问配置工作
- 降低新用户使用 OpenClaw 的接入门槛

---

## 工具优势

- **操作简单**：开箱即用
- **自动化程度高**：减少手工失误
- **配置更省心**：降低远程访问复杂度
- **体验更流畅**：提升连接效率与使用体验

---

## 环境要求

| 项目 | 要求 |
|---|---|
| Python | 3.9+（开发运行时需要） |
| 操作系统 | Windows 10 / 11 |
| 依赖组件 | 已启用 OpenSSH 客户端 |

---

## 快速开始

### 方式一：直接运行 EXE（推荐）

1. 双击 `openclaw-proxy.exe` 运行程序
2. 首次使用时会自动打开配置界面
3. 填写服务器信息，点击 **“生成并部署密钥”**
4. 输入 SSH 密码完成密钥部署
5. 点击 **“启动代理”**，程序会自动打开浏览器

### 方式二：通过 Python 源码运行

    # 安装依赖
    pip install -r requirements.txt

    # 运行程序
    python main.py

---

## 打包为 EXE

### 方式一：使用打包脚本

    build.bat

### 方式二：手动打包

    pip install pyinstaller
    pyinstaller build.spec --clean

打包完成后，生成文件位于：

    dist/openclaw-proxy.exe

---

## 使用说明

### 自动模式（默认）

直接运行程序后：

- 如果密钥存在且配置正确：**自动启动代理并打开浏览器**
- 如果密钥不存在或代理失败：**自动打开配置界面**

### 命令行参数

    # 强制打开配置界面
    openclaw-proxy.exe --config

    # 指定服务器地址
    openclaw-proxy.exe --host 192.168.1.100 --user admin

    # 不自动打开浏览器
    openclaw-proxy.exe --no-browser

    # 打开配置文件编辑
    openclaw-proxy.exe --edit-config

---

## 配置文件

配置文件 `config.ini` 位于 EXE 同目录下。

<<<<<<< HEAD
### 配置示例

    [ssh]
    host = localhost
    port = 22
    user = root
    local_bind_host = localhost
    local_port = 18789
    remote_host = localhost
    remote_port = 18789
    key_path =
    known_hosts =
    strict_host_key_checking = accept-new
    connect_timeout = 10
    server_alive_interval = 30
    server_alive_count_max = 3
    compression = false
=======
```ini
[ssh]
host = localhost
port = 22
user = admin
local_bind_host = localhost
local_port = 18789
remote_host = localhost
remote_port = 18789
key_path = C:\Users\%USERNAME%\.ssh\openclaw_ed25519
known_hosts = C:\Users\%USERNAME%\.ssh\known_hosts
strict_host_key_checking = accept-new
connect_timeout = 10
server_alive_interval = 30
server_alive_count_max = 3
compression = false

[browser]
auto_open = true
url = http://localhost:18789
open_timeout = 10
>>>>>>> 66dcfa8629292b9dfe3a62bc8998c0c1de17050c

    [browser]
    auto_open = true
    url = http://localhost:18789
    open_timeout = 10
    auto_fetch_token = true
    remote_config_path = ~/.openclaw/openclaw.json
    token =

    [keygen]
    key_type = ed25519
    comment = openclaw-proxy

    [app]
    log_level = INFO
    log_dir = logs

> **说明**  
> 当 `key_path` 和 `known_hosts` 为空时，程序会自动使用系统默认路径：
>
> - `~/.ssh/openclaw_ed25519`
> - `~/.ssh/known_hosts`

---

## 首次使用流程

1. 双击运行 `openclaw-proxy.exe`
2. 程序检测到密钥不存在，自动打开配置界面
3. 在 **“密钥管理”** 标签页点击 **“生成并部署密钥”**
4. 输入 SSH 用户名和密码
5. 等待密钥生成与部署完成
6. 点击 **“启动代理”**
7. 浏览器自动打开 OpenClaw 页面

---

## 安全说明

- 密码仅在内存中短暂存在，不会保存到文件或日志
- 私钥文件存储在用户目录下的 `.ssh` 文件夹中
- 建议优先使用 `ed25519` 密钥类型，兼顾安全性与性能

---

## 常见问题

### 1. 提示“未找到 ssh 命令”

请确认系统已安装并启用 Windows OpenSSH 客户端：

**设置** → **应用** → **可选功能** → **添加功能** → **OpenSSH 客户端**

### 2. 连接超时

请依次检查：

1. 服务器地址和端口是否正确
2. 网络是否可达
3. 防火墙是否允许 SSH 连接

### 3. 认证失败

请检查以下内容：

1. 用户名和密码是否正确
2. 密钥是否已正确部署到远程服务器
3. 远程服务器 `.ssh` 目录权限是否为 `700`
4. `authorized_keys` 文件权限是否为 `600`

---

## 项目结构

    openclaw-proxy/
    ├── main.py              # 主程序入口
    ├── config_manager.py    # 配置管理
    ├── ssh_tunnel.py        # SSH 隧道管理
    ├── key_manager.py       # 密钥生成与部署
    ├── ui.py                # Tkinter 图形界面
    ├── utils.py             # 公共工具函数
    ├── build.spec           # PyInstaller 配置
    ├── build.bat            # 打包脚本
    ├── requirements.txt     # Python 依赖
    └── README.md            # 说明文档

---

## License

MIT
