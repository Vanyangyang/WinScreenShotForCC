#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
截图工具GUI界面 - 包含质量设置
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import subprocess
import threading
from pathlib import Path
from screenshot_tool_new import ScreenshotTool, ScreenshotConfig

# 尝试导入热键库
try:
    import keyboard
    HOTKEY_AVAILABLE = True
except ImportError:
    HOTKEY_AVAILABLE = False
    print("注意: keyboard库未安装，热键功能将不可用")

class ScreenshotGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.geometry("520x1050")
        self.root.minsize(520, 600)
        self.root.resizable(True, True)
        
        # 创建配置
        self.config = ScreenshotConfig()
        self.tool = ScreenshotTool(self.config)
        self.tool.main_window = self.root
        
        # 热键相关
        self.hotkey_thread = None
        self.hotkey_enabled = False
        
        # 语言设置
        self.current_language = self.config.get("language", "zh")  # 默认中文
        self.init_translations()
        self.ui_elements = {}  # 存储需要更新文本的UI元素
        
        # 设置窗口标题
        self.root.title(self.tr("window_title"))
        
        self.create_widgets()
        self.load_settings()
        
        # 设置关闭时的清理
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # 初始化滚动区域
        self.root.after(100, self.update_scroll_region)
        
        # 确保窗口居中显示
        self.center_window()
    
    def init_translations(self):
        """初始化翻译字典"""
        self.translations = {
            "zh": {
                # 窗口标题
                "window_title": "截图工具",
                "tool_title": "🖼️ 截图工具",
                
                # 框架标题
                "monitor_info": "显示器信息",
                "screenshot_settings": "截图设置",
                "hotkey_settings": "热键设置",
                "screenshot_actions": "截图操作",
                "tools": "工具栏",
                
                # 标签文本
                "monitors_detected": "检测到 {} 个显示器",
                "save_directory": "保存目录:",
                "browse": "浏览",
                "directory_tip": "💡 建议使用项目根目录，方便Claude Code读取",
                "file_format": "文件格式: PNG（固定）",
                "image_quality": "图片质量:",
                "quality_low": "推荐Claude Code使用",
                "quality_medium": "平衡质量",
                "quality_high": "高质量 ⚠️",
                "quality_warning": "⚠️ 警告：高质量模式会生成较大的文件，可能消耗大量token！\n建议仅在必要时使用高质量模式。",
                "auto_copy_path": "自动复制路径到剪贴板",
                "show_preview": "显示预览窗口",
                "custom_prefix": "自定义前缀:",
                "prefix_tip": "💡 前缀将添加到剪贴板内容的开头，例如：'![截图](' 或 '图片：'",
                "hotkey": "热键:",
                "hotkey_disabled": "热键未启用",
                "hotkey_enabled": "热键已启用",
                "enable_hotkey": "启用热键",
                "disable_hotkey": "禁用热键",
                
                # 按钮文本
                "fullscreen_screenshot": "全屏截图",
                "mouse_screen_screenshot": "鼠标屏幕截图",
                "screenshot_tip": "提示: 按住并拖拽选择区域，ESC取消",
                "open_directory": "📁 打开目录",
                "clean_screenshots": "🗑️ 清理截图",
                "save_settings": "💾 保存设置",
                "exit": "❌ 退出",
                "switch_language": "🌐 English",
                
                # 对话框消息
                "select_directory": "选择保存目录",
                "settings_saved": "设置已保存",
                "settings_saved_msg": "设置已成功保存",
                "clean_confirm": "确认清理",
                "clean_confirm_msg": "是否清理所有截图文件？\n\n分析结果：\n{}",
                "no_screenshots": "没有截图",
                "no_screenshots_msg": "当前目录没有截图文件",
                "clean_success": "清理成功",
                "clean_success_msg": "已删除 {} 个截图文件",
                "hotkey_error": "热键设置错误",
                "hotkey_invalid": "无效的热键格式",
                "hotkey_register_failed": "热键注册失败: {}",
            },
            "en": {
                # Window titles
                "window_title": "Screenshot Tool",
                "tool_title": "🖼️ Screenshot Tool",
                
                # Frame titles
                "monitor_info": "Monitor Information",
                "screenshot_settings": "Screenshot Settings",
                "hotkey_settings": "Hotkey Settings",
                "screenshot_actions": "Screenshot Actions",
                "tools": "Tools",
                
                # Label texts
                "monitors_detected": "{} monitor(s) detected",
                "save_directory": "Save Directory:",
                "browse": "Browse",
                "directory_tip": "💡 Tip: Use project root for easy Claude Code access",
                "file_format": "File Format: PNG (Fixed)",
                "image_quality": "Image Quality:",
                "quality_low": "Recommended for Claude Code",
                "quality_medium": "Balanced Quality",
                "quality_high": "High Quality ⚠️",
                "quality_warning": "⚠️ Warning: High quality mode generates large files that may consume many tokens!\nUse high quality mode only when necessary.",
                "auto_copy_path": "Auto copy path to clipboard",
                "show_preview": "Show preview window",
                "custom_prefix": "Custom Prefix:",
                "prefix_tip": "💡 Prefix will be added to the beginning of clipboard content, e.g., '![Screenshot](' or 'Image: '",
                "hotkey": "Hotkey:",
                "hotkey_disabled": "Hotkey disabled",
                "hotkey_enabled": "Hotkey enabled",
                "enable_hotkey": "Enable Hotkey",
                "disable_hotkey": "Disable Hotkey",
                
                # Button texts
                "fullscreen_screenshot": "Fullscreen Screenshot",
                "mouse_screen_screenshot": "Mouse Screen Screenshot",
                "screenshot_tip": "Tip: Click and drag to select area, ESC to cancel",
                "open_directory": "📁 Open Directory",
                "clean_screenshots": "🗑️ Clean Screenshots",
                "save_settings": "💾 Save Settings",
                "exit": "❌ Exit",
                "switch_language": "🌐 中文",
                
                # Dialog messages
                "select_directory": "Select Save Directory",
                "settings_saved": "Settings Saved",
                "settings_saved_msg": "Settings saved successfully",
                "clean_confirm": "Confirm Clean",
                "clean_confirm_msg": "Clean all screenshot files?\n\nAnalysis:\n{}",
                "no_screenshots": "No Screenshots",
                "no_screenshots_msg": "No screenshot files in current directory",
                "clean_success": "Clean Success",
                "clean_success_msg": "Deleted {} screenshot file(s)",
                "hotkey_error": "Hotkey Error",
                "hotkey_invalid": "Invalid hotkey format",
                "hotkey_register_failed": "Hotkey registration failed: {}",
            }
        }
    
    def tr(self, key):
        """获取当前语言的翻译文本"""
        return self.translations[self.current_language].get(key, key)
        
    def create_widgets(self):
        """创建界面组件"""
        # 标题
        title_frame = tk.Frame(self.root)
        title_frame.pack(pady=10)
        
        self.title_label = tk.Label(title_frame, text=self.tr("tool_title"), font=("Arial", 20, "bold"))
        self.title_label.pack(side=tk.LEFT)
        self.ui_elements['title_label'] = self.title_label
        
        # 语言切换按钮
        self.lang_btn = tk.Button(title_frame, text=self.tr("switch_language"), 
                                 command=self.toggle_language, font=("Arial", 10))
        self.lang_btn.pack(side=tk.RIGHT, padx=20)
        self.ui_elements['lang_btn'] = self.lang_btn
        
        # 创建滚动框架
        canvas = tk.Canvas(self.root, highlightthickness=0)
        scrollbar = ttk.Scrollbar(self.root, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # 布局滚动组件
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # 主框架（现在在滚动框内）
        main_frame = tk.Frame(scrollable_frame, padx=20)
        main_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        # 鼠标滚轮绑定
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        
        # 绑定鼠标滚轮事件到不同组件
        def bind_mousewheel(widget):
            widget.bind("<MouseWheel>", _on_mousewheel)  # Windows
            widget.bind("<Button-4>", lambda e: canvas.yview_scroll(-1, "units"))  # Linux
            widget.bind("<Button-5>", lambda e: canvas.yview_scroll(1, "units"))   # Linux
        
        bind_mousewheel(canvas)
        bind_mousewheel(scrollable_frame)
        
        # 保存引用以便后续使用和绑定滚轮
        self.canvas = canvas
        self.scrollable_frame = scrollable_frame
        self.bind_mousewheel = bind_mousewheel
        
        # 显示器信息
        self.info_frame = tk.LabelFrame(main_frame, text=self.tr("monitor_info"), pady=10)
        self.info_frame.pack(fill=tk.X, pady=10)
        self.ui_elements['info_frame'] = self.info_frame
        
        info_text = self.tr("monitors_detected").format(len(self.tool.monitors)) + "\n"
        for i, monitor in enumerate(self.tool.monitors):
            info_text += f"  {monitor['name']}: {monitor['width']}x{monitor['height']}\n"
        
        self.info_label = tk.Label(self.info_frame, text=info_text, justify=tk.LEFT)
        self.info_label.pack(padx=10)
        self.ui_elements['info_label'] = self.info_label
        
        # 设置框架
        self.settings_frame = tk.LabelFrame(main_frame, text=self.tr("screenshot_settings"), pady=10)
        self.settings_frame.pack(fill=tk.X, pady=10)
        self.ui_elements['settings_frame'] = self.settings_frame
        
        # 保存目录
        dir_frame = tk.Frame(self.settings_frame)
        dir_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.dir_label = tk.Label(dir_frame, text=self.tr("save_directory"))
        self.dir_label.pack(side=tk.LEFT)
        self.ui_elements['dir_label'] = self.dir_label
        
        self.dir_var = tk.StringVar()
        self.dir_entry = tk.Entry(dir_frame, textvariable=self.dir_var, width=30)
        self.dir_entry.pack(side=tk.LEFT, padx=5)
        
        self.browse_btn = tk.Button(dir_frame, text=self.tr("browse"), command=self.browse_directory)
        self.browse_btn.pack(side=tk.LEFT)
        self.ui_elements['browse_btn'] = self.browse_btn
        
        # 目录建议提示
        dir_tip_frame = tk.Frame(self.settings_frame)
        dir_tip_frame.pack(fill=tk.X, padx=10, pady=2)
        
        self.dir_tip_label = tk.Label(dir_tip_frame, text=self.tr("directory_tip"), 
                font=("Arial", 9), fg="#28a745")
        self.dir_tip_label.pack(anchor=tk.W)
        self.ui_elements['dir_tip_label'] = self.dir_tip_label
        
        # 文件格式说明
        format_frame = tk.Frame(self.settings_frame)
        format_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.format_label = tk.Label(format_frame, text=self.tr("file_format"), font=("Arial", 10))
        self.format_label.pack(side=tk.LEFT)
        self.ui_elements['format_label'] = self.format_label
        
        # 质量预设（重要！）
        quality_frame = tk.Frame(self.settings_frame)
        quality_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.quality_label = tk.Label(quality_frame, text=self.tr("image_quality"))
        self.quality_label.pack(side=tk.LEFT)
        self.ui_elements['quality_label'] = self.quality_label
        self.quality_var = tk.StringVar()
        quality_combo = ttk.Combobox(quality_frame, textvariable=self.quality_var,
                                    values=["low", "medium", "high"], 
                                    state="readonly", width=10)
        quality_combo.pack(side=tk.LEFT, padx=5)
        quality_combo.bind("<<ComboboxSelected>>", self.on_quality_change)
        
        # 质量说明
        self.quality_info = tk.Label(quality_frame, text="", fg="blue")
        self.quality_info.pack(side=tk.LEFT, padx=10)
        
        # 警告框
        self.warning_frame = tk.Frame(self.settings_frame, bg="#fff3cd", relief=tk.RIDGE, bd=1)
        self.warning_label = tk.Label(self.warning_frame, 
                                     text=self.tr("quality_warning"),
                                     bg="#fff3cd", fg="#856404", justify=tk.LEFT,
                                     font=("Arial", 10, "bold"))
        self.warning_label.pack(padx=10, pady=5)
        self.ui_elements['warning_label'] = self.warning_label
        
        # 其他选项
        options_frame = tk.Frame(self.settings_frame)
        options_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.copy_path_var = tk.BooleanVar()
        self.copy_path_cb = tk.Checkbutton(options_frame, text=self.tr("auto_copy_path"), 
                      variable=self.copy_path_var)
        self.copy_path_cb.pack(anchor=tk.W)
        self.ui_elements['copy_path_cb'] = self.copy_path_cb
        
        self.show_preview_var = tk.BooleanVar()
        self.show_preview_cb = tk.Checkbutton(options_frame, text=self.tr("show_preview"),
                      variable=self.show_preview_var)
        self.show_preview_cb.pack(anchor=tk.W)
        self.ui_elements['show_preview_cb'] = self.show_preview_cb

        # 自定义前缀设置
        prefix_frame = tk.Frame(self.settings_frame)
        prefix_frame.pack(fill=tk.X, padx=10, pady=5)

        self.prefix_label = tk.Label(prefix_frame, text=self.tr("custom_prefix"))
        self.prefix_label.pack(side=tk.LEFT)
        self.ui_elements['prefix_label'] = self.prefix_label

        self.prefix_var = tk.StringVar()
        self.prefix_entry = tk.Entry(prefix_frame, textvariable=self.prefix_var, width=30)
        self.prefix_entry.pack(side=tk.LEFT, padx=5)

        # 前缀提示
        prefix_tip_frame = tk.Frame(self.settings_frame)
        prefix_tip_frame.pack(fill=tk.X, padx=10, pady=2)

        self.prefix_tip_label = tk.Label(prefix_tip_frame, text=self.tr("prefix_tip"),
                font=("Arial", 9), fg="#6c757d")
        self.prefix_tip_label.pack(anchor=tk.W)
        self.ui_elements['prefix_tip_label'] = self.prefix_tip_label
        
        # 热键设置
        self.hotkey_frame = tk.LabelFrame(main_frame, text=self.tr("hotkey_settings"), pady=10)
        self.hotkey_frame.pack(fill=tk.X, pady=10)
        self.ui_elements['hotkey_frame'] = self.hotkey_frame
        
        # 热键输入
        hk_input_frame = tk.Frame(self.hotkey_frame)
        hk_input_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.hotkey_label = tk.Label(hk_input_frame, text=self.tr("hotkey"))
        self.hotkey_label.pack(side=tk.LEFT)
        self.ui_elements['hotkey_label'] = self.hotkey_label
        
        self.hotkey_var = tk.StringVar()
        self.hotkey_entry = tk.Entry(hk_input_frame, textvariable=self.hotkey_var, width=20)
        self.hotkey_entry.pack(side=tk.LEFT, padx=5)
        
        # 热键控制按钮
        hk_control_frame = tk.Frame(self.hotkey_frame)
        hk_control_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.hotkey_status_label = tk.Label(hk_control_frame, text=self.tr("hotkey_disabled"), fg="red")
        self.hotkey_status_label.pack(side=tk.LEFT)
        self.ui_elements['hotkey_status_label'] = self.hotkey_status_label
        
        self.hotkey_toggle_btn = tk.Button(hk_control_frame, text=self.tr("enable_hotkey"), 
                                          command=self.toggle_hotkey)
        self.hotkey_toggle_btn.pack(side=tk.RIGHT, padx=5)
        self.ui_elements['hotkey_toggle_btn'] = self.hotkey_toggle_btn
        
        if not HOTKEY_AVAILABLE:
            self.hotkey_entry.config(state=tk.DISABLED)
            self.hotkey_toggle_btn.config(state=tk.DISABLED)
            self.hotkey_status_label.config(text="热键功能不可用（需要keyboard库）", fg="gray")
        
        # 截图按钮
        self.action_frame = tk.LabelFrame(main_frame, text=self.tr("screenshot_actions"), pady=10)
        self.action_frame.pack(fill=tk.X, pady=10)
        self.ui_elements['action_frame'] = self.action_frame
        
        self.fullscreen_btn = tk.Button(self.action_frame, text=self.tr("fullscreen_screenshot"), 
                 command=lambda: self.take_screenshot('all'),
                 font=("Arial", 12), height=2, bg="#28a745", fg="white")
        self.fullscreen_btn.pack(fill=tk.X, padx=10, pady=5)
        self.ui_elements['fullscreen_btn'] = self.fullscreen_btn
        
        self.mouse_screen_btn = tk.Button(self.action_frame, text=self.tr("mouse_screen_screenshot"), 
                 command=lambda: self.take_screenshot('mouse'),
                 font=("Arial", 12), height=2, bg="#17a2b8", fg="white")
        self.mouse_screen_btn.pack(fill=tk.X, padx=10, pady=5)
        self.ui_elements['mouse_screen_btn'] = self.mouse_screen_btn
        
        # 提示
        tip_frame = tk.Frame(main_frame)
        tip_frame.pack(fill=tk.X, pady=10)
        
        self.tip_label = tk.Label(tip_frame, text=self.tr("screenshot_tip"), 
                font=("Arial", 10), fg="gray")
        self.tip_label.pack()
        self.ui_elements['tip_label'] = self.tip_label
        
        # 工具栏（在滚动区域内）
        self.tools_frame = tk.LabelFrame(main_frame, text=self.tr("tools"), pady=10)
        self.tools_frame.pack(fill=tk.X, pady=10)
        self.ui_elements['tools_frame'] = self.tools_frame
        
        # 第一行按钮
        toolbar_row1 = tk.Frame(self.tools_frame)
        toolbar_row1.pack(pady=5)
        
        self.open_dir_btn = tk.Button(toolbar_row1, text=self.tr("open_directory"), command=self.open_screenshot_folder, 
                 bg="#17a2b8", fg="white", width=12, height=2)
        self.open_dir_btn.pack(side=tk.LEFT, padx=5)
        self.ui_elements['open_dir_btn'] = self.open_dir_btn
        
        self.clean_btn = tk.Button(toolbar_row1, text=self.tr("clean_screenshots"), command=self.clean_screenshots,
                 bg="#dc3545", fg="white", width=12, height=2)
        self.clean_btn.pack(side=tk.LEFT, padx=5)
        self.ui_elements['clean_btn'] = self.clean_btn
        
        self.save_btn = tk.Button(toolbar_row1, text=self.tr("save_settings"), command=self.save_settings,
                 bg="#28a745", fg="white", width=12, height=2)
        self.save_btn.pack(side=tk.LEFT, padx=5)
        self.ui_elements['save_btn'] = self.save_btn
        
        # 第二行按钮
        toolbar_row2 = tk.Frame(self.tools_frame)
        toolbar_row2.pack(pady=5)
        
        self.exit_btn = tk.Button(toolbar_row2, text=self.tr("exit"), command=self.on_closing,
                 bg="#6c757d", fg="white", width=12, height=2)
        self.exit_btn.pack()
        self.ui_elements['exit_btn'] = self.exit_btn
        
        # 为所有主要组件绑定鼠标滚轮
        for widget in [main_frame, self.info_frame, self.settings_frame, self.hotkey_frame, 
                      self.action_frame, tip_frame, self.tools_frame]:
            self.bind_mousewheel(widget)
        
    def center_window(self):
        """窗口居中显示"""
        self.root.update_idletasks()
        
        # 获取窗口尺寸
        window_width = self.root.winfo_width()
        window_height = self.root.winfo_height()
        
        # 获取屏幕尺寸
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        
        # 计算居中位置
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        
        # 设置窗口位置
        self.root.geometry(f"{window_width}x{window_height}+{x}+{y}")
    
    def update_scroll_region(self):
        """更新滚动区域"""
        try:
            self.canvas.update_idletasks()
            self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        except Exception as e:
            print(f"更新滚动区域失败: {e}")
    
    def browse_directory(self):
        """浏览目录"""
        directory = filedialog.askdirectory(
            title=self.tr("select_directory"),
            initialdir=self.dir_var.get()
        )
        if directory:
            self.dir_var.set(directory)
    
    def toggle_language(self):
        """切换语言"""
        self.current_language = "en" if self.current_language == "zh" else "zh"
        self.config.set("language", self.current_language)
        self.config.save_config()
        self.update_ui_text()
    
    def update_ui_text(self):
        """更新所有UI文本"""
        # 更新窗口标题
        self.root.title(self.tr("window_title"))
        
        # 更新所有已保存的UI元素
        for key, element in self.ui_elements.items():
            if key == 'title_label':
                element.config(text=self.tr("tool_title"))
            elif key == 'lang_btn':
                element.config(text=self.tr("switch_language"))
            elif key == 'info_frame':
                element.config(text=self.tr("monitor_info"))
            elif key == 'info_label':
                info_text = self.tr("monitors_detected").format(len(self.tool.monitors)) + "\n"
                for i, monitor in enumerate(self.tool.monitors):
                    info_text += f"  {monitor['name']}: {monitor['width']}x{monitor['height']}\n"
                element.config(text=info_text)
            elif key == 'settings_frame':
                element.config(text=self.tr("screenshot_settings"))
            elif key == 'dir_label':
                element.config(text=self.tr("save_directory"))
            elif key == 'browse_btn':
                element.config(text=self.tr("browse"))
            elif key == 'dir_tip_label':
                element.config(text=self.tr("directory_tip"))
            elif key == 'format_label':
                element.config(text=self.tr("file_format"))
            elif key == 'quality_label':
                element.config(text=self.tr("image_quality"))
            elif key == 'copy_path_cb':
                element.config(text=self.tr("auto_copy_path"))
            elif key == 'show_preview_cb':
                element.config(text=self.tr("show_preview"))
            elif key == 'prefix_label':
                element.config(text=self.tr("custom_prefix"))
            elif key == 'prefix_tip_label':
                element.config(text=self.tr("prefix_tip"))
            elif key == 'hotkey_frame':
                element.config(text=self.tr("hotkey_settings"))
            elif key == 'hotkey_label':
                element.config(text=self.tr("hotkey"))
            elif key == 'hotkey_toggle_btn':
                if self.hotkey_enabled:
                    element.config(text=self.tr("disable_hotkey"))
                else:
                    element.config(text=self.tr("enable_hotkey"))
            elif key == 'hotkey_status_label':
                if self.hotkey_enabled:
                    element.config(text=self.tr("hotkey_enabled"))
                else:
                    element.config(text=self.tr("hotkey_disabled"))
            elif key == 'action_frame':
                element.config(text=self.tr("screenshot_actions"))
            elif key == 'fullscreen_btn':
                element.config(text=self.tr("fullscreen_screenshot"))
            elif key == 'mouse_screen_btn':
                element.config(text=self.tr("mouse_screen_screenshot"))
            elif key == 'tip_label':
                element.config(text=self.tr("screenshot_tip"))
            elif key == 'tools_frame':
                element.config(text=self.tr("tools"))
            elif key == 'open_dir_btn':
                element.config(text=self.tr("open_directory"))
            elif key == 'clean_btn':
                element.config(text=self.tr("clean_screenshots"))
            elif key == 'save_btn':
                element.config(text=self.tr("save_settings"))
            elif key == 'exit_btn':
                element.config(text=self.tr("exit"))
            elif key == 'warning_label':
                element.config(text=self.tr("quality_warning"))
        
        # 更新质量信息
        self.on_quality_change()
    
    def on_quality_change(self, event=None):
        """质量选择改变时"""
        quality = self.quality_var.get()
        
        quality_info = {
            "low": self.tr("quality_low"),
            "medium": self.tr("quality_medium"),
            "high": self.tr("quality_high")
        }
        
        self.quality_info.config(text=quality_info.get(quality, ""))
        
        # 显示或隐藏警告
        if quality == "high":
            self.warning_frame.pack(fill=tk.X, padx=10, pady=5)
        else:
            self.warning_frame.pack_forget()
    
    def load_settings(self):
        """加载设置"""
        self.dir_var.set(self.config.get("save_directory"))
        self.quality_var.set(self.config.get("quality_preset", "low"))
        self.copy_path_var.set(self.config.get("auto_copy_path", True))
        self.show_preview_var.set(self.config.get("show_preview", True))
        self.prefix_var.set(self.config.get("custom_prefix", "read image: "))
        self.hotkey_var.set(self.config.get("hotkey", "ctrl+shift+s"))

        # 触发质量改变事件
        self.on_quality_change()
    
    def save_settings(self):
        """保存设置"""
        self.config.set("save_directory", self.dir_var.get())
        self.config.set("quality_preset", self.quality_var.get())
        self.config.set("auto_copy_path", self.copy_path_var.get())
        self.config.set("show_preview", self.show_preview_var.get())
        self.config.set("custom_prefix", self.prefix_var.get())
        self.config.set("hotkey", self.hotkey_var.get())
        self.config.set("language", self.current_language)

        if self.config.save_config():
            messagebox.showinfo(self.tr("settings_saved"), self.tr("settings_saved_msg"))
        else:
            messagebox.showerror("Error", "Failed to save settings")
    
    def take_screenshot(self, mode):
        """执行截图"""
        # 保存当前设置
        self.save_settings()
        
        # 如果选择了高质量，再次确认
        if self.quality_var.get() == "high":
            result = messagebox.askyesno("确认", 
                                       "您选择了高质量模式，这将生成较大的文件。\n"
                                       "是否继续？", 
                                       icon="warning")
                                       
            if not result:
                return
        
        # 执行截图
        self.tool.start_area_screenshot(screenshot_mode=mode)
    
    def toggle_hotkey(self):
        """切换热键状态"""
        if not HOTKEY_AVAILABLE:
            return
        
        if self.hotkey_enabled:
            # 禁用热键
            self.stop_hotkey()
        else:
            # 启用热键
            self.start_hotkey()
    
    def start_hotkey(self):
        """启动热键监听"""
        if not HOTKEY_AVAILABLE:
            return
        
        hotkey_str = self.hotkey_var.get().strip()
        if not hotkey_str:
            messagebox.showerror(self.tr("hotkey_error"), self.tr("hotkey_invalid"))
            return
        
        try:
            # 在后台线程中启动热键监听
            def hotkey_worker():
                try:
                    keyboard.add_hotkey(hotkey_str, lambda: self.tool.start_area_screenshot(screenshot_mode='all'))
                    self.hotkey_enabled = True
                    self.root.after(0, self.update_hotkey_status)
                    keyboard.wait()  # 保持监听
                except Exception as e:
                    self.root.after(0, lambda: messagebox.showerror(self.tr("hotkey_error"), 
                                                                   self.tr("hotkey_register_failed").format(e)))
            
            self.hotkey_thread = threading.Thread(target=hotkey_worker, daemon=True)
            self.hotkey_thread.start()
            
        except Exception as e:
            messagebox.showerror("错误", f"启动热键失败: {e}")
    
    def stop_hotkey(self):
        """停止热键监听"""
        if HOTKEY_AVAILABLE and self.hotkey_enabled:
            try:
                keyboard.unhook_all_hotkeys()
                self.hotkey_enabled = False
                self.update_hotkey_status()
            except Exception as e:
                print(f"停止热键失败: {e}")
    
    def update_hotkey_status(self):
        """更新热键状态显示"""
        if self.hotkey_enabled:
            self.hotkey_status_label.config(text=f"{self.tr('hotkey_enabled')}: {self.hotkey_var.get()}", fg="green")
            self.hotkey_toggle_btn.config(text=self.tr("disable_hotkey"))
        else:
            self.hotkey_status_label.config(text=self.tr("hotkey_disabled"), fg="red")
            self.hotkey_toggle_btn.config(text=self.tr("enable_hotkey"))
    
    def clean_screenshots(self):
        """清理截图文件"""
        save_dir = self.dir_var.get()
        if not save_dir:
            messagebox.showerror("错误", "保存目录未设置")
            return
        
        save_path = Path(save_dir)
        if not save_path.exists():
            messagebox.showwarning("警告", "保存目录不存在")
            return
        
        # 获取文件前缀配置
        file_prefix = self.config.get("file_prefix", "screenshot_")
        
        # 查找匹配的截图文件
        screenshot_patterns = [
            f"{file_prefix}*.png",
            f"{file_prefix}*.jpg", 
            f"{file_prefix}*.jpeg",
            "shot_*.png",  # 兼容旧格式
            "screenshot*.png"  # 兼容其他格式
        ]
        
        found_files = []
        for pattern in screenshot_patterns:
            found_files.extend(save_path.glob(pattern))
        
        if not found_files:
            messagebox.showinfo(self.tr("no_screenshots"), self.tr("no_screenshots_msg"))
            return
        
        # 按文件修改时间排序，显示文件信息
        found_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
        
        # 计算文件总大小
        total_size = sum(f.stat().st_size for f in found_files)
        size_mb = total_size / (1024 * 1024)
        
        # 分析文件时间分布
        import datetime
        now = datetime.datetime.now()
        today_files = []
        week_files = []
        month_files = []
        older_files = []
        
        for f in found_files:
            file_time = datetime.datetime.fromtimestamp(f.stat().st_mtime)
            days_ago = (now - file_time).days
            
            if days_ago == 0:
                today_files.append(f)
            elif days_ago <= 7:
                week_files.append(f)
            elif days_ago <= 30:
                month_files.append(f)
            else:
                older_files.append(f)
        
        # 构建详细确认对话框
        file_list = "\n".join([f"• {f.name} ({f.stat().st_size/1024:.1f}KB)" 
                              for f in found_files[:8]])  # 只显示前8个
        if len(found_files) > 8:
            file_list += f"\n... 还有 {len(found_files) - 8} 个文件"
        
        time_breakdown = (f"📅 时间分布:\n"
                         f"• 今天: {len(today_files)} 个\n"
                         f"• 本周: {len(week_files)} 个\n" 
                         f"• 本月: {len(month_files)} 个\n"
                         f"• 更早: {len(older_files)} 个")
        
        confirm_msg = (f"🗑️ 截图清理确认\n\n"
                      f"找到 {len(found_files)} 个截图文件，总大小 {size_mb:.2f}MB\n\n"
                      f"{time_breakdown}\n\n"
                      f"最新文件预览:\n{file_list}\n\n"
                      f"⚠️ 确定要删除这些文件吗？\n"
                      f"此操作无法撤销！")
        
        # 简化的确认消息
        simple_msg = self.tr("clean_confirm_msg").format(
            f"{len(found_files)} files, {size_mb:.1f}MB"
        )
        
        result = messagebox.askyesnocancel(self.tr("clean_confirm"), simple_msg, 
                                         icon="warning", default="no")
        
        if result is True:  # 用户选择"是"
            # 执行删除
            deleted_count = 0
            failed_files = []
            
            for file_path in found_files:
                try:
                    file_path.unlink()
                    deleted_count += 1
                except Exception as e:
                    failed_files.append(f"{file_path.name}: {e}")
            
            # 显示结果
            if failed_files:
                error_msg = f"成功删除 {deleted_count} 个文件\n\n删除失败的文件:\n" + \
                           "\n".join(failed_files[:5])
                if len(failed_files) > 5:
                    error_msg += f"\n... 还有 {len(failed_files) - 5} 个失败"
                messagebox.showwarning("部分完成", error_msg)
            else:
                messagebox.showinfo(self.tr("clean_success"), 
                                  self.tr("clean_success_msg").format(deleted_count))
    
    def open_screenshot_folder(self):
        """打开截图保存目录"""
        save_dir = self.dir_var.get()
        if not save_dir:
            messagebox.showerror("错误", "保存目录未设置")
            return
        
        # 确保目录存在
        Path(save_dir).mkdir(parents=True, exist_ok=True)
        
        try:
            if sys.platform == "win32":
                os.startfile(save_dir)
            elif sys.platform == "darwin":
                subprocess.run(["open", save_dir])
            else:
                subprocess.run(["xdg-open", save_dir])
        except Exception as e:
            messagebox.showerror("错误", f"无法打开目录: {e}")
    
    def on_closing(self):
        """关闭程序时的清理"""
        self.stop_hotkey()
        self.root.quit()
        self.root.destroy()
    
    def run(self):
        """运行GUI"""
        self.root.mainloop()

if __name__ == "__main__":
    app = ScreenshotGUI()
    app.run()