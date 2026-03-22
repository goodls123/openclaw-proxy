@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

echo ========================================
echo   虾代理 - Windows 打包脚本
echo ========================================
echo.

:: 检查Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到Python，请先安装Python 3.9+
    pause
    exit /b 1
)

:: 获取版本号
echo [信息] 获取版本号...
for /f "delims=" %%i in ('python scripts\get_version.py 2^>nul') do set VERSION=%%i
if "%VERSION%"=="" set VERSION=unknown
echo [信息] 版本: %VERSION%

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
echo [信息] 目标: xia_proxy_win.exe
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
echo   版本: %VERSION%
echo   输出: dist\xia_proxy_win.exe
echo ========================================
echo.

:: 复制配置文件模板
if not exist "dist\config.json" (
    echo [信息] 生成默认配置文件...
    python -c "from repositories.json_config_repository import JsonConfigRepository; import os; repo = JsonConfigRepository('dist'); repo.save(repo.load_multi())"
)

:: 显示产物信息
if exist "dist\xia_proxy_win.exe" (
    for %%F in ("dist\xia_proxy_win.exe") do (
        echo 产物信息:
        echo   - 大小: %%~zF bytes
        echo   - 路径: %%~fF
    )
)

echo.
echo 提示: 首次运行会自动生成配置文件
echo.
pause
