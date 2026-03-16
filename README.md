# OpenClaw代理工具

一键启动SSH端口转发并自动打开浏览器访问OpenClaw服务。

## 功能特性

- 一键启动SSH端口转发隧道
- 自动打开浏览器访问代理地址
- 支持SSH密钥生成与自动部署
- 图形化配置界面
- 可打包为独立EXE程序
- 无配置/代理失败时自动打开配置界面

## 环境要求

- Python 3.9+（开发时需要）
- Windows 10/11（已启用OpenSSH客户端）

## 快速开始

### 方式一：直接运行EXE（推荐）

1. 双击 `openclaw-proxy.exe` 运行
2. 首次使用会自动打开配置界面
3. 填写服务器信息，点击"生成并部署密钥"
4. 输入SSH密码完成密钥部署
5. 点击"启动代理"，自动打开浏览器

### 方式二：Python源码运行

```bash
# 安装依赖
pip install -r requirements.txt

# 运行
python main.py
```

## 打包为EXE

```bash
# 方式一：使用打包脚本
build.bat

# 方式二：手动打包
pip install pyinstaller
pyinstaller build.spec --clean
```

打包后的文件位于 `dist/openclaw-proxy.exe`

## 使用说明

### 自动模式（默认）

直接运行程序：
- 如果密钥存在且配置正确 → 自动启动代理并打开浏览器
- 如果密钥不存在或代理失败 → 自动打开配置界面

### 命令行参数

```bash
# 强制打开配置界面
openclaw-proxy.exe --config

# 指定服务器地址
openclaw-proxy.exe --host 192.168.1.100 --user admin

# 不自动打开浏览器
openclaw-proxy.exe --no-browser

# 打开配置文件编辑
openclaw-proxy.exe --edit-config
```

## 配置文件

配置文件 `config.ini` 位于EXE同目录下：

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

[keygen]
key_type = ed25519
comment = openclaw-proxy

[app]
log_level = INFO
log_dir = logs
```

## 首次使用流程

1. 双击运行 `openclaw-proxy.exe`
2. 程序检测到密钥不存在，自动打开配置界面
3. 在"密钥管理"标签页点击"生成并部署密钥"
4. 输入SSH用户名和密码
5. 等待密钥生成和部署完成
6. 点击"启动代理"
7. 浏览器自动打开OpenClaw页面

## 安全说明

- 密码仅在内存中短暂存在，不会保存到文件或日志
- 私钥文件存储在用户目录的 `.ssh` 文件夹中
- 建议使用 `ed25519` 密钥类型，更安全且性能更好

## 常见问题

### 提示"未找到ssh命令"

请确保已安装Windows OpenSSH客户端：
- 设置 > 应用 > 可选功能 > 添加功能 > OpenSSH客户端

### 连接超时

1. 检查服务器地址和端口是否正确
2. 检查网络是否可达
3. 检查防火墙是否允许SSH连接

### 认证失败

1. 确认用户名和密码正确
2. 确认密钥已正确部署到远程服务器
3. 检查远程服务器 `.ssh` 目录权限（应为700）
4. 检查 `authorized_keys` 文件权限（应为600）

## 项目结构

```
openclaw-proxy/
├── main.py              # 主程序入口
├── config_manager.py    # 配置管理
├── ssh_tunnel.py        # SSH隧道管理
├── key_manager.py       # 密钥生成与部署
├── ui.py                # Tkinter图形界面
├── utils.py             # 公共工具函数
├── build.spec           # PyInstaller配置
├── build.bat            # 打包脚本
├── requirements.txt     # Python依赖
└── README.md            # 说明文档
```

## License

MIT
