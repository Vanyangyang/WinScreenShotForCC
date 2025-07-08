#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
快速修复依赖问题
"""

import subprocess
import sys

def install_package(package):
    """安装单个包"""
    try:
        print(f"正在安装 {package}...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])
        print(f"✓ {package} 安装成功")
        return True
    except subprocess.CalledProcessError:
        print(f"✗ {package} 安装失败")
        return False

def main():
    print("=" * 50)
    print("截图工具依赖修复程序")
    print("=" * 50)
    
    # 必需的包列表
    required_packages = [
        "Pillow>=9.0.0",
        "pyperclip>=1.8.0",
        "keyboard>=0.13.0",
        "pystray>=0.19.0",
        "PyInstaller>=5.0.0",
        "pywin32>=300"
    ]
    
    print("\n正在升级pip...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", "pip"])
        print("✓ pip升级成功")
    except:
        print("! pip升级失败，继续安装")
    
    print("\n开始安装依赖包...")
    failed = []
    
    for package in required_packages:
        if not install_package(package):
            failed.append(package)
    
    print("\n" + "=" * 50)
    if failed:
        print("以下包安装失败:")
        for pkg in failed:
            print(f"  - {pkg}")
        print("\n请尝试手动安装或检查网络连接")
    else:
        print("✓ 所有依赖安装成功！")
        print("\n现在可以运行:")
        print("  - python screenshot_gui.py    # 运行截图工具")
        print("  - python build_spec.py        # 构建可执行文件")
    
    input("\n按回车键退出...")

if __name__ == "__main__":
    main()