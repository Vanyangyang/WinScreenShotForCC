#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简化版截图工具 - 专注核心功能
功能：选区截图、自动保存到指定位置、路径自动添加到剪贴板
"""

import os
import sys
import json
import time
import threading
from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

# 第三方库
try:
    from PIL import Image, ImageGrab, ImageTk
    import pyperclip
    import keyboard
    import pystray
    from pystray import MenuItem as item
except ImportError as e:
    print(f"缺少必要的依赖库: {e}")
    print("请运行: pip install Pillow pyperclip keyboard pystray")
    sys.exit(1)

# Windows API for multi-monitor support
if sys.platform == "win32":
    try:
        import ctypes
        from ctypes import wintypes
        user32 = ctypes.windll.user32
        gdi32 = ctypes.windll.gdi32
        
        # 常量定义
        SM_CMONITORS = 80
        SM_CXVIRTUALSCREEN = 78
        SM_CYVIRTUALSCREEN = 79
        SM_XVIRTUALSCREEN = 76
        SM_YVIRTUALSCREEN = 77
        
        # 监视器信息结构
        class RECT(ctypes.Structure):
            _fields_ = [("left", ctypes.c_long),
                       ("top", ctypes.c_long),
                       ("right", ctypes.c_long),
                       ("bottom", ctypes.c_long)]
        
        class MONITORINFO(ctypes.Structure):
            _fields_ = [("cbSize", wintypes.DWORD),
                       ("rcMonitor", RECT),
                       ("rcWork", RECT),
                       ("dwFlags", wintypes.DWORD)]
        
        MONITOR_DEFAULTTOPRIMARY = 0x00000001
        MONITORINFOF_PRIMARY = 0x00000001
        
    except ImportError:
        print("警告: 无法导入Windows API，多屏幕功能可能不可用")
        user32 = None
else:
    user32 = None

class ScreenshotConfig:
    """配置管理"""
    def __init__(self):
        self.config_file = "screenshot_config.json"
        # 尝试检测项目根目录
        project_screenshots_dir = self.detect_project_root()
        
        self.default_config = {
            "save_directory": project_screenshots_dir,
            "file_prefix": "screenshot_",
            "hotkey": "ctrl+shift+s",
            "auto_copy_path": True,
            "show_preview": True,
            "quality_preset": "low",  # low, medium, high
            "show_success_popup": False,
            "screenshot_mode": "auto",
            "custom_prefix": "read image: "  # 自定义前缀，默认为"read image: "
        }
        self.config = self.load_config()
    
    def detect_project_root(self):
        """检测项目根目录"""
        try:
            # 获取当前脚本所在目录的上级目录
            current_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(os.path.dirname(current_dir))  # 上两级目录
            
            # 检查是否是VESPERIX项目根目录
            vesperix_indicators = ["Assets", "scripts", "CLAUDE.md", ".mcp.json"]
            found_indicators = sum(1 for indicator in vesperix_indicators 
                                 if os.path.exists(os.path.join(project_root, indicator)))
            
            if found_indicators >= 2:
                # 找到项目根目录，返回screenshots子目录
                screenshots_dir = os.path.join(project_root, "screenshots")
                print(f"检测到VESPERIX项目根目录，设置截图目录为: {screenshots_dir}")
                return screenshots_dir
            else:
                # 未找到项目根目录，使用用户主目录
                fallback_dir = str(Path.home() / "Screenshots")
                print(f"未检测到项目根目录，使用默认目录: {fallback_dir}")
                return fallback_dir
                
        except Exception as e:
            print(f"检测项目根目录失败: {e}")
            return str(Path.home() / "Screenshots")
    
    def load_config(self):
        """加载配置"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                # 合并默认配置
                for key, value in self.default_config.items():
                    if key not in config:
                        config[key] = value
                return config
            return self.default_config.copy()
        except Exception as e:
            print(f"加载配置失败: {e}")
            return self.default_config.copy()
    
    def save_config(self):
        """保存配置"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=4, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"保存配置失败: {e}")
            return False
    
    def get(self, key, default=None):
        """获取配置项"""
        return self.config.get(key, default)
    
    def set(self, key, value):
        """设置配置项"""
        self.config[key] = value

class ScreenshotTool:
    """截图工具核心类"""
    def __init__(self, config):
        self.config = config
        self.screenshot_window = None
        self.selection_canvas = None
        self.start_x = 0
        self.start_y = 0
        self.end_x = 0
        self.end_y = 0
        self.selecting = False
        self.screenshot_img = None
        self.monitors = []
        self.current_monitor = 0
        self.virtual_screen_rect = None
        self.was_minimized = False  # 记录窗口是否被最小化
        
        # 初始化多屏幕信息
        self.detect_monitors()
        
    def detect_monitors(self):
        """检测多显示器配置"""
        self.monitors = []
        
        if sys.platform == "win32" and user32:
            try:
                # 获取监视器数量
                monitor_count = user32.GetSystemMetrics(SM_CMONITORS)
                print(f"检测到 {monitor_count} 个显示器")
                
                # 获取虚拟屏幕信息
                virtual_left = user32.GetSystemMetrics(SM_XVIRTUALSCREEN)
                virtual_top = user32.GetSystemMetrics(SM_YVIRTUALSCREEN)
                virtual_width = user32.GetSystemMetrics(SM_CXVIRTUALSCREEN)
                virtual_height = user32.GetSystemMetrics(SM_CYVIRTUALSCREEN)
                
                self.virtual_screen_rect = {
                    'left': virtual_left,
                    'top': virtual_top,
                    'width': virtual_width,
                    'height': virtual_height
                }
                
                print(f"虚拟屏幕: {virtual_left},{virtual_top} - {virtual_width}x{virtual_height}")
                
                # 枚举所有监视器
                def enum_monitors_proc(hMonitor, hdcMonitor, lprcMonitor, dwData):
                    try:
                        monitor_info = MONITORINFO()
                        monitor_info.cbSize = ctypes.sizeof(MONITORINFO)
                        
                        if user32.GetMonitorInfoW(hMonitor, ctypes.byref(monitor_info)):
                            rect = monitor_info.rcMonitor
                            work_rect = monitor_info.rcWork
                            is_primary = (monitor_info.dwFlags & MONITORINFOF_PRIMARY) != 0
                            
                            monitor_data = {
                                'handle': hMonitor,
                                'left': rect.left,
                                'top': rect.top,
                                'right': rect.right,
                                'bottom': rect.bottom,
                                'width': rect.right - rect.left,
                                'height': rect.bottom - rect.top,
                                'work_left': work_rect.left,
                                'work_top': work_rect.top,
                                'work_right': work_rect.right,
                                'work_bottom': work_rect.bottom,
                                'is_primary': is_primary,
                                'name': f"显示器 {len(self.monitors) + 1}" + (" (主显示器)" if is_primary else ""),
                                'scale_factor': 1.0
                            }
                            
                            self.monitors.append(monitor_data)
                            print(f"监视器 {len(self.monitors)}: {monitor_data['name']} - {monitor_data['width']}x{monitor_data['height']} at ({monitor_data['left']},{monitor_data['top']})")
                        else:
                            print(f"获取监视器信息失败: {hMonitor}")
                    except Exception as e:
                        print(f"枚举监视器回调异常: {e}")
                    
                    return True
                
                # 定义回调函数类型
                MONITORENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HMONITOR, wintypes.HDC, ctypes.POINTER(RECT), wintypes.LPARAM)
                
                # 枚举所有监视器
                print("开始枚举显示器...")
                result = user32.EnumDisplayMonitors(None, None, MONITORENUMPROC(enum_monitors_proc), 0)
                print(f"枚举结果: {result}, 找到 {len(self.monitors)} 个显示器")
                
                # 按主显示器排序
                self.monitors.sort(key=lambda x: (not x['is_primary'], x['left'], x['top']))
                
            except Exception as e:
                print(f"检测监视器失败: {e}")
                # 使用默认单屏幕配置
                self.monitors = [{
                    'handle': None,
                    'left': 0,
                    'top': 0,
                    'right': 1920,
                    'bottom': 1080,
                    'width': 1920,
                    'height': 1080,
                    'work_left': 0,
                    'work_top': 0,
                    'work_right': 1920,
                    'work_bottom': 1080,
                    'is_primary': True,
                    'name': "主显示器",
                    'scale_factor': 1.0
                }]
        else:
            # 非Windows系统或API不可用，使用默认配置
            root = tk.Tk()
            root.withdraw()
            screen_width = root.winfo_screenwidth()
            screen_height = root.winfo_screenheight()
            root.destroy()
            
            self.monitors = [{
                'handle': None,
                'left': 0,
                'top': 0,
                'right': screen_width,
                'bottom': screen_height,
                'width': screen_width,
                'height': screen_height,
                'work_left': 0,
                'work_top': 0,
                'work_right': screen_width,
                'work_bottom': screen_height,
                'is_primary': True,
                'name': "主显示器",
                'scale_factor': 1.0
            }]
        
        if not self.monitors:
            print("警告: 未检测到任何显示器，使用默认配置")
            self.monitors = [{
                'handle': None,
                'left': 0,
                'top': 0,
                'right': 1920,
                'bottom': 1080,
                'width': 1920,
                'height': 1080,
                'work_left': 0,
                'work_top': 0,
                'work_right': 1920,
                'work_bottom': 1080,
                'is_primary': True,
                'name': "主显示器",
                'scale_factor': 1.0
            }]
    
    def get_monitor_names(self):
        """获取所有监视器名称列表"""
        return [monitor['name'] for monitor in self.monitors]
    
    def get_virtual_screen_bounds(self):
        """获取虚拟屏幕边界信息"""
        if not self.virtual_screen_rect:
            # 如果没有虚拟屏幕信息，使用截图尺寸
            self.virtual_screen_rect = {
                'left': 0,
                'top': 0,
                'width': self.screenshot_img.width if hasattr(self, 'screenshot_img') else 1920,
                'height': self.screenshot_img.height if hasattr(self, 'screenshot_img') else 1080
            }
        return self.virtual_screen_rect
    
    def capture_all_screens(self):
        """截取所有屏幕 - 使用Windows API"""
        try:
            if sys.platform == "win32":
                try:
                    # 动态导入pywin32模块
                    import win32gui
                    import win32ui
                    import win32con
                    
                    # 获取虚拟屏幕尺寸
                    virtual_left = user32.GetSystemMetrics(SM_XVIRTUALSCREEN)
                    virtual_top = user32.GetSystemMetrics(SM_YVIRTUALSCREEN)
                    virtual_width = user32.GetSystemMetrics(SM_CXVIRTUALSCREEN)
                    virtual_height = user32.GetSystemMetrics(SM_CYVIRTUALSCREEN)
                    
                    print(f"虚拟屏幕: ({virtual_left}, {virtual_top}) - {virtual_width}x{virtual_height}")
                    
                    # 获取桌面设备上下文
                    hdesktop = win32gui.GetDesktopWindow()
                    desktop_dc = win32gui.GetWindowDC(hdesktop)
                    img_dc = win32ui.CreateDCFromHandle(desktop_dc)
                    
                    # 创建内存设备上下文
                    mem_dc = img_dc.CreateCompatibleDC()
                    
                    # 创建位图
                    screenshot = win32ui.CreateBitmap()
                    screenshot.CreateCompatibleBitmap(img_dc, virtual_width, virtual_height)
                    mem_dc.SelectObject(screenshot)
                    
                    # 复制屏幕内容
                    mem_dc.BitBlt((0, 0), (virtual_width, virtual_height), 
                                 img_dc, (virtual_left, virtual_top), win32con.SRCCOPY)
                    
                    # 转换为PIL图像
                    bmpinfo = screenshot.GetInfo()
                    bmpstr = screenshot.GetBitmapBits(True)
                    
                    img = Image.frombuffer(
                        'RGB',
                        (bmpinfo['bmWidth'], bmpinfo['bmHeight']),
                        bmpstr, 'raw', 'BGRX', 0, 1)
                    
                    # 清理资源
                    mem_dc.DeleteDC()
                    win32gui.DeleteObject(screenshot.GetHandle())
                    win32gui.ReleaseDC(hdesktop, desktop_dc)
                    
                    return img, (virtual_left, virtual_top)
                except ImportError:
                    print("pywin32未安装，使用PIL方法")
                    return ImageGrab.grab(), (0, 0)
            else:
                # 非Windows系统
                return ImageGrab.grab(), (0, 0)
        except Exception as e:
            print(f"Windows API 截图失败: {e}")
            return ImageGrab.grab(), (0, 0)
    
    def capture_monitor(self, monitor_info):
        """截取特定显示器"""
        try:
            if sys.platform == "win32":
                try:
                    # 动态导入pywin32模块
                    import win32gui
                    import win32ui
                    import win32con
                    
                    left = monitor_info['left']
                    top = monitor_info['top']
                    width = monitor_info['width']
                    height = monitor_info['height']
                    
                    hdesktop = win32gui.GetDesktopWindow()
                    desktop_dc = win32gui.GetWindowDC(hdesktop)
                    img_dc = win32ui.CreateDCFromHandle(desktop_dc)
                    mem_dc = img_dc.CreateCompatibleDC()
                    
                    screenshot = win32ui.CreateBitmap()
                    screenshot.CreateCompatibleBitmap(img_dc, width, height)
                    mem_dc.SelectObject(screenshot)
                    
                    mem_dc.BitBlt((0, 0), (width, height), 
                                 img_dc, (left, top), win32con.SRCCOPY)
                    
                    bmpinfo = screenshot.GetInfo()
                    bmpstr = screenshot.GetBitmapBits(True)
                    
                    img = Image.frombuffer(
                        'RGB',
                        (bmpinfo['bmWidth'], bmpinfo['bmHeight']),
                        bmpstr, 'raw', 'BGRX', 0, 1)
                    
                    mem_dc.DeleteDC()
                    win32gui.DeleteObject(screenshot.GetHandle())
                    win32gui.ReleaseDC(hdesktop, desktop_dc)
                    
                    return img
                except ImportError:
                    # pywin32未安装，使用PIL方法
                    bbox = (monitor_info['left'], monitor_info['top'], 
                           monitor_info['right'], monitor_info['bottom'])
                    return ImageGrab.grab(bbox)
            else:
                # 非Windows系统
                bbox = (monitor_info['left'], monitor_info['top'], 
                       monitor_info['right'], monitor_info['bottom'])
                return ImageGrab.grab(bbox)
        except Exception as e:
            print(f"显示器截图失败: {e}")
            bbox = (monitor_info['left'], monitor_info['top'], 
                   monitor_info['right'], monitor_info['bottom'])
            return ImageGrab.grab(bbox)
    
    def get_mouse_monitor(self):
        """获取鼠标当前所在的显示器"""
        if not user32:
            print("无Windows API支持，返回默认显示器")
            return 0
        
        try:
            # 获取鼠标位置
            cursor_pos = wintypes.POINT()
            success = user32.GetCursorPos(ctypes.byref(cursor_pos))
            
            if not success:
                print("获取鼠标位置失败")
                return 0
            
            print(f"=== 鼠标位置检测 ===")
            print(f"鼠标位置: ({cursor_pos.x}, {cursor_pos.y})")
            
            # 检查鼠标在哪个显示器上
            for i, monitor in enumerate(self.monitors):
                print(f"检查显示器{i+1}: 范围({monitor['left']}, {monitor['top']}) - ({monitor['right']}, {monitor['bottom']})")
                if (monitor['left'] <= cursor_pos.x < monitor['right'] and 
                    monitor['top'] <= cursor_pos.y < monitor['bottom']):
                    print(f"✓ 鼠标在显示器{i+1}: {monitor['name']}")
                    return i
            
            print("鼠标不在任何检测到的显示器上，使用主显示器")
            
            # 如果没有找到，返回主显示器
            for i, monitor in enumerate(self.monitors):
                if monitor['is_primary']:
                    print(f"使用主显示器: {monitor['name']}")
                    return i
            
            print("使用默认显示器(索引 0)")
            return 0
        except Exception as e:
            print(f"获取鼠标显示器失败: {e}")
            import traceback
            traceback.print_exc()
            return 0
    
    def ensure_save_directory(self):
        """确保保存目录存在"""
        save_dir = Path(self.config.get("save_directory"))
        save_dir.mkdir(parents=True, exist_ok=True)
        return save_dir
    
    def generate_filename(self):
        """生成文件名"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        prefix = self.config.get("file_prefix", "screenshot_")
        return f"{prefix}{timestamp}.png"
    
    def start_area_screenshot(self, monitor_index=None, screenshot_mode='auto'):
        """开始选区截图
        Args:
            monitor_index: 显示器索引（可选）
            screenshot_mode: 截图模式 - 'auto'（自动适应）, 'mouse'（鼠标所在屏幕）, 'all'（所有屏幕）
        """
        # 记录当前截图模式
        self.current_screenshot_mode = screenshot_mode
        self.virtual_offset = (0, 0)
        
        # 重新检测显示器以确保最新配置
        self.detect_monitors()
        
        # 检查并隐藏主窗口
        if hasattr(self, 'main_window') and self.main_window:
            # 记录窗口是否已经最小化（图标化）
            try:
                self.was_minimized = self.main_window.winfo_viewable() == 0 or self.main_window.state() == 'iconic'
                print(f"窗口最小化状态: {self.was_minimized}")
            except:
                self.was_minimized = False
            self.main_window.withdraw()
        
        print(f"=== 开始截图 (模式: {screenshot_mode}) ===")
        
        # 根据模式截图
        if screenshot_mode == 'mouse' and len(self.monitors) > 1:
            # 鼠标所在屏幕
            monitor_idx = self.get_mouse_monitor()
            if monitor_idx < len(self.monitors):
                monitor = self.monitors[monitor_idx]
                self.screenshot_img = self.capture_monitor(monitor)
                self.virtual_offset = (monitor['left'], monitor['top'])
                print(f"截取鼠标所在屏幕: {monitor['name']}")
            else:
                # 回退到全屏
                self.screenshot_img, self.virtual_offset = self.capture_all_screens()
        else:
            # 所有屏幕
            self.screenshot_img, self.virtual_offset = self.capture_all_screens()
        
        # 输出截图信息
        print(f"截图尺寸: {self.screenshot_img.width}x{self.screenshot_img.height}")
        print(f"虚拟偏移: {self.virtual_offset}")
        
        # 获取虚拟屏幕范围
        self.get_virtual_screen_bounds()
        
        # 输出显示器信息
        if len(self.monitors) > 1:
            print(f"检测到 {len(self.monitors)} 个显示器:")
            for i, monitor in enumerate(self.monitors):
                print(f"  显示器{i+1}: {monitor['width']}x{monitor['height']} at ({monitor['left']},{monitor['top']})")
        
        # 输出虚拟屏幕信息
        if self.virtual_screen_rect:
            print(f"虚拟屏幕: {self.virtual_screen_rect['width']}x{self.virtual_screen_rect['height']} at ({self.virtual_screen_rect['left']},{self.virtual_screen_rect['top']})")
        
        # 创建选择窗口
        self.create_selection_window()
    
    def start_full_screen_screenshot(self, monitor_index=0):
        """截取整个屏幕（指定监视器）"""
        try:
            # 隐藏主窗口
            if hasattr(self, 'main_window'):
                self.main_window.withdraw()
            
            monitor = self.monitors[monitor_index]
            bbox = (monitor['left'], monitor['top'], monitor['right'], monitor['bottom'])
            screenshot_img = ImageGrab.grab(bbox)
            
            # 保存截图
            self.save_screenshot(screenshot_img)
            
            # 恢复主窗口
            if hasattr(self, 'main_window') and self.main_window:
                try:
                    self.main_window.deiconify()
                except:
                    pass
                    
        except Exception as e:
            print(f"全屏截图失败: {e}")
            if hasattr(self, 'main_window') and self.main_window:
                try:
                    self.main_window.deiconify()
                except:
                    pass
    
    def create_selection_window(self):
        """创建选择窗口"""
        # 确保先销毁旧窗口
        if self.screenshot_window:
            try:
                self.screenshot_window.destroy()
            except:
                pass
        
        self.screenshot_window = tk.Toplevel()
        self.screenshot_window.title("选择截图区域")
        
        print(f"=== 创建选择窗口 ===")
        print(f"截图尺寸: {self.screenshot_img.width}x{self.screenshot_img.height}")
        print(f"虚拟偏移: {self.virtual_offset}")
        
        # 强制覆盖整个虚拟屏幕空间
        # 禁用窗口管理器
        self.screenshot_window.overrideredirect(True)
        self.screenshot_window.attributes('-topmost', True)
        self.screenshot_window.configure(cursor="crosshair", bg='black')
        
        # 获取虚拟屏幕的完整范围
        if self.virtual_screen_rect:
            virtual_left = self.virtual_screen_rect['left']
            virtual_top = self.virtual_screen_rect['top'] 
            virtual_width = self.virtual_screen_rect['width']
            virtual_height = self.virtual_screen_rect['height']
        else:
            # 后备方案
            virtual_left = 0
            virtual_top = 0
            virtual_width = self.screenshot_img.width
            virtual_height = self.screenshot_img.height
        
        print(f"=== 虚拟屏幕信息 ===")
        print(f"虚拟屏幕范围: ({virtual_left}, {virtual_top}) {virtual_width}x{virtual_height}")
        
        # 设置窗口的准确位置和大小以覆盖整个虚拟屏幕
        geometry_str = f"{virtual_width}x{virtual_height}+{virtual_left}+{virtual_top}"
        print(f"窗口几何信息: {geometry_str}")
        self.screenshot_window.geometry(geometry_str)
        
        # 获取窗口尺寸（使用虚拟屏幕尺寸）
        window_width = virtual_width
        window_height = virtual_height
        window_x = virtual_left
        window_y = virtual_top
        
        # 创建画布（覆盖整个窗口）
        self.selection_canvas = tk.Canvas(
            self.screenshot_window,
            width=window_width,
            height=window_height,
            highlightthickness=0,
            bg='black'
        )
        self.selection_canvas.pack(fill=tk.BOTH, expand=True)
        
        # 强制更新和显示窗口
        self.screenshot_window.update_idletasks()
        self.screenshot_window.update()
        
        # 确保窗口在所有屏幕上可见
        self.screenshot_window.lift()
        self.screenshot_window.attributes('-topmost', True)
        
        # 保存窗口尺寸信息
        self.canvas_width = window_width
        self.canvas_height = window_height
        
        print(f"画布尺寸: {self.canvas_width}x{self.canvas_height}")
        print(f"截图尺寸: {self.screenshot_img.width}x{self.screenshot_img.height}")
        
        # 创建图片对象
        self.bg_photo = ImageTk.PhotoImage(self.screenshot_img)
        
        # 计算图片在画布中的正确位置
        # 重要：窗口覆盖虚拟屏幕，图片也是虚拟屏幕的截图
        # 但它们的原点可能不同
        
        print(f"窗口范围: ({window_x}, {window_y}) 到 ({window_x + window_width}, {window_y + window_height})")
        print(f"虚拟偏移: {self.virtual_offset}")
        
        # 图片在画布中的位置计算
        # 因为窗口覆盖整个虚拟屏幕，图片应该直接放在(0,0)位置
        img_x = 0
        img_y = 0
        
        print(f"图片在画布中的位置: ({img_x}, {img_y})")
        self.selection_canvas.create_image(img_x, img_y, anchor=tk.NW, image=self.bg_photo)
        
        # 添加轻微半透明遮罩
        self.selection_canvas.create_rectangle(0, 0, window_width, window_height, 
                                             fill='black', stipple='gray25', outline='', tags='overlay')
        
        # 保存窗口尺寸信息，供坐标转换使用
        self.canvas_width = self.screenshot_img.width
        self.canvas_height = self.screenshot_img.height
        
        # 绑定事件
        self.selection_canvas.bind('<Button-1>', self.on_mouse_press)
        self.selection_canvas.bind('<B1-Motion>', self.on_mouse_drag)
        self.selection_canvas.bind('<ButtonRelease-1>', self.on_mouse_release)
        
        # ESC键绑定 - 多重绑定确保有效
        self.screenshot_window.bind('<Escape>', self.cancel_screenshot)
        self.screenshot_window.bind('<KeyPress-Escape>', self.cancel_screenshot)
        self.selection_canvas.bind('<Escape>', self.cancel_screenshot)
        self.selection_canvas.bind('<KeyPress-Escape>', self.cancel_screenshot)
        
        # 绑定所有可能的键盘事件
        self.screenshot_window.bind('<Key>', self.on_key_press)
        self.selection_canvas.bind('<Key>', self.on_key_press)
        
        # 设置焦点
        self.screenshot_window.focus_set()
        self.screenshot_window.focus_force()
        self.selection_canvas.focus_set()
        
        # 使窗口能接收键盘事件
        self.screenshot_window.config(takefocus=True)
        self.selection_canvas.config(takefocus=True)
        
        # 尝试独占输入（可能因为overrideredirect失效）
        try:
            self.screenshot_window.grab_set()
        except:
            print("警告: 无法设置输入独占")
        
        # 显示提示
        self.show_instruction()
        
        # 最终确保窗口正确显示在所有屏幕
        self.screenshot_window.after(50, self.final_window_setup)
    
    def final_window_setup(self):
        """最终窗口设置确保"""
        try:
            # 再次确认窗口几何信息
            if self.virtual_screen_rect:
                virtual_left = self.virtual_screen_rect['left']
                virtual_top = self.virtual_screen_rect['top'] 
                virtual_width = self.virtual_screen_rect['width']
                virtual_height = self.virtual_screen_rect['height']
                geometry_str = f"{virtual_width}x{virtual_height}+{virtual_left}+{virtual_top}"
                self.screenshot_window.geometry(geometry_str)
            
            # 强制提升到最前和获得焦点
            self.screenshot_window.lift()
            self.screenshot_window.attributes('-topmost', True)
            self.screenshot_window.focus_force()
            self.selection_canvas.focus_set()
            
            print("=== 最终窗口设置完成 ===")
            
        except Exception as e:
            print(f"最终窗口设置失败: {e}")
    
    def on_key_press(self, event):
        """处理所有键盘按键"""
        print(f"键盘事件: {event.keysym}, keycode: {event.keycode}")
        if event.keysym == 'Escape':
            self.cancel_screenshot(event)
    
    def show_instruction(self):
        """显示操作提示"""
        try:
            canvas_width = self.screenshot_window.winfo_width()
        except:
            canvas_width = 1920
        
        instruction_text = "拖拽选择截图区域，按 ESC 取消"
        if len(self.monitors) > 1:
            instruction_text = f"拖拽选择截图区域，按 ESC 取消\n多屏幕模式: 自动覆盖所有屏幕"
        
        instruction = self.selection_canvas.create_text(
            canvas_width // 2,
            50,
            text=instruction_text,
            font=("Arial", 16),
            fill="white",
            tags="instruction"
        )
    
    def on_mouse_press(self, event):
        """鼠标按下事件"""
        self.start_x = event.x
        self.start_y = event.y
        self.selecting = True
        
        # 清除之前的选择框
        self.selection_canvas.delete("selection")
        self.selection_canvas.delete("instruction")
    
    def on_mouse_drag(self, event):
        """鼠标拖拽事件"""
        if self.selecting:
            self.end_x = event.x
            self.end_y = event.y
            
            # 清除之前的选择框
            self.selection_canvas.delete("selection")
            
            # 绘制选择框
            self.selection_canvas.create_rectangle(
                self.start_x, self.start_y, self.end_x, self.end_y,
                outline="red", width=2, tags="selection"
            )
            
            # 显示尺寸信息
            width = abs(self.end_x - self.start_x)
            height = abs(self.end_y - self.start_y)
            size_text = f"{width} x {height}"
            
            self.selection_canvas.create_text(
                self.end_x, self.end_y - 20,
                text=size_text,
                font=("Arial", 12),
                fill="red",
                tags="selection"
            )
    
    def on_mouse_release(self, event):
        """鼠标释放事件"""
        if self.selecting:
            self.selecting = False
            self.end_x = event.x
            self.end_y = event.y
            
            # 确保坐标正确
            x1 = min(self.start_x, self.end_x)
            y1 = min(self.start_y, self.end_y)
            x2 = max(self.start_x, self.end_x)
            y2 = max(self.start_y, self.end_y)
            
            if x2 - x1 > 10 and y2 - y1 > 10:  # 最小选择区域
                self.capture_selected_area(x1, y1, x2, y2)
            else:
                self.cancel_screenshot()
    
    def capture_selected_area(self, x1, y1, x2, y2):
        """截取选定区域"""
        try:
            print(f"=== 开始截取选定区域 ===")
            print(f"选择区域: ({x1}, {y1}) - ({x2}, {y2})")
            print(f"虚拟偏移: {self.virtual_offset}")
            print(f"截图尺寸: {self.screenshot_img.width}x{self.screenshot_img.height}")
            
            # 关闭选择窗口
            try:
                self.screenshot_window.grab_release()  # 释放输入独占
                self.screenshot_window.destroy()
            except:
                pass
            self.screenshot_window = None
            
            # 调整坐标到图像坐标系
            # 画布坐标已经包含了虚拟偏移，需要还原
            img_x1 = x1
            img_y1 = y1
            img_x2 = x2
            img_y2 = y2
            
            print(f"图像坐标: ({img_x1}, {img_y1}) - ({img_x2}, {img_y2})")
            
            # 确保坐标在有效范围内
            img_x1 = max(0, min(img_x1, self.screenshot_img.width - 1))
            img_y1 = max(0, min(img_y1, self.screenshot_img.height - 1))
            img_x2 = max(0, min(img_x2, self.screenshot_img.width))
            img_y2 = max(0, min(img_y2, self.screenshot_img.height))
            
            # 确保区域有效
            if img_x2 <= img_x1 or img_y2 <= img_y1:
                print(f"无效的选择区域: ({img_x1}, {img_y1}) - ({img_x2}, {img_y2})")
                messagebox.showerror("错误", "选择区域无效，请重新选择")
                return
            
            print(f"最终坐标: ({img_x1}, {img_y1}) - ({img_x2}, {img_y2})")
            
            # 截取区域
            cropped_img = self.screenshot_img.crop((img_x1, img_y1, img_x2, img_y2))
            print(f"截取结果: {cropped_img.width}x{cropped_img.height}")
            
            # 保存图片
            self.save_screenshot(cropped_img)
            
        except Exception as e:
            print(f"截图失败: {e}")
            import traceback
            traceback.print_exc()
            messagebox.showerror("错误", f"截图失败: {e}")
        finally:
            # 根据之前的状态决定是否恢复主窗口
            if hasattr(self, 'main_window') and self.main_window:
                try:
                    if not self.was_minimized:
                        # 只有在窗口之前不是最小化状态时才恢复显示
                        self.main_window.deiconify()
                        print("恢复主窗口显示")
                    else:
                        # 窗口之前是最小化的，保持最小化
                        self.main_window.iconify()
                        print("保持主窗口最小化")
                except:
                    pass
    
    def save_screenshot(self, img):
        """保存截图"""
        try:
            # 确保保存目录存在
            save_dir = self.ensure_save_directory()
            
            # 生成文件路径
            filename = self.generate_filename()
            filepath = save_dir / filename
            
            # 保存图片（优化压缩）
            if self.save_optimized_image(img, str(filepath)):
                # 复制路径到剪贴板（支持自定义前缀）
                if self.config.get("auto_copy_path", True):
                    self.copy_to_clipboard_with_prefix(str(filepath))
                
                # 显示成功消息（可选）
                if self.config.get("show_success_popup", False):
                    messagebox.showinfo("成功", f"截图已保存: {filename}\n路径已复制到剪贴板")
                
                # 显示预览（可选）
                if self.config.get("show_preview", True):
                    self.show_preview(img, filepath)
            else:
                messagebox.showerror("错误", "保存图片失败")
            
        except Exception as e:
            print(f"保存失败: {e}")
            messagebox.showerror("错误", f"保存失败: {e}")

    def copy_to_clipboard_with_prefix(self, filepath):
        """复制路径到剪贴板，支持自定义前缀"""
        try:
            # 获取自定义前缀
            custom_prefix = self.config.get("custom_prefix", "")

            # 构建最终的剪贴板内容
            if custom_prefix:
                # 如果有自定义前缀，添加到路径前面
                clipboard_content = custom_prefix + str(filepath)
            else:
                # 没有前缀，直接使用路径
                clipboard_content = str(filepath)

            # 复制到剪贴板
            pyperclip.copy(clipboard_content)

            print(f"已复制到剪贴板: {clipboard_content}")

        except Exception as e:
            print(f"复制到剪贴板失败: {e}")
            # 如果复制失败，尝试只复制路径
            try:
                pyperclip.copy(str(filepath))
                print(f"已复制路径到剪贴板: {filepath}")
            except:
                print("剪贴板操作完全失败")

    def save_optimized_image(self, img, filepath):
        """保存优化后的图片"""
        try:
            quality_preset = self.config.get("quality_preset", "low")
            
            # 质量预设配置 - 专注于PNG优化
            quality_settings = {
                "low": {
                    "png_compress_level": 9,     # 最大压缩（1-9）
                    "optimize": True,
                    "resize_threshold": 9999999, # 不自动缩放
                    "resize_max_width": 9999999, # 不限制宽度
                    "color_reduction": False,    # 不减少颜色
                    "quantize_colors": None      # 不使用调色板
                },
                "medium": {
                    "png_compress_level": 6,     # 中等压缩
                    "optimize": True,
                    "resize_threshold": 2560,    # 超过2560宽度才缩放
                    "resize_max_width": 2048,    # 最大宽度限制
                    "color_reduction": False,    # 不减少颜色
                    "quantize_colors": None
                },
                "high": {
                    "png_compress_level": 3,     # 轻度压缩
                    "optimize": False,           # 不优化以保持质量
                    "resize_threshold": 4096,    # 超过4K才缩放
                    "resize_max_width": 3840,    # 最大宽度限制
                    "color_reduction": False,
                    "quantize_colors": None
                }
            }
            
            settings = quality_settings.get(quality_preset, quality_settings["low"])
            
            # 根据预设进行图片优化
            width, height = img.size
            original_size = (width, height)
            
            # 尺寸优化
            if width > settings["resize_threshold"]:
                # 计算缩放比例，保持宽高比
                scale = min(settings["resize_max_width"] / width, 1.0)
                new_width = int(width * scale)
                new_height = int(height * scale)
                img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                print(f"图片缩放: {width}x{height} -> {new_width}x{new_height}")
            
            # 低质量模式不再进行二次压缩，保持原始质量
            
            # PNG保存参数
            save_kwargs = {
                "optimize": settings["optimize"],
                "compress_level": settings["png_compress_level"]
            }
            
            # 对于低质量模式，使用正常保存策略，不再特殊处理
            if quality_preset == "low":
                save_kwargs = {
                    "optimize": settings["optimize"],
                    "compress_level": settings["png_compress_level"]
                }
            
            img.save(filepath, "PNG", **save_kwargs)
            
            # 输出文件信息
            file_size = Path(filepath).stat().st_size
            size_mb = file_size / (1024 * 1024)
            size_kb = file_size / 1024
            
            if size_mb >= 1:
                size_str = f"{size_mb:.2f} MB"
            else:
                size_str = f"{size_kb:.1f} KB"
                
            print(f"保存完成 - 质量: {quality_preset}, 大小: {size_str}, 原始尺寸: {original_size}")
            
            return True
        except Exception as e:
            print(f"保存优化图片失败: {e}")
            return False
    
    def optimize_image_before_save(self, img):
        """保存前优化图片"""
        try:
            # 如果图片过大，进行适当的质量优化
            width, height = img.size
            max_dimension = 3840  # 4K分辨率
            
            if width > max_dimension or height > max_dimension:
                # 计算缩放比例
                scale = min(max_dimension / width, max_dimension / height)
                new_width = int(width * scale)
                new_height = int(height * scale)
                
                # 使用高质量重采样
                img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                print(f"图片已优化：{width}x{height} -> {new_width}x{new_height}")
            
            return img
        except Exception as e:
            print(f"图片优化失败: {e}")
            return img
    
    def show_preview(self, img, filepath):
        """显示预览窗口"""
        preview_window = tk.Toplevel()
        preview_window.title("截图预览")
        preview_window.geometry("400x300")
        
        # 调整图片大小以适应预览窗口
        img_width, img_height = img.size
        max_width, max_height = 350, 200
        
        if img_width > max_width or img_height > max_height:
            ratio = min(max_width / img_width, max_height / img_height)
            new_width = int(img_width * ratio)
            new_height = int(img_height * ratio)
            img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        # 显示图片
        photo = ImageTk.PhotoImage(img)
        label = tk.Label(preview_window, image=photo)
        label.image = photo  # 防止被垃圾回收
        label.pack(pady=10)
        
        # 显示文件信息
        try:
            file_size = Path(filepath).stat().st_size
            if file_size > 1024 * 1024:
                size_str = f"{file_size / (1024 * 1024):.1f} MB"
            elif file_size > 1024:
                size_str = f"{file_size / 1024:.1f} KB"
            else:
                size_str = f"{file_size} B"
        except:
            size_str = "Unknown"
        
        info_text = f"文件: {Path(filepath).name}\n路径: {filepath}\n尺寸: {img.size[0]} x {img.size[1]}\n大小: {size_str}"
        info_label = tk.Label(preview_window, text=info_text, justify=tk.LEFT)
        info_label.pack(pady=5)
        
        # 关闭按钮
        close_btn = tk.Button(preview_window, text="关闭", command=preview_window.destroy)
        close_btn.pack(pady=5)
    
    def cancel_screenshot(self, event=None):
        """取消截图"""
        print(f"=== ESC取消截图 ===")
        if event:
            print(f"事件类型: {event.type}, 键码: {getattr(event, 'keycode', 'N/A')}, 组件: {event.widget}")
        
        try:
            if self.screenshot_window:
                self.screenshot_window.grab_release()  # 释放输入独占
                self.screenshot_window.destroy()
                self.screenshot_window = None
                print("✓ 选择窗口已关闭")
        except Exception as e:
            print(f"✗ 关闭选择窗口失败: {e}")
        
        try:
            if hasattr(self, 'main_window') and self.main_window:
                # 根据之前的状态决定是否恢复主窗口
                if hasattr(self, 'was_minimized') and self.was_minimized:
                    # 窗口之前是最小化的，保持最小化
                    self.main_window.iconify()
                    print("✓ 主窗口保持最小化")
                else:
                    # 窗口之前不是最小化的，恢复显示
                    self.main_window.deiconify()
                    self.main_window.lift()
                    print("✓ 主窗口已恢复")
        except Exception as e:
            print(f"✗ 恢复主窗口失败: {e}")

class ScreenshotGUI:
    """截图工具GUI"""
    def __init__(self):
        self.config = ScreenshotConfig()
        self.screenshot_tool = ScreenshotTool(self.config)
        self.screenshot_tool.main_window = None  # 稍后设置
        self.tray_icon = None
        self.is_minimized_to_tray = False
        
        self.setup_gui()
        self.load_config_to_gui()
        self.setup_hotkeys()
        self.setup_system_tray()
    
    def setup_gui(self):
        """设置GUI界面"""
        self.root = tk.Tk()
        self.root.title("截图工具")
        self.root.geometry("650x750")
        self.root.resizable(True, True)
        
        # 设置主窗口引用
        self.screenshot_tool.main_window = self.root
        
        # 创建滚动框架
        canvas = tk.Canvas(self.root)
        scrollbar = ttk.Scrollbar(self.root, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # 创建主框架
        main_frame = ttk.Frame(scrollable_frame, padding="20")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 标题
        title_label = ttk.Label(main_frame, text="📷 截图工具", font=("Arial", 16, "bold"))
        title_label.grid(row=0, column=0, columnspan=2, pady=(0, 20))
        
        # 保存路径设置
        ttk.Label(main_frame, text="保存路径:").grid(row=1, column=0, sticky=tk.W, pady=5)
        
        path_frame = ttk.Frame(main_frame)
        path_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        
        self.path_var = tk.StringVar()
        self.path_entry = ttk.Entry(path_frame, textvariable=self.path_var, width=50)
        self.path_entry.grid(row=0, column=0, sticky=(tk.W, tk.E))
        
        ttk.Button(path_frame, text="浏览", command=self.browse_folder).grid(row=0, column=1, padx=(5, 0))
        
        # 文件设置
        file_frame = ttk.LabelFrame(main_frame, text="文件设置", padding="10")
        file_frame.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=10)
        
        ttk.Label(file_frame, text="文件前缀:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.prefix_var = tk.StringVar()
        ttk.Entry(file_frame, textvariable=self.prefix_var, width=20).grid(row=0, column=1, sticky=tk.W, pady=5, padx=(10, 0))
        
        ttk.Label(file_frame, text="文件格式:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.format_var = tk.StringVar()
        format_combo = ttk.Combobox(file_frame, textvariable=self.format_var, values=["png", "jpg", "bmp"], width=17)
        format_combo.grid(row=1, column=1, sticky=tk.W, pady=5, padx=(10, 0))
        format_combo.state(['readonly'])
        
        ttk.Label(file_frame, text="JPEG质量:").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.quality_var = tk.StringVar()
        quality_spinbox = tk.Spinbox(file_frame, from_=1, to=100, textvariable=self.quality_var, width=15)
        quality_spinbox.grid(row=2, column=1, sticky=tk.W, pady=5, padx=(10, 0))
        
        ttk.Label(file_frame, text="PNG压缩:").grid(row=3, column=0, sticky=tk.W, pady=5)
        self.png_compress_var = tk.StringVar()
        png_compress_spinbox = tk.Spinbox(file_frame, from_=0, to=9, textvariable=self.png_compress_var, width=15)
        png_compress_spinbox.grid(row=3, column=1, sticky=tk.W, pady=5, padx=(10, 0))
        
        # 热键设置
        hotkey_frame = ttk.LabelFrame(main_frame, text="热键设置", padding="10")
        hotkey_frame.grid(row=4, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=10)
        
        ttk.Label(hotkey_frame, text="截图热键:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.hotkey_var = tk.StringVar()
        hotkey_entry = ttk.Entry(hotkey_frame, textvariable=self.hotkey_var, width=20)
        hotkey_entry.grid(row=0, column=1, sticky=tk.W, pady=5, padx=(10, 0))
        
        # 热键测试按钮
        ttk.Button(hotkey_frame, text="测试热键", command=self.test_hotkey).grid(row=0, column=2, pady=5, padx=(10, 0))
        
        # 热键状态显示
        self.hotkey_status_var = tk.StringVar()
        self.hotkey_status_var.set("未测试")
        hotkey_status_label = ttk.Label(hotkey_frame, textvariable=self.hotkey_status_var, foreground="blue")
        hotkey_status_label.grid(row=1, column=0, columnspan=3, sticky=tk.W, pady=2)
        
        # 多显示器设置
        monitor_frame = ttk.LabelFrame(main_frame, text="显示器设置", padding="10")
        monitor_frame.grid(row=5, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=10)
        
        # 检测到的显示器信息
        monitor_info = f"检测到 {len(self.screenshot_tool.monitors)} 个显示器"
        ttk.Label(monitor_frame, text=monitor_info).grid(row=0, column=0, columnspan=3, sticky=tk.W, pady=5)
        
        # 截图模式选择
        ttk.Label(monitor_frame, text="截图模式:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.screenshot_mode_var = tk.StringVar()
        mode_options = [
            ("auto", "自动适应（所有屏幕）"),
            ("mouse", "鼠标所在屏幕"),
            ("all", "所有屏幕")
        ]
        mode_combo = ttk.Combobox(monitor_frame, textvariable=self.screenshot_mode_var, 
                                 values=[desc for _, desc in mode_options], width=20)
        mode_combo.grid(row=1, column=1, sticky=tk.W, pady=5, padx=(10, 0))
        mode_combo.state(['readonly'])
        
        # 模式说明
        mode_descriptions = {
            "auto": "自动适应：截取所有屏幕，适合多屏幕环境",
            "mouse": "鼠标模式：只截取鼠标当前所在的屏幕",
            "all": "全屏模式：截取所有显示器的内容"
        }
        self.mode_desc_var = tk.StringVar()
        mode_desc_label = ttk.Label(monitor_frame, textvariable=self.mode_desc_var, 
                                   foreground="blue", font=("Arial", 9))
        mode_desc_label.grid(row=2, column=0, columnspan=3, sticky=tk.W, pady=2)
        
        def on_mode_change(event=None):
            selected_desc = self.screenshot_mode_var.get()
            for mode_key, desc in mode_options:
                if desc == selected_desc:
                    self.mode_desc_var.set(mode_descriptions.get(mode_key, ""))
                    break
        
        mode_combo.bind('<<ComboboxSelected>>', on_mode_change)
        
        # 存储模式选项映射
        self.mode_options_map = {desc: key for key, desc in mode_options}
        self.mode_reverse_map = {key: desc for key, desc in mode_options}
        
        # 功能选项
        options_frame = ttk.LabelFrame(main_frame, text="功能选项", padding="10")
        options_frame.grid(row=5, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=10)
        
        self.auto_copy_var = tk.BooleanVar()
        ttk.Checkbutton(options_frame, text="自动复制路径到剪贴板", variable=self.auto_copy_var).grid(row=0, column=0, sticky=tk.W, pady=2)
        
        self.show_preview_var = tk.BooleanVar()
        ttk.Checkbutton(options_frame, text="显示预览窗口", variable=self.show_preview_var).grid(row=1, column=0, sticky=tk.W, pady=2)
        
        self.optimize_image_var = tk.BooleanVar()
        ttk.Checkbutton(options_frame, text="优化图片大小", variable=self.optimize_image_var).grid(row=2, column=0, sticky=tk.W, pady=2)
        
        self.show_success_popup_var = tk.BooleanVar()
        ttk.Checkbutton(options_frame, text="显示成功弹窗", variable=self.show_success_popup_var).grid(row=3, column=0, sticky=tk.W, pady=2)
        
        # 按钮区域
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=6, column=0, columnspan=2, pady=20)
        
        # 第一行按钮
        ttk.Button(button_frame, text="开始截图", command=self.start_screenshot).grid(row=0, column=0, padx=5, pady=5)
        ttk.Button(button_frame, text="保存配置", command=self.save_config).grid(row=0, column=1, padx=5, pady=5)
        ttk.Button(button_frame, text="重新加载配置", command=self.reload_config).grid(row=0, column=2, padx=5, pady=5)
        
        # 第二行按钮
        ttk.Button(button_frame, text="打开保存文件夹", command=self.open_save_folder).grid(row=1, column=0, padx=5, pady=5)
        ttk.Button(button_frame, text="重置为默认", command=self.reset_to_default).grid(row=1, column=1, padx=5, pady=5)
        ttk.Button(button_frame, text="隐藏到托盘", command=self.hide_window).grid(row=1, column=2, padx=5, pady=5)
        
        # 使用说明
        help_frame = ttk.LabelFrame(main_frame, text="使用说明", padding="10")
        help_frame.grid(row=7, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=10)
        
        help_text = """📷 点击"开始截图"或使用热键开始截图
🖱️ 拖拽选择截图区域
💾 截图自动保存到指定文件夹
📋 文件路径自动复制到剪贴板
⌨️ 按 ESC 取消截图
🔧 修改任何设置后请点击"保存配置"生效
📱 可隐藏到系统托盘，全局热键在后台仍可使用
📊 JPEG质量(1-100)和PNG压缩(0-9)可调节文件大小
🖥️ 多屏幕模式：自动适应/鼠标所在屏幕/所有屏幕"""
        
        help_label = ttk.Label(help_frame, text=help_text, justify=tk.LEFT)
        help_label.grid(row=0, column=0, sticky=tk.W)
        
        # 状态栏
        self.status_var = tk.StringVar()
        self.status_var.set("就绪 - 支持全局热键和系统托盘")
        status_label = ttk.Label(main_frame, textvariable=self.status_var, relief=tk.SUNKEN, font=("Arial", 9))
        status_label.grid(row=8, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(10, 0))
        
        # 配置列权重
        path_frame.columnconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        scrollable_frame.columnconfigure(0, weight=1)
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        
        # 鼠标滚轮绑定
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        
        self.root.bind_all("<MouseWheel>", _on_mousewheel)
    
    def setup_system_tray(self):
        """设置系统托盘"""
        try:
            # 创建托盘图标（简单的白色圆形）
            image = Image.new('RGB', (64, 64), color='white')
            
            # 创建托盘菜单
            menu = pystray.Menu(
                item('截图', self.tray_screenshot),
                item('显示窗口', self.show_window),
                item('隐藏窗口', self.hide_window),
                pystray.Menu.SEPARATOR,
                item('退出', self.quit_app)
            )
            
            # 创建托盘图标
            self.tray_icon = pystray.Icon(
                "screenshot_tool",
                image,
                "截图工具",
                menu
            )
            
            # 在后台线程中运行托盘
            self.tray_thread = threading.Thread(target=self.tray_icon.run, daemon=True)
            self.tray_thread.start()
            
            print("系统托盘已启动")
            
        except Exception as e:
            print(f"设置系统托盘失败: {e}")
    
    def tray_screenshot(self):
        """托盘截图功能"""
        self.start_screenshot()
    
    def show_window(self):
        """显示窗口"""
        try:
            self.root.deiconify()
            self.root.lift()
            self.root.focus_force()
            self.is_minimized_to_tray = False
        except:
            pass
    
    def hide_window(self):
        """隐藏窗口到托盘"""
        try:
            self.root.withdraw()
            self.is_minimized_to_tray = True
            print("窗口已隐藏到系统托盘")
        except:
            pass
    
    def load_config_to_gui(self):
        """加载配置到GUI"""
        self.path_var.set(self.config.get("save_directory"))
        self.prefix_var.set(self.config.get("file_prefix"))
        self.format_var.set(self.config.get("file_format"))
        self.hotkey_var.set(self.config.get("hotkey"))
        self.auto_copy_var.set(self.config.get("auto_copy_path"))
        
        # 加载截图模式
        mode_key = self.config.get("screenshot_mode", "auto")
        mode_desc = self.mode_reverse_map.get(mode_key, "自动适应（所有屏幕）")
        self.screenshot_mode_var.set(mode_desc)
        
        # 更新模式说明
        mode_descriptions = {
            "auto": "自动适应：截取所有屏幕，适合多屏幕环境",
            "mouse": "鼠标模式：只截取鼠标当前所在的屏幕",
            "all": "全屏模式：截取所有显示器的内容"
        }
        self.mode_desc_var.set(mode_descriptions.get(mode_key, ""))
        self.show_preview_var.set(self.config.get("show_preview"))
        self.quality_var.set(str(self.config.get("image_quality", 85)))
        self.png_compress_var.set(str(self.config.get("png_compress_level", 6)))
        self.optimize_image_var.set(self.config.get("optimize_image", True))
        self.show_success_popup_var.set(self.config.get("show_success_popup", False))
    
    def browse_folder(self):
        """浏览文件夹"""
        folder = filedialog.askdirectory(initialdir=self.path_var.get())
        if folder:
            self.path_var.set(folder)
    
    def test_hotkey(self):
        """测试热键是否冲突"""
        try:
            # 检查管理员权限
            import ctypes
            is_admin = False
            try:
                is_admin = ctypes.windll.shell32.IsUserAnAdmin()
            except:
                pass
            
            if not is_admin:
                self.hotkey_status_var.set("❌ 需要管理员权限")
                messagebox.showwarning("权限不足", "热键功能需要管理员权限才能正常工作。\n请以管理员身份运行程序后再测试。")
                return
            
            hotkey = self.hotkey_var.get().strip()
            if not hotkey:
                self.hotkey_status_var.set("❌ 热键不能为空")
                return
            
            # 验证热键格式
            valid_keys = ['ctrl', 'alt', 'shift', 'win']
            parts = hotkey.lower().split('+')
            
            if len(parts) < 2:
                self.hotkey_status_var.set("❌ 热键格式错误 (例: ctrl+alt+s)")
                return
            
            # 检查修饰键
            modifiers = parts[:-1]
            key = parts[-1]
            
            for modifier in modifiers:
                if modifier not in valid_keys:
                    self.hotkey_status_var.set(f"❌ 无效的修饰键: {modifier}")
                    return
            
            # 线程安全的测试回调
            def test_callback():
                try:
                    def show_success():
                        self.hotkey_status_var.set("✅ 热键测试成功！")
                        messagebox.showinfo("热键测试", f"热键 '{hotkey}' 测试成功！\n热键工作正常。")
                    
                    self.root.after(0, show_success)
                except Exception as e:
                    print(f"测试回调失败: {e}")
            
            # 先清理现有热键
            try:
                keyboard.unhook_all_hotkeys()
                import time
                time.sleep(0.1)
            except:
                pass
            
            # 注册测试热键
            keyboard.add_hotkey(hotkey, test_callback)
            self.hotkey_status_var.set("🔄 热键已注册，请按热键测试...")
            
            # 5秒后自动重置（延长时间）
            def reset_test():
                try:
                    keyboard.unhook_all_hotkeys()
                    import time
                    time.sleep(0.1)
                    self.setup_hotkeys()  # 恢复原有热键
                    if self.hotkey_status_var.get() == "🔄 热键已注册，请按热键测试...":
                        self.hotkey_status_var.set("⏱️ 测试超时，请手动验证")
                except Exception as e:
                    print(f"重置测试失败: {e}")
            
            self.root.after(5000, reset_test)
            
        except Exception as e:
            self.hotkey_status_var.set(f"❌ 测试失败: {str(e)[:20]}...")
            print(f"热键测试失败: {e}")
    
    def save_config(self):
        """保存配置"""
        try:
            # 验证路径
            save_dir = self.path_var.get().strip()
            if not save_dir:
                messagebox.showerror("错误", "保存路径不能为空")
                return
            
            # 验证文件前缀
            prefix = self.prefix_var.get().strip()
            if not prefix:
                messagebox.showerror("错误", "文件前缀不能为空")
                return
            
            # 验证热键
            hotkey = self.hotkey_var.get().strip()
            if not hotkey:
                messagebox.showerror("错误", "热键不能为空")
                return
            
            # 保存配置
            self.config.set("save_directory", save_dir)
            self.config.set("file_prefix", prefix)
            self.config.set("file_format", self.format_var.get())
            self.config.set("hotkey", hotkey)
            self.config.set("auto_copy_path", self.auto_copy_var.get())
            self.config.set("show_preview", self.show_preview_var.get())
            
            # 保存截图模式
            mode_desc = self.screenshot_mode_var.get()
            mode_key = self.mode_options_map.get(mode_desc, "auto")
            self.config.set("screenshot_mode", mode_key)
            
            # 保存图片优化配置
            try:
                quality = int(self.quality_var.get())
                if 1 <= quality <= 100:
                    self.config.set("image_quality", quality)
            except ValueError:
                self.config.set("image_quality", 85)
            
            try:
                png_compress = int(self.png_compress_var.get())
                if 0 <= png_compress <= 9:
                    self.config.set("png_compress_level", png_compress)
            except ValueError:
                self.config.set("png_compress_level", 6)
            
            self.config.set("optimize_image", self.optimize_image_var.get())
            self.config.set("show_success_popup", self.show_success_popup_var.get())
            
            if self.config.save_config():
                messagebox.showinfo("成功", "配置已保存并应用")
                self.setup_hotkeys()  # 重新设置热键
                self.screenshot_tool.ensure_save_directory()  # 确保保存目录存在
            else:
                messagebox.showerror("错误", "保存配置失败")
        except Exception as e:
            messagebox.showerror("错误", f"保存配置失败: {e}")
    
    def reload_config(self):
        """重新加载配置"""
        try:
            self.config = ScreenshotConfig()
            self.load_config_to_gui()
            self.setup_hotkeys()
            messagebox.showinfo("成功", "配置已重新加载")
        except Exception as e:
            messagebox.showerror("错误", f"重新加载配置失败: {e}")
    
    def reset_to_default(self):
        """重置为默认配置"""
        try:
            if messagebox.askyesno("确认", "确定要重置所有设置为默认值吗？"):
                self.config.config = self.config.default_config.copy()
                self.load_config_to_gui()
                self.setup_hotkeys()
                messagebox.showinfo("成功", "已重置为默认配置")
        except Exception as e:
            messagebox.showerror("错误", f"重置配置失败: {e}")
    
    def start_screenshot(self):
        """开始截图（根据配置的模式）"""
        # 获取当前选择的截图模式
        mode_desc = self.screenshot_mode_var.get()
        mode_key = self.mode_options_map.get(mode_desc, "auto")
        
        # 使用选择的模式进行截图
        self.screenshot_tool.start_area_screenshot(screenshot_mode=mode_key)
    
    # 已移除显示器选择功能，现在使用自动适应模式
    
    def open_save_folder(self):
        """打开保存文件夹"""
        save_dir = self.config.get("save_directory")
        try:
            if sys.platform == "win32":
                os.startfile(save_dir)
            elif sys.platform == "darwin":
                os.system(f"open '{save_dir}'")
            else:
                os.system(f"xdg-open '{save_dir}'")
        except Exception as e:
            messagebox.showerror("错误", f"无法打开文件夹: {e}")
    
    def setup_hotkeys(self):
        """设置热键"""
        try:
            # 检查是否有管理员权限
            import ctypes
            import os
            
            is_admin = False
            try:
                is_admin = ctypes.windll.shell32.IsUserAnAdmin()
            except:
                pass
            
            if not is_admin:
                print("警告：热键功能需要管理员权限才能正常工作")
                print("提示：请以管理员身份运行程序，或只使用界面按钮截图")
                return
            
            # 安全地清理现有热键
            try:
                keyboard.unhook_all_hotkeys()
            except AttributeError:
                try:
                    keyboard.unhook_all()
                except:
                    pass
            except:
                pass
            
            # 延迟一下确保清理完成
            import time
            time.sleep(0.1)
            
            hotkey = self.config.get("hotkey", "ctrl+shift+s")
            
            # 创建全局热键回调函数
            def global_screenshot_callback():
                try:
                    print(f"全局热键触发: {hotkey}")
                    
                    # 确保主窗口存在且可用
                    if hasattr(self, 'root') and self.root and self.root.winfo_exists():
                        # 如果窗口被最小化，先恢复
                        if self.root.state() == 'iconic':
                            self.root.deiconify()
                        
                        # 在主线程中执行截图
                        self.root.after(0, self.start_screenshot)
                    else:
                        # 如果GUI不可用，直接调用截图工具
                        print("GUI不可用，直接调用截图功能")
                        self.screenshot_tool.start_area_screenshot()
                        
                except Exception as e:
                    print(f"全局热键回调失败: {e}")
                    try:
                        # 备用方案：直接调用截图
                        self.screenshot_tool.start_area_screenshot()
                    except Exception as e2:
                        print(f"备用截图方案也失败: {e2}")
            
            # 注册全局热键
            keyboard.add_hotkey(hotkey, global_screenshot_callback)
            print(f"全局热键已设置: {hotkey}")
            
            # 更新状态栏
            if hasattr(self, 'status_var'):
                self.status_var.set(f"就绪 - 全局热键: {hotkey}")
                
        except Exception as e:
            print(f"设置热键失败: {e}")
            print("提示：热键功能可能不可用，但截图功能仍可通过界面按钮使用")
            if hasattr(self, 'status_var'):
                self.status_var.set("就绪 - 热键不可用，请使用按钮截图")
    
    def quit_app(self):
        """退出应用程序"""
        try:
            # 停止托盘图标
            if self.tray_icon:
                self.tray_icon.stop()
            
            # 清理热键
            try:
                keyboard.unhook_all_hotkeys()
            except AttributeError:
                try:
                    keyboard.unhook_all()
                except:
                    pass
            except:
                pass
            
            # 销毁GUI
            self.root.destroy()
            
        except Exception as e:
            print(f"退出程序时出错: {e}")
            
        # 强制退出
        sys.exit(0)
    
    def run(self):
        """运行GUI"""
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.root.mainloop()
    
    def on_closing(self):
        """关闭窗口时的处理"""
        # 询问用户是否要最小化到托盘
        choice = messagebox.askyesnocancel(
            "截图工具", 
            "要最小化到系统托盘吗？\n\n是：最小化到托盘（后台运行）\n否：完全退出程序\n取消：继续运行"
        )
        
        if choice is True:  # 最小化到托盘
            self.hide_window()
        elif choice is False:  # 退出程序
            self.quit_app()
        # choice is None (取消) - 什么都不做，继续运行

def main():
    """主函数"""
    try:
        app = ScreenshotGUI()
        app.run()
    except Exception as e:
        print(f"程序启动失败: {e}")
        input("按回车键退出...")

if __name__ == "__main__":
    main()