"""
VPython 3D可视化器
使用VPython实现四元数数据的3D可视化
"""

import asyncio
import logging
import time
import math
import numpy as np
from typing import List, Dict, Any, Optional, Callable
from collections import deque
import threading

try:
    import vpython as vp
    VPYTHON_AVAILABLE = True
except ImportError:
    VPYTHON_AVAILABLE = False
    logging.warning("VPython未安装，3D可视化功能将不可用")

from .quaternion_processor import Quaternion, QuaternionProcessor

logger = logging.getLogger(__name__)


class VPython3DVisualizer:
    """VPython 3D可视化器"""
    
    def __init__(self, config, quaternion_processor: QuaternionProcessor):
        if not VPYTHON_AVAILABLE:
            raise ImportError("VPython未安装，无法使用3D可视化功能")
        
        self.config = config
        self.quaternion_processor = quaternion_processor
        self.running = False
        
        # VPython场景和对象
        self.scene = None
        self.coordinate_frame = None
        self.object_3d = None
        self.trail = None
        self.info_text = None
        
        # 数据历史
        self.quaternion_history = deque(maxlen=500)
        self.euler_history = deque(maxlen=500)
        
        # 可视化设置
        self.show_coordinate_frame = True
        self.show_trail = True
        self.show_info = True
        self.trail_length = 100
        
        # 性能统计
        self.frame_count = 0
        self.last_fps_time = time.time()
        self.fps = 0.0
        
        # 初始化VPython场景
        self._setup_vpython_scene()
    
    def _setup_vpython_scene(self):
        """设置VPython 3D场景"""
        try:
            # 创建场景
            self.scene = vp.canvas(
                title='四元数3D可视化 - USART Trams',
                width=1000,
                height=700,
                background=vp.color.black,
                center=vp.vector(0, 0, 0),
                range=3
            )
            
            # 设置相机
            self.scene.camera.pos = vp.vector(5, 3, 5)
            self.scene.camera.axis = vp.vector(-1, -0.3, -1)
            
            # 创建坐标系
            if self.show_coordinate_frame:
                self._create_coordinate_frame()
            
            # 创建3D对象 (立方体代表传感器)
            self.object_3d = vp.box(
                pos=vp.vector(0, 0, 0),
                size=vp.vector(2, 1, 0.5),
                color=vp.color.cyan,
                opacity=0.8
            )
            
            # 创建轨迹
            if self.show_trail:
                self.trail = vp.curve(
                    color=vp.color.yellow,
                    radius=0.02
                )
            
            # 创建信息显示
            if self.show_info:
                self.info_text = vp.wtext(
                    text="等待数据...\n",
                    pos=self.scene.title_anchor
                )
            
            # 添加控制按钮
            self._add_controls()
            
            logger.info("VPython 3D场景初始化完成")
            
        except Exception as e:
            logger.error(f"VPython场景初始化失败: {e}")
            raise
    
    def _create_coordinate_frame(self):
        """创建坐标系"""
        # X轴 (红色)
        vp.arrow(
            pos=vp.vector(0, 0, 0),
            axis=vp.vector(2, 0, 0),
            color=vp.color.red,
            shaftwidth=0.05
        )
        vp.label(
            pos=vp.vector(2.2, 0, 0),
            text='X',
            color=vp.color.red,
            height=16
        )
        
        # Y轴 (绿色)
        vp.arrow(
            pos=vp.vector(0, 0, 0),
            axis=vp.vector(0, 2, 0),
            color=vp.color.green,
            shaftwidth=0.05
        )
        vp.label(
            pos=vp.vector(0, 2.2, 0),
            text='Y',
            color=vp.color.green,
            height=16
        )
        
        # Z轴 (蓝色)
        vp.arrow(
            pos=vp.vector(0, 0, 0),
            axis=vp.vector(0, 0, 2),
            color=vp.color.blue,
            shaftwidth=0.05
        )
        vp.label(
            pos=vp.vector(0, 0, 2.2),
            text='Z',
            color=vp.color.blue,
            height=16
        )
    
    def _add_controls(self):
        """添加控制按钮"""
        # 重置视图按钮
        def reset_view():
            self.scene.camera.pos = vp.vector(5, 3, 5)
            self.scene.camera.axis = vp.vector(-1, -0.3, -1)
            self.scene.range = 3
        
        # 清空轨迹按钮
        def clear_trail():
            if self.trail:
                self.trail.clear()
        
        # 切换轨迹显示
        def toggle_trail():
            self.show_trail = not self.show_trail
            if self.trail:
                self.trail.visible = self.show_trail
        
        # 添加按钮到场景
        self.scene.append_to_caption('\n\n')
        
        reset_button = vp.button(
            text="重置视图",
            bind=lambda: reset_view()
        )
        
        clear_button = vp.button(
            text="清空轨迹",
            bind=lambda: clear_trail()
        )
        
        trail_button = vp.button(
            text="切换轨迹",
            bind=lambda: toggle_trail()
        )
    
    async def start(self):
        """启动3D可视化"""
        self.running = True
        logger.info("启动VPython 3D可视化...")
        
        try:
            # 启动更新任务
            update_task = asyncio.create_task(self._update_visualization())
            fps_task = asyncio.create_task(self._update_fps())
            
            await asyncio.gather(
                update_task,
                fps_task,
                return_exceptions=True
            )
            
        except Exception as e:
            logger.error(f"3D可视化异常: {e}")
    
    async def stop(self):
        """停止3D可视化"""
        self.running = False
        logger.info("停止VPython 3D可视化")
    
    async def _update_visualization(self):
        """更新3D可视化"""
        while self.running:
            try:
                # 获取最新四元数
                latest_quat = self.quaternion_processor.get_latest_quaternion()
                
                if latest_quat:
                    # 更新3D对象姿态
                    self._update_object_orientation(latest_quat)
                    
                    # 更新轨迹
                    if self.show_trail and self.trail:
                        self._update_trail(latest_quat)
                    
                    # 更新信息显示
                    if self.show_info:
                        self._update_info_display(latest_quat)
                    
                    # 保存历史数据
                    self.quaternion_history.append(latest_quat)
                    
                    # 更新帧计数
                    self.frame_count += 1
                
                # 控制更新频率 (约120 FPS)
                await asyncio.sleep(1/120)
                
            except Exception as e:
                logger.error(f"更新3D可视化时发生错误: {e}")
                await asyncio.sleep(0.1)
    
    def _update_object_orientation(self, quaternion: Quaternion):
        """更新3D对象的方向"""
        try:
            # 将四元数转换为旋转矩阵
            rotation_matrix = quaternion.to_rotation_matrix()
            
            # 计算新的方向向量
            # VPython使用右手坐标系
            forward = vp.vector(rotation_matrix[0, 0], rotation_matrix[0, 1], rotation_matrix[0, 2])
            up = vp.vector(rotation_matrix[1, 0], rotation_matrix[1, 1], rotation_matrix[1, 2])
            
            # 更新对象方向
            self.object_3d.axis = forward * 2  # 长度为2
            self.object_3d.up = up
            
        except Exception as e:
            logger.error(f"更新对象方向时发生错误: {e}")
    
    def _update_trail(self, quaternion: Quaternion):
        """更新轨迹显示"""
        try:
            # 计算轨迹点位置 (基于四元数的某个特征)
            # 这里使用四元数的向量部分作为轨迹点
            trail_point = vp.vector(quaternion.x, quaternion.y, quaternion.z)
            
            # 添加轨迹点
            self.trail.append(trail_point)
            
            # 限制轨迹长度 - VPython 7.6+使用不同的API
            try:
                # 新版本VPython使用pos属性
                if hasattr(self.trail, 'pos') and len(self.trail.pos) > self.trail_length:
                    # 保留最后的轨迹点
                    recent_points = self.trail.pos[-self.trail_length:]
                    self.trail.clear()
                    for point in recent_points:
                        self.trail.append(point)
            except AttributeError:
                # 如果API不兼容，忽略轨迹长度限制
                pass
            
        except Exception as e:
            logger.error(f"更新轨迹时发生错误: {e}")
    
    def _update_info_display(self, quaternion: Quaternion):
        """更新信息显示"""
        try:
            # 获取欧拉角
            roll, pitch, yaw = quaternion.to_euler_angles()
            
            # 获取统计信息
            stats = self.quaternion_processor.get_statistics()
            
            # 格式化信息文本
            info_text = f"""
四元数: w={quaternion.w:.4f}, x={quaternion.x:.4f}, y={quaternion.y:.4f}, z={quaternion.z:.4f}
欧拉角 (度): Roll={math.degrees(roll):.2f}°, Pitch={math.degrees(pitch):.2f}°, Yaw={math.degrees(yaw):.2f}°
欧拉角 (弧度): Roll={roll:.4f}, Pitch={pitch:.4f}, Yaw={yaw:.4f}
FPS: {self.fps:.1f}
数据包: {stats['valid_packets']}/{stats['total_packets']} (成功率: {stats['success_rate']:.1f}%)
历史记录: {len(self.quaternion_history)} 个四元数
            """.strip()
            
            self.info_text.text = info_text
            
        except Exception as e:
            logger.error(f"更新信息显示时发生错误: {e}")
    
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
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取可视化统计信息"""
        return {
            'fps': self.fps,
            'frame_count': self.frame_count,
            'quaternion_history_size': len(self.quaternion_history),
            'show_trail': self.show_trail,
            'show_info': self.show_info,
            'trail_length': self.trail_length
        }
    
    def set_trail_length(self, length: int):
        """设置轨迹长度"""
        self.trail_length = max(10, min(length, 1000))
        logger.info(f"轨迹长度设置为: {self.trail_length}")
    
    def toggle_coordinate_frame(self):
        """切换坐标系显示"""
        self.show_coordinate_frame = not self.show_coordinate_frame
        # 注意：VPython中已创建的对象无法轻易隐藏，需要重新创建场景
        logger.info(f"坐标系显示: {'开启' if self.show_coordinate_frame else '关闭'}")
    
    def save_screenshot(self, filename: str = None):
        """保存截图"""
        try:
            if filename is None:
                timestamp = int(time.time())
                filename = f"quaternion_3d_{timestamp}.png"
            
            # VPython截图功能
            self.scene.capture(filename)
            logger.info(f"截图已保存: {filename}")
            
        except Exception as e:
            logger.error(f"保存截图时发生错误: {e}")


def run_vpython_in_thread(visualizer):
    """在单独线程中运行VPython"""
    try:
        # VPython需要在主线程中运行，这里提供一个包装函数
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(visualizer.start())
    except Exception as e:
        logger.error(f"VPython线程运行异常: {e}")
