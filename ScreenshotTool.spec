# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['G:\\u2dProject\\u6project\\VESPERIX\\scripts\\screenshot-tool\\screenshot_gui.py'],
    pathex=[],
    binaries=[],
    datas=[('screenshot_config.json', '.')],
    hiddenimports=['PIL', 'PIL.Image', 'PIL.ImageTk', 'PIL.ImageGrab', 'PIL.ImageDraw', 'pyperclip', 'keyboard', 'pystray', 'pystray._base', 'pystray._win32', 'tkinter', 'tkinter.ttk', 'tkinter.filedialog', 'tkinter.messagebox', 'json', 'threading', 'pathlib', 'datetime', 'ctypes', 'ctypes.wintypes', 'win32gui', 'win32ui', 'win32con', 'subprocess', 'screenshot_tool_new', 'sys', 'os', 'traceback'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['matplotlib', 'numpy', 'pandas', 'scipy', 'cv2', 'torch', 'tensorflow'],
    noarchive=False,
    optimize=2,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [('O', None, 'OPTION'), ('O', None, 'OPTION')],
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
)
