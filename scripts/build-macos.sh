#!/bin/bash
# -*- coding: utf-8 -*-
#
# 虾代理 - macOS 打包脚本
#
# 使用方式:
#   ./scripts/build-macos.sh              # 构建当前架构
#   ARCH=x86_64 ./scripts/build-macos.sh  # 构建 Intel 版本
#   ARCH=arm64 ./scripts/build-macos.sh   # 构建 Apple Silicon 版本
#
# 环境变量:
#   ARCH         - 目标架构 (x86_64 或 arm64)
#   PYTHON_PATH  - Python 可执行文件路径 (可选)
#

set -e  # 遇到错误立即退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 项目根目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# 目标架构
ARCH="${ARCH:-$(uname -m)}"

# 产物名称
if [[ "$ARCH" == "x86_64" ]]; then
    OUTPUT_NAME="xia_proxy_macos-x86_64"
elif [[ "$ARCH" == "arm64" ]]; then
    OUTPUT_NAME="xia_proxy_macos-arm64"
else
    OUTPUT_NAME="xia_proxy_macos"
fi

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  虾代理 - macOS 打包脚本${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# 切换到项目根目录
cd "$PROJECT_ROOT"

# 检查 Python
PYTHON="${PYTHON_PATH:-python3}"
if ! command -v "$PYTHON" &> /dev/null; then
    echo -e "${RED}[错误] 未找到 Python3，请先安装${NC}"
    exit 1
fi

PYTHON_VERSION=$("$PYTHON" --version 2>&1)
echo -e "${GREEN}[信息] Python: $PYTHON_VERSION${NC}"

# 获取版本号
VERSION=$("$PYTHON" scripts/get_version.py 2>/dev/null || echo "unknown")
echo -e "${GREEN}[信息] 版本: $VERSION${NC}"
echo -e "${GREEN}[信息] 架构: $ARCH${NC}"

# 检查 PyInstaller
if ! "$PYTHON" -m pip show pyinstaller &> /dev/null; then
    echo -e "${YELLOW}[信息] 正在安装 PyInstaller...${NC}"
    "$PYTHON" -m pip install pyinstaller
fi

# 检查依赖
if ! "$PYTHON" -m pip show paramiko &> /dev/null; then
    echo -e "${YELLOW}[信息] 正在安装依赖...${NC}"
    "$PYTHON" -m pip install -r requirements.txt
fi

# 打包
echo ""
echo -e "${GREEN}[信息] 开始打包...${NC}"
echo -e "${GREEN}[信息] 目标: $OUTPUT_NAME${NC}"

export TARGET_ARCH="$ARCH"

if [[ "$ARCH" == "x86_64" ]]; then
    # Intel Mac
    "$PYTHON" -m PyInstaller build-macos.spec --clean --target-arch x86_64
elif [[ "$ARCH" == "arm64" ]]; then
    # Apple Silicon
    "$PYTHON" -m PyInstaller build-macos.spec --clean --target-arch arm64
else
    # 当前架构
    "$PYTHON" -m PyInstaller build-macos.spec --clean
fi

# 重命名产物
if [[ -f "dist/xia_proxy_macos" ]]; then
    mv "dist/xia_proxy_macos" "dist/$OUTPUT_NAME"
fi

# 验证产物
echo ""
if [[ -f "dist/$OUTPUT_NAME" ]]; then
    FILE_SIZE=$(stat -f%z "dist/$OUTPUT_NAME" 2>/dev/null || stat -c%s "dist/$OUTPUT_NAME" 2>/dev/null || echo "unknown")
    FILE_PATH="$(pwd)/dist/$OUTPUT_NAME"
    
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}  打包完成！${NC}"
    echo -e "${GREEN}  版本: $VERSION${NC}"
    echo -e "${GREEN}  架构: $ARCH${NC}"
    echo -e "${GREEN}  输出: $FILE_PATH${NC}"
    echo -e "${GREEN}  大小: $FILE_SIZE bytes${NC}"
    echo -e "${GREEN}========================================${NC}"
    
    # 设置可执行权限
    chmod +x "dist/$OUTPUT_NAME"
    
    echo ""
    echo "运行测试:"
    echo "  ./dist/$OUTPUT_NAME"
else
    echo -e "${RED}[错误] 打包失败，未找到产物${NC}"
    exit 1
fi
