@echo off
chcp 65001 >nul
echo ========================================
echo   OpenClaw代理工具 - 打包脚本
echo ========================================
echo.

:: 检查Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到Python，请先安装Python 3.9+
    pause
    exit /b 1
)

:: 检查PyInstaller
pip show pyinstaller >nul 2>&1
if errorlevel 1 (
    echo [信息] 正在安装PyInstaller...
    pip install pyinstaller
)

:: 检查依赖
pip show paramiko >nul 2>&1
if errorlevel 1 (
    echo [信息] 正在安装依赖...
    pip install -r requirements.txt
)

:: 打包
echo [信息] 正在打包...
pyinstaller build.spec --clean

if errorlevel 1 (
    echo.
    echo [错误] 打包失败
    pause
    exit /b 1
)

echo.
echo ========================================
echo   打包完成！
echo   输出文件: dist\openclaw-proxy.exe
echo ========================================
echo.

:: 复制配置文件模板
if not exist "dist\config.ini" (
    echo [信息] 生成默认配置文件...
    python -c "from config_manager import ConfigManager; ConfigManager('dist/config.ini').save()"
)

echo 提示: 首次运行会自动生成配置文件
echo.
pause
