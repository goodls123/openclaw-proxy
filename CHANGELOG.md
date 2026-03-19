# 更新日志

### 修复 - 2026-03-19

#### 密钥测试弹窗不显示
- **问题**: 在配置窗口点击密钥"测试"按钮后，日志显示连接成功但没有弹窗提示
- **原因**: `_run_on_ui_thread` 方法只检查 `view.root` 属性，但 `ConfigWindow` 是 `tk.Toplevel`，它本身就有 `after` 方法
- **修复**: 优先使用 `view.root`（MainWindow），如果没有则直接使用 `view` 本身（Toplevel）
- **文件**: `presenters/base.py`

#### 重启代理后实际访问失败
- **问题**: 保存配置后重启代理显示"连接就绪"，但实际代理访问失败
- **原因**: `restart()` 停止隧道后没有将 `self._tunnel` 设为 `None`，导致 `start()` 判断隧道已运行而直接返回，没有用新配置创建隧道
- **修复**: 在 `restart()` 中停止隧道后添加 `self._tunnel = None`
- **文件**: `services/tunnel_service.py`

### 新增

#### 保存配置后自动重启代理
- **功能**: 保存配置后如果隧道正在运行，自动重启让新配置生效
- **文件**: `ui/windows/config_window.py`

#### 保存配置后自动获取 Token
- **功能**: 保存配置后如果启用了自动获取 token，自动获取并保存到配置文件
- **文件**: `ui/windows/config_window.py`

#### 服务器地址变更自动匹配密钥
- **功能**: 服务器地址输入框失去焦点时，自动在 `~/.ssh/` 目录查找匹配 `{host}_ed25519` 或 `{host}_rsa` 格式的密钥文件
- **行为**: 找到则自动填充密钥路径，没找到则清空
- **文件**: `utils/path_utils.py`, `ui/windows/config_window.py`

#### 保存配置时错误弹窗提示
- **功能**: 保存配置时如果出现错误（重启代理失败或 Token 获取失败），弹窗显示具体的错误信息
- **文件**: `ui/windows/config_window.py`
