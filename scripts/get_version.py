#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
版本号提取工具

从 Git 标签或 version.py 提取版本号，供 CI/CD 使用。

使用方式:
    python scripts/get_version.py              # 输出版本号
    python scripts/get_version.py --json       # 输出 JSON 格式
    python scripts/get_version.py --source     # 输出版本来源 (git/file)
"""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path


def get_version_from_git() -> str | None:
    """
    从 Git 标签获取版本号
    
    使用 git describe --tags 获取最近的标签
    返回格式: v1.2.3 或 1.2.3 (去掉 v 前缀)
    """
    try:
        # 检查是否在 Git 仓库中
        result = subprocess.run(
            ["git", "rev-parse", "--git-dir"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent
        )
        if result.returncode != 0:
            return None
        
        # 获取最近的标签
        result = subprocess.run(
            ["git", "describe", "--tags", "--abbrev=0"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent
        )
        
        if result.returncode == 0:
            version = result.stdout.strip()
            # 去掉 v 前缀
            if version.startswith("v"):
                version = version[1:]
            return version
        
        return None
    except Exception:
        return None


def get_version_from_file() -> str | None:
    """
    从 version.py 文件获取版本号
    """
    try:
        version_file = Path(__file__).parent.parent / "version.py"
        if not version_file.exists():
            return None
        
        # 读取文件内容并解析 __version__
        content = version_file.read_text(encoding="utf-8")
        
        for line in content.split("\n"):
            line = line.strip()
            if line.startswith("__version__"):
                # 提取引号中的版本号
                if '"' in line:
                    version = line.split('"')[1]
                elif "'" in line:
                    version = line.split("'")[1]
                else:
                    continue
                
                if version:
                    return version
        
        return None
    except Exception:
        return None


def get_version() -> tuple[str, str]:
    """
    获取版本号（优先 Git 标签，fallback 到文件）
    
    Returns:
        tuple[str, str]: (版本号, 来源) - 来源为 "git" 或 "file"
    """
    # 优先从 Git 标签获取
    version = get_version_from_git()
    if version:
        return version, "git"
    
    # Fallback 到 version.py
    version = get_version_from_file()
    if version:
        return version, "file"
    
    # 最后 fallback 到默认值
    return "0.0.0", "default"


def main():
    parser = argparse.ArgumentParser(
        description="版本号提取工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
    python scripts/get_version.py              # 输出版本号
    python scripts/get_version.py --json       # 输出 JSON 格式
    python scripts/get_version.py --source     # 输出版本来源
        """
    )
    
    parser.add_argument(
        "--json",
        action="store_true",
        help="输出 JSON 格式"
    )
    parser.add_argument(
        "--source",
        action="store_true",
        help="输出版本来源 (git/file/default)"
    )
    
    args = parser.parse_args()
    
    version, source = get_version()
    
    if args.json:
        output = {
            "version": version,
            "source": source
        }
        print(json.dumps(output, indent=2))
    elif args.source:
        print(source)
    else:
        print(version)


if __name__ == "__main__":
    main()
