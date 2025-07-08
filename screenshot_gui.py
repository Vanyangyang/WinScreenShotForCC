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
        self.root.title("截图工具")
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
        
        self.create_widgets()
        self.load_settings()
        
        # 设置关闭时的清理
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # 初始化滚动区域
        self.root.after(100, self.update_scroll_region)
        
        # 确保窗口居中显示
        self.center_window()
        
    def create_widgets(self):
        """创建界面组件"""
        # 标题
        title_frame = tk.Frame(self.root)
        title_frame.pack(pady=10)
        
        title = tk.Label(title_frame, text="🖼️ 截图工具", font=("Arial", 20, "bold"))
        title.pack()
        
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
        info_frame = tk.LabelFrame(main_frame, text="显示器信息", pady=10)
        info_frame.pack(fill=tk.X, pady=10)
        
        info_text = f"检测到 {len(self.tool.monitors)} 个显示器\n"
        for i, monitor in enumerate(self.tool.monitors):
            info_text += f"  {monitor['name']}: {monitor['width']}x{monitor['height']}\n"
        
        tk.Label(info_frame, text=info_text, justify=tk.LEFT).pack(padx=10)
        
        # 设置框架
        settings_frame = tk.LabelFrame(main_frame, text="截图设置", pady=10)
        settings_frame.pack(fill=tk.X, pady=10)
        
        # 保存目录
        dir_frame = tk.Frame(settings_frame)
        dir_frame.pack(fill=tk.X, padx=10, pady=5)
        
        tk.Label(dir_frame, text="保存目录:").pack(side=tk.LEFT)
        self.dir_var = tk.StringVar()
        self.dir_entry = tk.Entry(dir_frame, textvariable=self.dir_var, width=30)
        self.dir_entry.pack(side=tk.LEFT, padx=5)
        tk.Button(dir_frame, text="浏览", command=self.browse_directory).pack(side=tk.LEFT)
        
        # 目录建议提示
        dir_tip_frame = tk.Frame(settings_frame)
        dir_tip_frame.pack(fill=tk.X, padx=10, pady=2)
        
        tk.Label(dir_tip_frame, text="💡 建议使用项目根目录，方便Claude Code读取", 
                font=("Arial", 9), fg="#28a745").pack(anchor=tk.W)
        
        # 文件格式说明
        format_frame = tk.Frame(settings_frame)
        format_frame.pack(fill=tk.X, padx=10, pady=5)
        
        tk.Label(format_frame, text="文件格式: PNG（固定）", font=("Arial", 10)).pack(side=tk.LEFT)
        
        # 质量预设（重要！）
        quality_frame = tk.Frame(settings_frame)
        quality_frame.pack(fill=tk.X, padx=10, pady=5)
        
        tk.Label(quality_frame, text="图片质量:").pack(side=tk.LEFT)
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
        self.warning_frame = tk.Frame(settings_frame, bg="#fff3cd", relief=tk.RIDGE, bd=1)
        self.warning_label = tk.Label(self.warning_frame, 
                                     text="⚠️ 警告：高质量模式会生成较大的文件，可能消耗大量token！\n"
                                          "建议仅在必要时使用高质量模式。",
                                     bg="#fff3cd", fg="#856404", justify=tk.LEFT,
                                     font=("Arial", 10, "bold"))
        self.warning_label.pack(padx=10, pady=5)
        
        # 其他选项
        options_frame = tk.Frame(settings_frame)
        options_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.copy_path_var = tk.BooleanVar()
        tk.Checkbutton(options_frame, text="自动复制路径到剪贴板", 
                      variable=self.copy_path_var).pack(anchor=tk.W)
        
        self.show_preview_var = tk.BooleanVar()
        tk.Checkbutton(options_frame, text="显示预览窗口", 
                      variable=self.show_preview_var).pack(anchor=tk.W)
        
        # 热键设置
        hotkey_frame = tk.LabelFrame(main_frame, text="热键设置", pady=10)
        hotkey_frame.pack(fill=tk.X, pady=10)
        
        # 热键输入
        hk_input_frame = tk.Frame(hotkey_frame)
        hk_input_frame.pack(fill=tk.X, padx=10, pady=5)
        
        tk.Label(hk_input_frame, text="热键:").pack(side=tk.LEFT)
        self.hotkey_var = tk.StringVar()
        self.hotkey_entry = tk.Entry(hk_input_frame, textvariable=self.hotkey_var, width=20)
        self.hotkey_entry.pack(side=tk.LEFT, padx=5)
        
        # 热键控制按钮
        hk_control_frame = tk.Frame(hotkey_frame)
        hk_control_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.hotkey_status_label = tk.Label(hk_control_frame, text="热键未启用", fg="red")
        self.hotkey_status_label.pack(side=tk.LEFT)
        
        self.hotkey_toggle_btn = tk.Button(hk_control_frame, text="启用热键", 
                                          command=self.toggle_hotkey)
        self.hotkey_toggle_btn.pack(side=tk.RIGHT, padx=5)
        
        if not HOTKEY_AVAILABLE:
            self.hotkey_entry.config(state=tk.DISABLED)
            self.hotkey_toggle_btn.config(state=tk.DISABLED)
            self.hotkey_status_label.config(text="热键功能不可用（需要keyboard库）", fg="gray")
        
        # 截图按钮
        button_frame = tk.LabelFrame(main_frame, text="截图操作", pady=10)
        button_frame.pack(fill=tk.X, pady=10)
        
        tk.Button(button_frame, text="📸 全屏截图 (所有屏幕)", 
                 command=lambda: self.take_screenshot('all'),
                 font=("Arial", 12), height=2, bg="#28a745", fg="white").pack(fill=tk.X, padx=10, pady=5)
        
        tk.Button(button_frame, text="🖱️ 鼠标所在屏幕截图", 
                 command=lambda: self.take_screenshot('mouse'),
                 font=("Arial", 12), height=2, bg="#17a2b8", fg="white").pack(fill=tk.X, padx=10, pady=5)
        
        # 提示
        tip_frame = tk.Frame(main_frame)
        tip_frame.pack(fill=tk.X, pady=10)
        
        tk.Label(tip_frame, text="💡 提示：截图时按 ESC 键取消", 
                font=("Arial", 10), fg="gray").pack()
        
        # 工具栏（在滚动区域内）
        toolbar_frame = tk.LabelFrame(main_frame, text="工具栏", pady=10)
        toolbar_frame.pack(fill=tk.X, pady=10)
        
        # 第一行按钮
        toolbar_row1 = tk.Frame(toolbar_frame)
        toolbar_row1.pack(pady=5)
        
        tk.Button(toolbar_row1, text="📁 打开目录", command=self.open_screenshot_folder, 
                 bg="#17a2b8", fg="white", width=12, height=2).pack(side=tk.LEFT, padx=5)
        tk.Button(toolbar_row1, text="🗑️ 清理截图", command=self.clean_screenshots,
                 bg="#dc3545", fg="white", width=12, height=2).pack(side=tk.LEFT, padx=5)
        tk.Button(toolbar_row1, text="💾 保存设置", command=self.save_settings,
                 bg="#28a745", fg="white", width=12, height=2).pack(side=tk.LEFT, padx=5)
        
        # 第二行按钮
        toolbar_row2 = tk.Frame(toolbar_frame)
        toolbar_row2.pack(pady=5)
        
        tk.Button(toolbar_row2, text="❌ 退出", command=self.on_closing,
                 bg="#6c757d", fg="white", width=12, height=2).pack()
        
        # 为所有主要组件绑定鼠标滚轮
        for widget in [main_frame, info_frame, settings_frame, hotkey_frame, button_frame, tip_frame, toolbar_frame, dir_tip_frame]:
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
        directory = filedialog.askdirectory(initialdir=self.dir_var.get())
        if directory:
            self.dir_var.set(directory)
    
    def on_quality_change(self, event=None):
        """质量选择改变时"""
        quality = self.quality_var.get()
        
        quality_info = {
            "low": "最小文件（~100-500KB）推荐Claude Code使用",
            "medium": "平衡质量（~500KB-2MB）",
            "high": "高质量（2MB+）⚠️"
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
        self.hotkey_var.set(self.config.get("hotkey", "ctrl+shift+s"))
        
        # 触发质量改变事件
        self.on_quality_change()
    
    def save_settings(self):
        """保存设置"""
        self.config.set("save_directory", self.dir_var.get())
        self.config.set("quality_preset", self.quality_var.get())
        self.config.set("auto_copy_path", self.copy_path_var.get())
        self.config.set("show_preview", self.show_preview_var.get())
        self.config.set("hotkey", self.hotkey_var.get())
        
        if self.config.save_config():
            messagebox.showinfo("成功", "设置已保存")
        else:
            messagebox.showerror("错误", "保存设置失败")
    
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
            messagebox.showerror("错误", "请输入热键")
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
                    self.root.after(0, lambda: messagebox.showerror("热键错误", f"热键设置失败: {e}"))
            
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
            self.hotkey_status_label.config(text=f"热键已启用: {self.hotkey_var.get()}", fg="green")
            self.hotkey_toggle_btn.config(text="禁用热键")
        else:
            self.hotkey_status_label.config(text="热键未启用", fg="red")
            self.hotkey_toggle_btn.config(text="启用热键")
    
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
            messagebox.showinfo("信息", f"在目录中未找到截图文件\n\n搜索模式:\n" + 
                              "\n".join([f"• {pattern}" for pattern in screenshot_patterns]))
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
        
        result = messagebox.askyesnocancel("确认清理", confirm_msg, 
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
                messagebox.showinfo("完成", f"成功删除 {deleted_count} 个截图文件\n"
                                           f"释放空间 {size_mb:.2f}MB")
    
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