"""
四元数数据图表可视化器
使用matplotlib实现四元数和欧拉角的实时图表显示
"""

import asyncio
import logging
import time
import math
import numpy as np
from typing import List, Dict, Any, Optional
from collections import deque
import threading

try:
    import matplotlib.pyplot as plt
    import matplotlib.animation as animation
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    import tkinter as tk
    from tkinter import ttk
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    logging.warning("matplotlib或tkinter未安装，图表可视化功能将不可用")

from .quaternion_processor import Quaternion, QuaternionProcessor

logger = logging.getLogger(__name__)


class QuaternionPlotter:
    """四元数数据图表可视化器"""
    
    def __init__(self, config, quaternion_processor: QuaternionProcessor):
        if not MATPLOTLIB_AVAILABLE:
            raise ImportError("matplotlib未安装，无法使用图表可视化功能")
        
        self.config = config
        self.quaternion_processor = quaternion_processor
        self.running = False
        
        # 数据历史
        self.max_points = 500
        self.time_data = deque(maxlen=self.max_points)
        self.quaternion_data = {
            'w': deque(maxlen=self.max_points),
            'x': deque(maxlen=self.max_points),
            'y': deque(maxlen=self.max_points),
            'z': deque(maxlen=self.max_points)
        }
        self.euler_data = {
            'roll': deque(maxlen=self.max_points),
            'pitch': deque(maxlen=self.max_points),
            'yaw': deque(maxlen=self.max_points)
        }
        
        # GUI组件
        self.root = None
        self.fig = None
        self.axes = None
        self.canvas = None
        self.animation = None
        
        # 图表设置
        self.show_quaternion = True
        self.show_euler = True
        self.use_degrees = True
        self.auto_scale = True
        
        # 性能统计
        self.update_count = 0
        self.last_update_time = time.time()
        
        # 初始化GUI
        self._setup_gui()
    
    def _setup_gui(self):
        """设置GUI界面"""
        try:
            # 创建主窗口
            self.root = tk.Tk()
            self.root.title("四元数数据图表 - USART Trams")
            self.root.geometry("1200x800")
            
            # 创建控制面板
            control_frame = ttk.Frame(self.root)
            control_frame.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)
            
            # 添加控制按钮
            self._add_control_buttons(control_frame)
            
            # 创建图表
            self._create_plots()
            
            # 设置matplotlib样式
            plt.style.use('dark_background')
            
            logger.info("四元数图表GUI初始化完成")
            
        except Exception as e:
            logger.error(f"GUI初始化失败: {e}")
            raise
    
    def _add_control_buttons(self, parent):
        """添加控制按钮"""
        # 开始/停止按钮
        self.start_button = ttk.Button(
            parent,
            text="开始",
            command=self._toggle_plotting
        )
        self.start_button.pack(side=tk.LEFT, padx=5)
        
        # 清空数据按钮
        clear_button = ttk.Button(
            parent,
            text="清空数据",
            command=self._clear_data
        )
        clear_button.pack(side=tk.LEFT, padx=5)
        
        # 保存图表按钮
        save_button = ttk.Button(
            parent,
            text="保存图表",
            command=self._save_plot
        )
        save_button.pack(side=tk.LEFT, padx=5)
        
        # 显示选项
        ttk.Label(parent, text="Display:").pack(side=tk.LEFT, padx=(20, 5))

        self.show_quat_var = tk.BooleanVar(value=True)
        quat_check = ttk.Checkbutton(
            parent,
            text="Quaternion",
            variable=self.show_quat_var,
            command=self._update_display_options
        )
        quat_check.pack(side=tk.LEFT, padx=5)

        self.show_euler_var = tk.BooleanVar(value=True)
        euler_check = ttk.Checkbutton(
            parent,
            text="Euler Angles",
            variable=self.show_euler_var,
            command=self._update_display_options
        )
        euler_check.pack(side=tk.LEFT, padx=5)

        # 角度单位选择
        ttk.Label(parent, text="Unit:").pack(side=tk.LEFT, padx=(20, 5))
        
        self.angle_unit_var = tk.StringVar(value="Degrees")
        angle_combo = ttk.Combobox(
            parent,
            textvariable=self.angle_unit_var,
            values=["Degrees", "Radians"],
            width=8,
            state="readonly"
        )
        angle_combo.pack(side=tk.LEFT, padx=5)
        angle_combo.bind('<<ComboboxSelected>>', self._update_angle_unit)

        # 状态标签
        self.status_label = ttk.Label(parent, text="Status: Waiting for data...")
        self.status_label.pack(side=tk.RIGHT, padx=5)
    
    def _create_plots(self):
        """创建图表"""
        # 创建图形和子图
        self.fig, self.axes = plt.subplots(2, 1, figsize=(12, 8))
        self.fig.patch.set_facecolor('black')
        
        # 四元数子图
        self.quat_ax = self.axes[0]
        self.quat_ax.set_title('Quaternion (w, x, y, z)', color='white', fontsize=14)
        self.quat_ax.set_ylabel('Value', color='white')
        self.quat_ax.grid(True, alpha=0.3)
        self.quat_ax.set_facecolor('black')

        # 欧拉角子图
        self.euler_ax = self.axes[1]
        self.euler_ax.set_title('Euler Angles (Roll, Pitch, Yaw)', color='white', fontsize=14)
        self.euler_ax.set_xlabel('Time (seconds)', color='white')
        self.euler_ax.set_ylabel('Angle', color='white')
        self.euler_ax.grid(True, alpha=0.3)
        self.euler_ax.set_facecolor('black')
        
        # 设置颜色
        for ax in self.axes:
            ax.tick_params(colors='white')
            ax.spines['bottom'].set_color('white')
            ax.spines['top'].set_color('white')
            ax.spines['right'].set_color('white')
            ax.spines['left'].set_color('white')
        
        # 初始化线条
        self.quat_lines = {
            'w': self.quat_ax.plot([], [], 'r-', label='w', linewidth=2)[0],
            'x': self.quat_ax.plot([], [], 'g-', label='x', linewidth=2)[0],
            'y': self.quat_ax.plot([], [], 'b-', label='y', linewidth=2)[0],
            'z': self.quat_ax.plot([], [], 'y-', label='z', linewidth=2)[0]
        }
        
        self.euler_lines = {
            'roll': self.euler_ax.plot([], [], 'r-', label='Roll', linewidth=2)[0],
            'pitch': self.euler_ax.plot([], [], 'g-', label='Pitch', linewidth=2)[0],
            'yaw': self.euler_ax.plot([], [], 'b-', label='Yaw', linewidth=2)[0]
        }
        
        # 添加图例
        self.quat_ax.legend(loc='upper right')
        self.euler_ax.legend(loc='upper right')
        
        # 创建画布
        self.canvas = FigureCanvasTkAgg(self.fig, self.root)
        self.canvas.get_tk_widget().pack(side=tk.BOTTOM, fill=tk.BOTH, expand=True)
        
        # 紧凑布局
        plt.tight_layout()
    
    def _toggle_plotting(self):
        """切换绘图状态"""
        if self.running:
            self.stop()
            self.start_button.config(text="开始")
        else:
            asyncio.create_task(self.start())
            self.start_button.config(text="停止")
    
    def _clear_data(self):
        """清空数据"""
        self.time_data.clear()
        for key in self.quaternion_data:
            self.quaternion_data[key].clear()
        for key in self.euler_data:
            self.euler_data[key].clear()
        
        # 清空图表
        for line in self.quat_lines.values():
            line.set_data([], [])
        for line in self.euler_lines.values():
            line.set_data([], [])
        
        self.canvas.draw()
        logger.info("图表数据已清空")
    
    def _save_plot(self):
        """保存图表"""
        try:
            timestamp = int(time.time())
            filename = f"quaternion_plot_{timestamp}.png"
            self.fig.savefig(filename, dpi=300, bbox_inches='tight', 
                           facecolor='black', edgecolor='white')
            logger.info(f"图表已保存: {filename}")
            self.status_label.config(text=f"图表已保存: {filename}")
        except Exception as e:
            logger.error(f"保存图表时发生错误: {e}")
    
    def _update_display_options(self):
        """更新显示选项"""
        self.show_quaternion = self.show_quat_var.get()
        self.show_euler = self.show_euler_var.get()
        
        # 显示/隐藏子图
        if self.show_quaternion and self.show_euler:
            self.quat_ax.set_visible(True)
            self.euler_ax.set_visible(True)
        elif self.show_quaternion:
            self.quat_ax.set_visible(True)
            self.euler_ax.set_visible(False)
        elif self.show_euler:
            self.quat_ax.set_visible(False)
            self.euler_ax.set_visible(True)
        else:
            # 至少显示一个
            self.show_quat_var.set(True)
            self.show_quaternion = True
        
        self.canvas.draw()
    
    def _update_angle_unit(self, event=None):
        """更新角度单位"""
        self.use_degrees = (self.angle_unit_var.get() == "Degrees")
        unit_text = "Degrees" if self.use_degrees else "Radians"
        self.euler_ax.set_ylabel(f'Angle ({unit_text})', color='white')
        self.canvas.draw()
    
    async def start(self):
        """启动图表绘制"""
        self.running = True
        logger.info("启动四元数图表绘制...")
        
        try:
            # 启动数据更新任务
            update_task = asyncio.create_task(self._update_data())
            plot_task = asyncio.create_task(self._update_plots())
            
            await asyncio.gather(
                update_task,
                plot_task,
                return_exceptions=True
            )
            
        except Exception as e:
            logger.error(f"图表绘制异常: {e}")
    
    async def stop(self):
        """停止图表绘制"""
        self.running = False
        logger.info("停止四元数图表绘制")
    
    async def _update_data(self):
        """更新数据"""
        start_time = time.time()
        
        while self.running:
            try:
                # 获取最新四元数
                latest_quat = self.quaternion_processor.get_latest_quaternion()
                
                if latest_quat:
                    current_time = time.time() - start_time
                    
                    # 添加时间数据
                    self.time_data.append(current_time)
                    
                    # 添加四元数数据
                    self.quaternion_data['w'].append(latest_quat.w)
                    self.quaternion_data['x'].append(latest_quat.x)
                    self.quaternion_data['y'].append(latest_quat.y)
                    self.quaternion_data['z'].append(latest_quat.z)
                    
                    # 添加欧拉角数据
                    roll, pitch, yaw = latest_quat.to_euler_angles()
                    
                    if self.use_degrees:
                        roll = math.degrees(roll)
                        pitch = math.degrees(pitch)
                        yaw = math.degrees(yaw)
                    
                    self.euler_data['roll'].append(roll)
                    self.euler_data['pitch'].append(pitch)
                    self.euler_data['yaw'].append(yaw)
                    
                    self.update_count += 1
                
                # 控制更新频率
                await asyncio.sleep(0.05)  # 20 Hz
                
            except Exception as e:
                logger.error(f"更新数据时发生错误: {e}")
                await asyncio.sleep(0.1)
    
    async def _update_plots(self):
        """更新图表"""
        while self.running:
            try:
                if len(self.time_data) > 1:
                    time_array = np.array(self.time_data)
                    
                    # 更新四元数图表
                    if self.show_quaternion:
                        for key, line in self.quat_lines.items():
                            data_array = np.array(self.quaternion_data[key])
                            line.set_data(time_array, data_array)
                        
                        # 自动缩放
                        if self.auto_scale:
                            self.quat_ax.relim()
                            self.quat_ax.autoscale_view()
                    
                    # 更新欧拉角图表
                    if self.show_euler:
                        for key, line in self.euler_lines.items():
                            data_array = np.array(self.euler_data[key])
                            line.set_data(time_array, data_array)
                        
                        # 自动缩放
                        if self.auto_scale:
                            self.euler_ax.relim()
                            self.euler_ax.autoscale_view()
                    
                    # 重绘画布
                    self.canvas.draw()
                    
                    # 更新状态
                    stats = self.quaternion_processor.get_statistics()
                    status_text = f"数据点: {len(self.time_data)}, 成功率: {stats['success_rate']:.1f}%"
                    self.status_label.config(text=status_text)
                
                # 控制绘图频率
                await asyncio.sleep(1/30)  # 30 FPS
                
            except Exception as e:
                logger.error(f"更新图表时发生错误: {e}")
                await asyncio.sleep(0.1)
    
    def run_gui(self):
        """运行GUI主循环"""
        try:
            self.root.mainloop()
        except Exception as e:
            logger.error(f"GUI运行异常: {e}")
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            'update_count': self.update_count,
            'data_points': len(self.time_data),
            'show_quaternion': self.show_quaternion,
            'show_euler': self.show_euler,
            'use_degrees': self.use_degrees,
            'max_points': self.max_points
        }
