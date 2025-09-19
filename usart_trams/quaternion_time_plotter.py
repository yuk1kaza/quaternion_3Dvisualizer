#!/usr/bin/env python3
"""
四元数时间轴绘图工具
实时绘制串口传来的四元数数据随时间变化的曲线图
支持手动选择端口号和波特率
"""

import asyncio
import logging
import sys
import time
import numpy as np
from pathlib import Path
from collections import deque
import threading
import tkinter as tk
from tkinter import ttk, messagebox
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import serial.tools.list_ports

# 添加src目录到路径
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from src.config import Config
from src.serial_manager import SerialManager
from src.quaternion_processor import QuaternionProcessor

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class QuaternionTimePlotter:
    """四元数时间轴绘图器"""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("四元数时间轴绘图工具")
        self.root.geometry("1200x800")
        
        # 数据存储 - 移除长度限制，保持所有历史数据
        self.time_data = []  # 保存所有时间数据
        self.w_data = []     # 保存所有W分量数据
        self.x_data = []     # 保存所有X分量数据
        self.y_data = []     # 保存所有Y分量数据
        self.z_data = []     # 保存所有Z分量数据

        # 显示控制
        self.show_all_data = True  # 是否显示所有数据
        self.window_size = 30      # 滚动窗口大小（秒）
        
        # 状态变量
        self.is_running = False
        self.start_time = None
        self.data_count = 0
        self.serial_manager = None
        self.quaternion_processor = None
        
        # 创建界面
        self.create_widgets()
        self.setup_plot()
        
        # 扫描可用端口
        self.scan_ports()
        
    def create_widgets(self):
        """创建界面组件"""
        # 控制面板
        control_frame = ttk.Frame(self.root)
        control_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # 端口选择
        ttk.Label(control_frame, text="串口:").grid(row=0, column=0, padx=5)
        self.port_var = tk.StringVar()
        self.port_combo = ttk.Combobox(control_frame, textvariable=self.port_var, width=10)
        self.port_combo.grid(row=0, column=1, padx=5)
        
        # 波特率选择
        ttk.Label(control_frame, text="波特率:").grid(row=0, column=2, padx=5)
        self.baudrate_var = tk.StringVar(value="115200")
        baudrate_combo = ttk.Combobox(control_frame, textvariable=self.baudrate_var, width=10)
        baudrate_combo['values'] = ('9600', '19200', '38400', '57600', '115200', '128000', '230400', '460800', '921600')
        baudrate_combo.grid(row=0, column=3, padx=5)
        
        # 数据格式选择
        ttk.Label(control_frame, text="数据格式:").grid(row=0, column=4, padx=5)
        self.format_var = tk.StringVar(value="ascii")
        format_combo = ttk.Combobox(control_frame, textvariable=self.format_var, width=10)
        format_combo['values'] = ('ascii', 'binary')
        format_combo.grid(row=0, column=5, padx=5)
        
        # 控制按钮
        self.start_button = ttk.Button(control_frame, text="开始", command=self.start_plotting)
        self.start_button.grid(row=0, column=6, padx=5)
        
        self.stop_button = ttk.Button(control_frame, text="停止", command=self.stop_plotting, state=tk.DISABLED)
        self.stop_button.grid(row=0, column=7, padx=5)
        
        self.clear_button = ttk.Button(control_frame, text="清空", command=self.clear_data)
        self.clear_button.grid(row=0, column=8, padx=5)
        
        self.refresh_button = ttk.Button(control_frame, text="刷新端口", command=self.scan_ports)
        self.refresh_button.grid(row=0, column=9, padx=5)

        # 显示模式控制
        ttk.Label(control_frame, text="显示模式:").grid(row=0, column=10, padx=5)
        self.display_mode_var = tk.StringVar(value="all")
        display_mode_combo = ttk.Combobox(control_frame, textvariable=self.display_mode_var, width=8)
        display_mode_combo['values'] = ('all', 'window')
        display_mode_combo.grid(row=0, column=11, padx=5)
        display_mode_combo.bind('<<ComboboxSelected>>', self.on_display_mode_change)

        # 窗口大小控制
        ttk.Label(control_frame, text="窗口(秒):").grid(row=0, column=12, padx=5)
        self.window_size_var = tk.StringVar(value="30")
        window_size_entry = ttk.Entry(control_frame, textvariable=self.window_size_var, width=6)
        window_size_entry.grid(row=0, column=13, padx=5)
        window_size_entry.bind('<Return>', self.on_window_size_change)
        
        # 状态显示
        status_frame = ttk.Frame(self.root)
        status_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.status_label = ttk.Label(status_frame, text="状态: 未连接")
        self.status_label.pack(side=tk.LEFT)
        
        self.data_label = ttk.Label(status_frame, text="数据: 0")
        self.data_label.pack(side=tk.LEFT, padx=20)
        
        self.rate_label = ttk.Label(status_frame, text="速率: 0 Hz")
        self.rate_label.pack(side=tk.LEFT, padx=20)
        
    def setup_plot(self):
        """设置绘图区域"""
        # 创建matplotlib图形
        self.fig, self.axes = plt.subplots(2, 2, figsize=(12, 8))
        self.fig.suptitle('quaternion-time-plotter', fontsize=16)
        
        # 设置子图
        self.axes[0, 0].set_title('W')
        self.axes[0, 0].set_ylabel('W')
        self.axes[0, 0].grid(True)
        
        self.axes[0, 1].set_title('X')
        self.axes[0, 1].set_ylabel('X')
        self.axes[0, 1].grid(True)
        
        self.axes[1, 0].set_title('Y')
        self.axes[1, 0].set_ylabel('Y')
        self.axes[1, 0].set_xlabel('t (s)')
        self.axes[1, 0].grid(True)
        
        self.axes[1, 1].set_title('Z')
        self.axes[1, 1].set_ylabel('Z')
        self.axes[1, 1].set_xlabel('t (s)')
        self.axes[1, 1].grid(True)
        
        # 初始化线条
        self.w_line, = self.axes[0, 0].plot([], [], 'r-', linewidth=1.5, label='W')
        self.x_line, = self.axes[0, 1].plot([], [], 'g-', linewidth=1.5, label='X')
        self.y_line, = self.axes[1, 0].plot([], [], 'b-', linewidth=1.5, label='Y')
        self.z_line, = self.axes[1, 1].plot([], [], 'm-', linewidth=1.5, label='Z')
        
        # 设置坐标轴范围
        for ax in self.axes.flat:
            ax.set_xlim(0, 30)  # 显示最近30秒
            ax.set_ylim(-1.2, 1.2)  # 四元数范围
        
        # 嵌入到tkinter
        self.canvas = FigureCanvasTkAgg(self.fig, self.root)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # 启动动画
        self.animation = FuncAnimation(self.fig, self.update_plot, interval=50, blit=False)
        
    def scan_ports(self):
        """扫描可用串口"""
        ports = serial.tools.list_ports.comports()
        port_list = [port.device for port in ports]
        
        self.port_combo['values'] = port_list
        if port_list:
            self.port_combo.set(port_list[0])
        
        logger.info(f"发现 {len(port_list)} 个串口: {port_list}")

    def on_display_mode_change(self, event=None):
        """显示模式改变回调"""
        mode = self.display_mode_var.get()
        self.show_all_data = (mode == "all")
        logger.info(f"显示模式切换为: {'全部数据' if self.show_all_data else '滚动窗口'}")

    def on_window_size_change(self, event=None):
        """窗口大小改变回调"""
        try:
            self.window_size = float(self.window_size_var.get())
            logger.info(f"窗口大小设置为: {self.window_size}秒")
        except ValueError:
            self.window_size_var.set(str(self.window_size))
            logger.warning("无效的窗口大小，已恢复默认值")

    def start_plotting(self):
        """开始绘图"""
        if self.is_running:
            return
            
        port = self.port_var.get()
        baudrate = int(self.baudrate_var.get())
        data_format = self.format_var.get()
        
        if not port:
            messagebox.showerror("错误", "请选择串口")
            return
            
        try:
            # 配置串口和数据处理
            config = Config()
            config.serial.port = port
            config.serial.baudrate = baudrate
            config.serial.timeout = 0.1
            config.processing.data_format = data_format
            config.processing.enable_filtering = False  # 绘图时不使用滤波
            
            # 初始化处理器
            self.quaternion_processor = QuaternionProcessor(config)
            self.quaternion_processor.set_data_format(data_format)
            self.serial_manager = SerialManager(config, self.process_data)
            
            # 启动数据处理线程
            self.start_time = time.time()
            self.data_count = 0
            self.is_running = True
            
            # 启动异步数据处理
            self.data_thread = threading.Thread(target=self.run_data_processing, daemon=True)
            self.data_thread.start()
            
            # 更新界面
            self.start_button.config(state=tk.DISABLED)
            self.stop_button.config(state=tk.NORMAL)
            self.status_label.config(text=f"状态: 已连接 {port} @ {baudrate}")
            
            logger.info(f"开始绘图: {port} @ {baudrate} baud, 格式: {data_format}")
            
        except Exception as e:
            messagebox.showerror("错误", f"启动失败: {e}")
            logger.error(f"启动绘图失败: {e}")
            
    def stop_plotting(self):
        """停止绘图"""
        if not self.is_running:
            return
            
        self.is_running = False
        
        if self.serial_manager:
            try:
                # 停止串口管理器
                asyncio.run(self.serial_manager.stop())
            except:
                pass
            
        # 更新界面
        self.start_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
        self.status_label.config(text="状态: 已断开")
        
        logger.info("绘图已停止")
        
    def clear_data(self):
        """清空数据"""
        self.time_data = []
        self.w_data = []
        self.x_data = []
        self.y_data = []
        self.z_data = []
        
        self.data_count = 0
        self.start_time = time.time()
        
        self.data_label.config(text="数据: 0")
        self.rate_label.config(text="速率: 0 Hz")
        
        logger.info("数据已清空")
        
    def run_data_processing(self):
        """运行数据处理"""
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self.serial_manager.start())
        except Exception as e:
            logger.error(f"数据处理异常: {e}")
        finally:
            loop.close()
            
    async def process_data(self, raw_data: bytes):
        """处理数据"""
        try:
            processed_data = self.quaternion_processor.process_raw_data(raw_data)
            
            if processed_data:
                current_time = time.time()
                
                for data_point in processed_data:
                    self.data_count += 1
                    
                    # 添加数据点 - 保存所有历史数据
                    relative_time = current_time - self.start_time
                    quat = data_point['quaternion']

                    self.time_data.append(relative_time)
                    self.w_data.append(quat['w'])
                    self.x_data.append(quat['x'])
                    self.y_data.append(quat['y'])
                    self.z_data.append(quat['z'])
                    
                # 更新状态显示
                elapsed = current_time - self.start_time
                rate = self.data_count / elapsed if elapsed > 0 else 0
                
                self.root.after(0, lambda: self.data_label.config(text=f"数据: {self.data_count}"))
                self.root.after(0, lambda: self.rate_label.config(text=f"速率: {rate:.1f} Hz"))
                
        except Exception as e:
            logger.error(f"处理数据异常: {e}")
            
    def update_plot(self, frame):
        """更新绘图 - 支持全部数据和滚动窗口两种模式"""
        if not self.time_data:
            return

        # 转换为numpy数组
        times = np.array(self.time_data)
        w_vals = np.array(self.w_data)
        x_vals = np.array(self.x_data)
        y_vals = np.array(self.y_data)
        z_vals = np.array(self.z_data)

        # 根据显示模式选择数据范围
        if self.show_all_data:
            # 显示所有历史数据
            display_times = times
            display_w = w_vals
            display_x = x_vals
            display_y = y_vals
            display_z = z_vals

            # 设置X轴范围为全部数据
            if len(times) > 0:
                x_min = max(0, times[0] - 1)
                x_max = times[-1] + 1
                for ax in self.axes.flat:
                    ax.set_xlim(x_min, x_max)
        else:
            # 滚动窗口模式
            if len(times) > 0:
                max_time = times[-1]
                # 找到窗口范围内的数据
                window_start = max_time - self.window_size
                mask = times >= window_start

                display_times = times[mask]
                display_w = w_vals[mask]
                display_x = x_vals[mask]
                display_y = y_vals[mask]
                display_z = z_vals[mask]

                # 设置X轴范围为窗口大小
                for ax in self.axes.flat:
                    ax.set_xlim(window_start, max_time + 1)
            else:
                display_times = times
                display_w = w_vals
                display_x = x_vals
                display_y = y_vals
                display_z = z_vals

        # 更新线条数据
        self.w_line.set_data(display_times, display_w)
        self.x_line.set_data(display_times, display_x)
        self.y_line.set_data(display_times, display_y)
        self.z_line.set_data(display_times, display_z)

        # 动态调整Y轴范围以适应数据
        if len(display_w) > 0:
            all_vals = np.concatenate([display_w, display_x, display_y, display_z])
            y_min = np.min(all_vals) - 0.1
            y_max = np.max(all_vals) + 0.1

            for ax in self.axes.flat:
                ax.set_ylim(y_min, y_max)

        return self.w_line, self.x_line, self.y_line, self.z_line
        
    def on_closing(self):
        """关闭程序"""
        if self.is_running:
            self.stop_plotting()
        self.root.quit()
        self.root.destroy()
        
    def run(self):
        """运行程序"""
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.root.mainloop()


def main():
    """主函数"""
    print("""
📊 四元数时间轴绘图工具 - 增强版
===============================

功能特性:
✅ 实时绘制四元数四个分量的时间轴曲线
✅ 支持手动选择串口和波特率
✅ 支持ASCII和二进制数据格式
✅ 两种显示模式：全部历史数据 / 滚动窗口
✅ 可调节滚动窗口大小
✅ 自动Y轴缩放适应数据范围
✅ 实时数据速率监控

操作说明:
1. 选择串口和波特率
2. 选择数据格式
3. 选择显示模式：
   - "all": 显示所有历史数据，便于观察长期趋势
   - "window": 滚动窗口模式，专注最新数据
4. 设置窗口大小（滚动模式下有效）
5. 点击"开始"按钮
6. 观察实时四元数曲线图

启动图形界面...
""")
    
    try:
        app = QuaternionTimePlotter()
        app.run()
    except Exception as e:
        logger.error(f"程序异常: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
