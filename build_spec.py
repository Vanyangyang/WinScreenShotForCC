#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
截图工具打包配置文件
使用 PyInstaller 打包截图工具为独立可执行文件
"""

import PyInstaller.__main__
import sys
import os
from pathlib import Path

def build_screenshot_tool():
    """构建截图工具"""
    # 获取当前目录
    current_dir = Path(__file__).parent
    
    # 主程序文件 - 使用GUI版本
    main_script = current_dir / "screenshot_gui.py"
    
    # 构建参数
    build_args = [
        str(main_script),
        '--onefile',                    # 打包成单个exe文件
        '--windowed',                   # 不显示控制台窗口
        '--name=ScreenshotTool',        # 输出文件名
        '--icon=icon.ico',              # 图标文件（如果存在）
        '--add-data=screenshot_config.json;.',  # 包含配置文件
        '--clean',                      # 清理临时文件
        '--noconfirm',                  # 不确认覆盖
        '--optimize=2',                 # 优化级别
        '--strip',                      # 去除调试信息
        '--upx-dir=upx',               # UPX压缩（如果可用）
        '--distpath=dist',             # 输出目录
        '--workpath=build',            # 工作目录
        '--specpath=.',                # spec文件目录
        
        # 隐藏导入的模块
        '--hidden-import=PIL',
        '--hidden-import=PIL.Image',
        '--hidden-import=PIL.ImageTk',
        '--hidden-import=PIL.ImageGrab',
        '--hidden-import=PIL.ImageDraw',
        '--hidden-import=pyperclip',
        '--hidden-import=keyboard',
        '--hidden-import=pystray',
        '--hidden-import=pystray._base',
        '--hidden-import=pystray._win32',
        '--hidden-import=tkinter',
        '--hidden-import=tkinter.ttk',
        '--hidden-import=tkinter.filedialog',
        '--hidden-import=tkinter.messagebox',
        '--hidden-import=json',
        '--hidden-import=threading',
        '--hidden-import=pathlib',
        '--hidden-import=datetime',
        '--hidden-import=ctypes',
        '--hidden-import=ctypes.wintypes',
        '--hidden-import=win32gui',
        '--hidden-import=win32ui',
        '--hidden-import=win32con',
        '--hidden-import=subprocess',
        '--hidden-import=screenshot_tool_new',
        '--hidden-import=sys',
        '--hidden-import=os',
        '--hidden-import=traceback',
        
        # 排除不需要的模块
        '--exclude-module=matplotlib',
        '--exclude-module=numpy',
        '--exclude-module=pandas',
        '--exclude-module=scipy',
        '--exclude-module=cv2',
        '--exclude-module=torch',
        '--exclude-module=tensorflow',
    ]
    
    # 检查图标文件是否存在
    icon_path = current_dir / "icon.ico"
    if not icon_path.exists():
        # 如果没有图标文件，移除图标参数
        build_args = [arg for arg in build_args if not arg.startswith('--icon=')]
    
    # 检查配置文件是否存在
    config_path = current_dir / "screenshot_config.json"
    if not config_path.exists():
        # 如果没有配置文件，移除配置文件参数
        build_args = [arg for arg in build_args if not arg.startswith('--add-data=screenshot_config.json')]
    
    print("开始构建截图工具...")
    print(f"主程序文件: {main_script}")
    print(f"构建参数: {' '.join(build_args)}")
    
    try:
        # 执行构建
        PyInstaller.__main__.run(build_args)
        print("\n✅ 构建成功！")
        print(f"输出文件: {current_dir / 'dist' / 'ScreenshotTool.exe'}")
        
        # 显示文件信息
        exe_path = current_dir / 'dist' / 'ScreenshotTool.exe'
        if exe_path.exists():
            file_size = exe_path.stat().st_size / (1024 * 1024)  # MB
            print(f"文件大小: {file_size:.2f} MB")
        
    except Exception as e:
        print(f"❌ 构建失败: {e}")
        return False
    
    return True

def create_spec_file():
    """创建自定义的spec文件"""
    spec_content = '''
# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['screenshot_gui.py'],
    pathex=[],
    binaries=[],
    datas=[('screenshot_config.json', '.'), ],
    hiddenimports=[
        'PIL',
        'PIL.Image',
        'PIL.ImageTk', 
        'PIL.ImageGrab',
        'PIL.ImageDraw',
        'pyperclip',
        'keyboard',
        'pystray',
        'pystray._base',
        'pystray._win32',
        'tkinter',
        'tkinter.ttk',
        'tkinter.filedialog',
        'tkinter.messagebox',
        'json',
        'threading',
        'pathlib',
        'datetime',
        'ctypes',
        'ctypes.wintypes',
        'win32gui',
        'win32ui', 
        'win32con',
        'subprocess',
        'screenshot_tool_new',
        'sys',
        'os',
        'traceback'
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'matplotlib',
        'numpy', 
        'pandas',
        'scipy',
        'cv2',
        'torch',
        'tensorflow'
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='ScreenshotTool',
    debug=False,
    bootloader_ignore_signals=False,
    strip=True,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='icon.ico'
)
'''
    
    spec_path = Path(__file__).parent / "screenshot_tool.spec"
    try:
        with open(spec_path, 'w', encoding='utf-8') as f:
            f.write(spec_content)
        print(f"✅ 已创建spec文件: {spec_path}")
        return True
    except Exception as e:
        print(f"❌ 创建spec文件失败: {e}")
        return False

def clean_build_files():
    """清理构建文件"""
    current_dir = Path(__file__).parent
    
    # 要清理的目录和文件
    clean_items = [
        current_dir / "build",
        current_dir / "__pycache__",
        current_dir / "screenshot_tool.spec",
        current_dir / "screenshot_tool_new.spec"
    ]
    
    for item in clean_items:
        if item.exists():
            if item.is_dir():
                import shutil
                shutil.rmtree(item)
                print(f"🧹 已清理目录: {item}")
            else:
                item.unlink()
                print(f"🧹 已清理文件: {item}")

def install_dependencies():
    """安装必要的依赖"""
    dependencies = [
        'Pillow',
        'pyperclip', 
        'keyboard',
        'pystray',
        'PyInstaller'
    ]
    
    print("检查并安装依赖...")
    for dep in dependencies:
        try:
            __import__(dep.lower().replace('-', '_'))
            print(f"✅ {dep} 已安装")
        except ImportError:
            print(f"📦 安装 {dep}...")
            os.system(f"pip install {dep}")

def main():
    """主函数"""
    print("🚀 截图工具构建脚本")
    print("=" * 50)
    
    # 检查当前目录
    current_dir = Path(__file__).parent
    main_script = current_dir / "screenshot_gui.py"
    backend_script = current_dir / "screenshot_tool_new.py"
    
    if not main_script.exists():
        print(f"❌ 找不到主程序文件: {main_script}")
        return
        
    if not backend_script.exists():
        print(f"❌ 找不到后端模块文件: {backend_script}")
        return
    
    # 菜单选项
    while True:
        print("\n请选择操作:")
        print("1. 安装依赖")
        print("2. 构建可执行文件")
        print("3. 创建spec文件")
        print("4. 清理构建文件")
        print("5. 全部执行 (安装依赖 + 构建)")
        print("0. 退出")
        
        choice = input("\n请输入选项 (0-5): ").strip()
        
        if choice == "0":
            break
        elif choice == "1":
            install_dependencies()
        elif choice == "2":
            build_screenshot_tool()
        elif choice == "3":
            create_spec_file()
        elif choice == "4":
            clean_build_files()
        elif choice == "5":
            install_dependencies()
            if build_screenshot_tool():
                print("\n🎉 截图工具构建完成!")
                print(f"可执行文件位置: {current_dir / 'dist' / 'ScreenshotTool.exe'}")
        else:
            print("无效选项，请重新选择")

if __name__ == "__main__":
    main()