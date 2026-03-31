# Release {VERSION}

**发布日期**: {DATE}

## 变更日志

{CHANGES}

## 下载

### Windows

- [xia_proxy_win.exe](https://github.com/goodls123/openclaw-proxy/releases/download/{TAG}/xia_proxy_win.exe)
  - 适用于 Windows 10/11 (64位)
  - 双击运行即可，无需安装

### macOS

- [xia_proxy_macos-x86_64](https://github.com/goodls123/openclaw-proxy/releases/download/{TAG}/xia_proxy_macos-x86_64)
  - 适用于 macOS Intel (x86_64)
  
- [xia_proxy_macos-arm64](https://github.com/goodls123/openclaw-proxy/releases/download/{TAG}/xia_proxy_macos-arm64)
  - 适用于 macOS Apple Silicon (M1/M2/M3)

> **macOS 用户**: 首次运行可能需要在"系统偏好设置" → "安全性与隐私"中允许运行。

## 系统要求

### Windows
- Windows 10 或 Windows 11
- 必须启用 OpenSSH 客户端

### macOS
- macOS 10.15 (Catalina) 或更高版本

## 安装说明

1. 下载对应平台的可执行文件
2. Windows: 双击 `xia_proxy_win.exe` 运行
3. macOS: 
   ```bash
   chmod +x xia_proxy_macos-*
   ./xia_proxy_macos-arm64  # 或 x86_64
   ```

## 升级说明

直接替换旧版本可执行文件即可，配置文件会自动保留。

## 已知问题

- macOS 版本暂未签名，首次运行需要在系统设置中允许
- Windows 版本暂无代码签名

---

**完整变更记录**: https://github.com/goodls123/openclaw-proxy/compare/{PREVIOUS_TAG}...{TAG}
