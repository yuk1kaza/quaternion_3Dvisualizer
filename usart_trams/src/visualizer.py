"""
高性能数据可视化器
使用VisPy实现低延迟实时数据显示
"""

import asyncio
import logging
import time
import numpy as np
from typing import List, Dict, Any, Callable
import vispy
from vispy import app, scene
from vispy.scene import visuals
from vispy.color import Color

from .config import Config

logger = logging.getLogger(__name__)

# 设置VisPy后端
vispy.use(app='qt')


class DataVisualizer:
    """高性能数据可视化器"""
    
    def __init__(self, config: Config, data_source: Callable):
        self.config = config
        self.data_source = data_source
        self.running = False
        
        # VisPy组件
        self.canvas = None
        self.view = None
        self.line_visual = None
        self.text_visual = None
        
        # 数据缓存
        self.x_data = np.array([])
        self.y_data = np.array([])
        self.data_index = 0
        
        # 性能统计
        self.frame_count = 0
        self.last_fps_time = time.time()
        self.fps = 0.0
        
        # 显示范围
        self.x_range = [0, self.config.visualization.max_points]
        self.y_range = [-100, 100]  # 自动调整
        
        # 初始化VisPy
        self._setup_vispy()
    
    def _setup_vispy(self):
        """设置VisPy可视化环境"""
        try:
            # 创建画布
            self.canvas = scene.SceneCanvas(
                title='USART Trams - 实时数据监控',
                size=(
                    self.config.visualization.window_width,
                    self.config.visualization.window_height
                ),
                show=True,
                bgcolor=self.config.visualization.background_color
            )
            
            # 创建视图
            self.view = self.canvas.central_widget.add_view()
            self.view.camera = scene.PanZoomCamera(
                rect=(0, -100, self.config.visualization.max_points, 200),
                aspect=None
            )
            
            # 创建网格
            grid = scene.visuals.GridLines(parent=self.view.scene)
            
            # 创建线条可视化
            self.line_visual = scene.visuals.Line(
                parent=self.view.scene,
                color=self.config.visualization.line_color,
                width=self.config.visualization.line_width,
                method='gl'  # 使用OpenGL加速
            )
            
            # 创建文本显示（统计信息）
            if self.config.visualization.show_statistics:
                self.text_visual = scene.visuals.Text(
                    text='',
                    color='white',
                    font_size=12,
                    pos=(10, 30),
                    parent=self.view
                )
            
            # 绑定事件
            self.canvas.events.key_press.connect(self._on_key_press)
            self.canvas.events.resize.connect(self._on_resize)
            
            logger.info("VisPy可视化环境初始化完成")
            
        except Exception as e:
            logger.error(f"VisPy初始化失败: {e}")
            raise
    
    async def start(self):
        """启动可视化"""
        self.running = True
        logger.info("启动数据可视化...")
        
        try:
            # 启动更新任务
            update_task = asyncio.create_task(self._update_visualization())
            fps_task = asyncio.create_task(self._update_fps())
            
            # 启动VisPy事件循环
            app_task = asyncio.create_task(self._run_vispy_app())
            
            await asyncio.gather(
                update_task,
                fps_task,
                app_task,
                return_exceptions=True
            )
            
        except Exception as e:
            logger.error(f"可视化异常: {e}")
    
    async def stop(self):
        """停止可视化"""
        self.running = False
        if self.canvas:
            self.canvas.close()
    
    async def _run_vispy_app(self):
        """运行VisPy应用循环"""
        try:
            # 在单独的线程中运行VisPy应用
            import threading
            
            def run_app():
                app.run()
            
            app_thread = threading.Thread(target=run_app, daemon=True)
            app_thread.start()
            
            # 等待应用线程
            while self.running and app_thread.is_alive():
                await asyncio.sleep(0.1)
                
        except Exception as e:
            logger.error(f"VisPy应用循环异常: {e}")
    
    async def _update_visualization(self):
        """更新可视化数据"""
        while self.running:
            try:
                # 获取最新数据
                data_points = self.data_source()
                
                if data_points:
                    # 更新数据
                    await self._update_data(data_points)
                    
                    # 更新可视化
                    self._update_line_visual()
                    
                    # 更新统计信息
                    if self.config.visualization.show_statistics:
                        self._update_statistics_text()
                    
                    # 更新帧计数
                    self.frame_count += 1
                
                # 控制更新频率
                await asyncio.sleep(self.config.visualization.update_interval)
                
            except Exception as e:
                logger.error(f"更新可视化时发生错误: {e}")
                await asyncio.sleep(0.1)
    
    async def _update_data(self, data_points: List[Dict[str, Any]]):
        """更新数据数组"""
        try:
            if not data_points:
                return
            
            # 提取数值和索引
            new_values = [point['value'] for point in data_points]
            new_indices = [point['index'] for point in data_points]
            
            # 转换为numpy数组
            new_x = np.array(new_indices, dtype=np.float32)
            new_y = np.array(new_values, dtype=np.float32)
            
            # 合并数据
            if len(self.x_data) == 0:
                self.x_data = new_x
                self.y_data = new_y
            else:
                self.x_data = np.concatenate([self.x_data, new_x])
                self.y_data = np.concatenate([self.y_data, new_y])
            
            # 限制数据点数量
            max_points = self.config.visualization.max_points
            if len(self.x_data) > max_points:
                self.x_data = self.x_data[-max_points:]
                self.y_data = self.y_data[-max_points:]
            
            # 自动调整Y轴范围
            if len(self.y_data) > 0:
                y_min, y_max = np.min(self.y_data), np.max(self.y_data)
                y_margin = (y_max - y_min) * 0.1
                self.y_range = [y_min - y_margin, y_max + y_margin]
            
            # 更新X轴范围
            if len(self.x_data) > 0:
                x_min, x_max = np.min(self.x_data), np.max(self.x_data)
                x_margin = max(1, (x_max - x_min) * 0.05)
                self.x_range = [x_min - x_margin, x_max + x_margin]
            
        except Exception as e:
            logger.error(f"更新数据时发生错误: {e}")
    
    def _update_line_visual(self):
        """更新线条可视化"""
        try:
            if len(self.x_data) > 1 and len(self.y_data) > 1:
                # 创建位置数组
                pos = np.column_stack([self.x_data, self.y_data])
                
                # 更新线条数据
                self.line_visual.set_data(pos=pos)
                
                # 更新相机视图
                self.view.camera.rect = (
                    self.x_range[0], self.y_range[0],
                    self.x_range[1] - self.x_range[0],
                    self.y_range[1] - self.y_range[0]
                )
                
                # 请求重绘
                self.canvas.update()
                
        except Exception as e:
            logger.error(f"更新线条可视化时发生错误: {e}")
    
    def _update_statistics_text(self):
        """更新统计信息文本"""
        try:
            if self.text_visual:
                stats_text = (
                    f"FPS: {self.fps:.1f}\n"
                    f"数据点: {len(self.y_data)}\n"
                    f"Y范围: [{self.y_range[0]:.2f}, {self.y_range[1]:.2f}]\n"
                    f"最新值: {self.y_data[-1]:.2f}" if len(self.y_data) > 0 else "无数据"
                )
                self.text_visual.text = stats_text
                
        except Exception as e:
            logger.error(f"更新统计文本时发生错误: {e}")
    
    async def _update_fps(self):
        """更新FPS统计"""
        while self.running:
            try:
                current_time = time.time()
                time_diff = current_time - self.last_fps_time
                
                if time_diff >= 1.0:  # 每秒更新一次FPS
                    self.fps = self.frame_count / time_diff
                    self.frame_count = 0
                    self.last_fps_time = current_time
                
                await asyncio.sleep(1.0)
                
            except Exception as e:
                logger.error(f"更新FPS时发生错误: {e}")
                await asyncio.sleep(1.0)
    
    def _on_key_press(self, event):
        """键盘事件处理"""
        try:
            if event.key == 'r':
                # 重置视图
                self._reset_view()
            elif event.key == 'c':
                # 清空数据
                self._clear_data()
            elif event.key == 's':
                # 保存截图
                self._save_screenshot()
            elif event.key == 'q' or event.key == 'Escape':
                # 退出
                self.canvas.close()
                
        except Exception as e:
            logger.error(f"处理键盘事件时发生错误: {e}")
    
    def _on_resize(self, event):
        """窗口大小改变事件"""
        try:
            # 更新视图大小
            if self.view:
                self.view.camera.aspect = None
                
        except Exception as e:
            logger.error(f"处理窗口大小改变事件时发生错误: {e}")
    
    def _reset_view(self):
        """重置视图"""
        try:
            if len(self.x_data) > 0 and len(self.y_data) > 0:
                self.view.camera.rect = (
                    self.x_range[0], self.y_range[0],
                    self.x_range[1] - self.x_range[0],
                    self.y_range[1] - self.y_range[0]
                )
                self.canvas.update()
                
        except Exception as e:
            logger.error(f"重置视图时发生错误: {e}")
    
    def _clear_data(self):
        """清空数据"""
        try:
            self.x_data = np.array([])
            self.y_data = np.array([])
            self.line_visual.set_data(pos=np.array([]))
            self.canvas.update()
            logger.info("数据已清空")
            
        except Exception as e:
            logger.error(f"清空数据时发生错误: {e}")
    
    def _save_screenshot(self):
        """保存截图"""
        try:
            timestamp = int(time.time())
            filename = f"screenshot_{timestamp}.png"
            
            # 渲染到图像
            img = self.canvas.render()
            
            # 保存图像
            import imageio
            imageio.imwrite(filename, img)
            
            logger.info(f"截图已保存: {filename}")
            
        except Exception as e:
            logger.error(f"保存截图时发生错误: {e}")
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取可视化统计信息"""
        return {
            'fps': self.fps,
            'data_points': len(self.y_data),
            'x_range': self.x_range,
            'y_range': self.y_range,
            'frame_count': self.frame_count
        }
