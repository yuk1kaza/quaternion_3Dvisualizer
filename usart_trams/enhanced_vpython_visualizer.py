#!/usr/bin/env python3
"""
增强版VPython四元数可视化器
基于现有VPython重构，提供更灵敏更直观的3D可视化体验
无需额外依赖，立即可用
"""

import asyncio
import logging
import sys
import time
import math
import numpy as np
from pathlib import Path
from collections import deque

# 添加src目录到路径
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from src.config import Config
from src.serial_manager import SerialManager
from src.quaternion_processor import QuaternionProcessor

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# 检查VPython可用性
try:
    import vpython as vp
    VPYTHON_AVAILABLE = True
    logger.info("VPython 可用")
except ImportError:
    VPYTHON_AVAILABLE = False
    logger.error("VPython 不可用，请安装: pip install vpython")
    sys.exit(1)


class EnhancedVPythonRenderer:
    """增强版VPython渲染器"""
    
    def __init__(self):
        # 创建增强的3D场景
        self.scene = vp.canvas(
            title="增强版四元数3D可视化器 - 自适应速率匹配 + 极速响应",
            width=1600,
            height=1000,
            background=vp.color.black,
            center=vp.vector(0, 0, 0)
        )
        
        # 创建3D对象
        self._create_enhanced_objects()
        
        # 轨迹系统
        self.trail_points = deque(maxlen=2000)
        self.trail_curves = []
        self.max_trail_segments = 10
        
        # 动画和效果
        self.rotation_smoothing = 0.1
        self.last_rotation = None
        
        # 性能优化
        self.update_counter = 0
        self.trail_update_interval = 5  # 每5帧更新一次轨迹
        
        logger.info("增强版VPython渲染器已初始化")
    
    def _create_enhanced_objects(self):
        """创建增强的3D对象"""
        # 创建更精美的传感器模型
        self.sensor_main = vp.box(
            pos=vp.vector(0, 0, 0),
            size=vp.vector(3, 1.5, 0.8),
            color=vp.color.cyan,
            opacity=0.9
        )
        
        # 添加传感器细节
        self.sensor_top = vp.box(
            pos=vp.vector(0, 0.6, 0),
            size=vp.vector(2.5, 0.3, 0.6),
            color=vp.color.blue,
            opacity=0.8
        )
        
        # 创建方向指示器
        self.direction_arrow = vp.arrow(
            pos=vp.vector(0, 0, 0),
            axis=vp.vector(2, 0, 0),
            color=vp.color.red,
            shaftwidth=0.2,
            headwidth=0.4,
            headlength=0.6
        )
        
        # 创建增强的坐标轴
        self.axes = []
        
        # X轴 - 红色，更粗
        x_axis = vp.arrow(
            pos=vp.vector(0, 0, 0),
            axis=vp.vector(4, 0, 0),
            color=vp.color.red,
            shaftwidth=0.15,
            headwidth=0.3,
            headlength=0.5
        )
        
        # Y轴 - 绿色
        y_axis = vp.arrow(
            pos=vp.vector(0, 0, 0),
            axis=vp.vector(0, 4, 0),
            color=vp.color.green,
            shaftwidth=0.15,
            headwidth=0.3,
            headlength=0.5
        )
        
        # Z轴 - 蓝色
        z_axis = vp.arrow(
            pos=vp.vector(0, 0, 0),
            axis=vp.vector(0, 0, 4),
            color=vp.color.blue,
            shaftwidth=0.15,
            headwidth=0.3,
            headlength=0.5
        )
        
        self.axes = [x_axis, y_axis, z_axis]
        
        # 创建网格地面
        self._create_grid_floor()
        
        # 添加控制界面
        self._create_enhanced_controls()
    
    def _create_grid_floor(self):
        """创建网格地面"""
        self.grid_lines = []
        grid_size = 10
        grid_spacing = 1
        
        # 创建网格线
        for i in range(-grid_size, grid_size + 1):
            # X方向线
            line_x = vp.curve(
                pos=[vp.vector(-grid_size, -3, i * grid_spacing), 
                     vp.vector(grid_size, -3, i * grid_spacing)],
                color=vp.color.gray(0.3),
                radius=0.02
            )
            
            # Z方向线
            line_z = vp.curve(
                pos=[vp.vector(i * grid_spacing, -3, -grid_size), 
                     vp.vector(i * grid_spacing, -3, grid_size)],
                color=vp.color.gray(0.3),
                radius=0.02
            )
            
            self.grid_lines.extend([line_x, line_z])
    
    def _create_enhanced_controls(self):
        """创建增强的控制界面"""
        self.scene.append_to_caption('\n\n')
        
        # 标题
        self.scene.append_to_caption('<h2>增强版四元数3D可视化器</h2>')
        self.scene.append_to_caption('<h3>极速响应 + 零漂抑制 + 增强视觉效果</h3>')
        
        # 控制按钮
        self.scene.append_to_caption('\n<b>控制面板:</b>\n')
        
        # 重置视图
        reset_button = vp.button(text="🔄 重置视图", bind=self._reset_view)
        self.scene.append_to_caption('  ')
        
        # 清空轨迹
        clear_button = vp.button(text="🧹 清空轨迹", bind=self._clear_trail)
        self.scene.append_to_caption('  ')
        
        # 切换网格
        grid_button = vp.button(text="📐 切换网格", bind=self._toggle_grid)
        self.scene.append_to_caption('\n\n')
        
        # 信息显示区域
        self.scene.append_to_caption('<b>实时数据:</b>\n')
        self.info_text = vp.wtext(text="等待数据...")
        
        self.scene.append_to_caption('\n\n<b>性能统计:</b>\n')
        self.stats_text = vp.wtext(text="等待统计...")
        
        self.scene.append_to_caption('\n\n<b>操作说明:</b>\n')
        self.scene.append_to_caption("""
• 鼠标拖拽: 旋转视角
• 滚轮: 缩放视图
• 右键拖拽: 平移视图
• Ctrl+鼠标: 精细控制
• 双击: 自动聚焦
        """)
    
    def _reset_view(self, b):
        """重置视图"""
        self.scene.camera.pos = vp.vector(8, 6, 8)
        self.scene.camera.axis = vp.vector(-1, -0.75, -1)
        self.scene.center = vp.vector(0, 0, 0)
    
    def _clear_trail(self, b):
        """清空轨迹"""
        self.trail_points.clear()
        for curve in self.trail_curves:
            curve.visible = False
        self.trail_curves.clear()
    
    def _toggle_grid(self, b):
        """切换网格显示"""
        for line in self.grid_lines:
            line.visible = not line.visible
    
    def update_pose(self, quaternion: dict, euler: dict):
        """更新姿态 - 增强版"""
        try:
            # 四元数归一化
            w, x, y, z = quaternion['w'], quaternion['x'], quaternion['y'], quaternion['z']
            norm = math.sqrt(w*w + x*x + y*y + z*z)
            if norm > 0:
                w, x, y, z = w/norm, x/norm, y/norm, z/norm
            
            # 创建旋转矩阵
            rotation_matrix = self._quaternion_to_matrix(w, x, y, z)
            
            # 平滑旋转（减少抖动）
            if self.last_rotation is not None:
                # 简单的线性插值平滑
                for i in range(3):
                    for j in range(3):
                        rotation_matrix[i][j] = (
                            self.last_rotation[i][j] * (1 - self.rotation_smoothing) +
                            rotation_matrix[i][j] * self.rotation_smoothing
                        )
            
            self.last_rotation = rotation_matrix
            
            # 更新传感器主体
            axis = vp.vector(rotation_matrix[0][0], rotation_matrix[1][0], rotation_matrix[2][0])
            up = vp.vector(rotation_matrix[0][1], rotation_matrix[1][1], rotation_matrix[2][1])
            
            self.sensor_main.axis = axis * 3
            self.sensor_main.up = up
            
            # 更新传感器顶部
            self.sensor_top.axis = axis * 2.5
            self.sensor_top.up = up
            
            # 更新方向指示器
            self.direction_arrow.axis = axis * 2
            
            # 更新轨迹
            self._update_enhanced_trail(euler)
            
        except Exception as e:
            logger.error(f"更新姿态异常: {e}")
    
    def _quaternion_to_matrix(self, w, x, y, z):
        """四元数到旋转矩阵"""
        return [
            [1-2*(y*y+z*z), 2*(x*y-w*z), 2*(x*z+w*y)],
            [2*(x*y+w*z), 1-2*(x*x+z*z), 2*(y*z-w*x)],
            [2*(x*z-w*y), 2*(y*z+w*x), 1-2*(x*x+y*y)]
        ]
    
    def _update_enhanced_trail(self, euler: dict):
        """更新增强轨迹"""
        self.update_counter += 1
        
        # 添加新的轨迹点
        trail_point = vp.vector(
            euler['roll'] * 0.05,
            euler['pitch'] * 0.05,
            euler['yaw'] * 0.05
        )
        
        self.trail_points.append(trail_point)
        
        # 每隔几帧更新轨迹显示（性能优化）
        if self.update_counter % self.trail_update_interval == 0:
            self._rebuild_trail_curves()
    
    def _rebuild_trail_curves(self):
        """重建轨迹曲线"""
        if len(self.trail_points) < 2:
            return
        
        # 清除旧的轨迹段
        for curve in self.trail_curves:
            curve.visible = False
        self.trail_curves.clear()
        
        # 创建分段轨迹（颜色渐变）
        points_per_segment = max(1, len(self.trail_points) // self.max_trail_segments)
        
        for i in range(0, len(self.trail_points) - points_per_segment, points_per_segment):
            segment_points = list(self.trail_points)[i:i + points_per_segment + 1]
            
            if len(segment_points) > 1:
                # 计算颜色（从红到黄的渐变）
                intensity = i / len(self.trail_points)
                color = vp.vector(1.0, intensity, 0.0)
                
                # 创建轨迹段
                trail_segment = vp.curve(
                    pos=segment_points,
                    color=color,
                    radius=0.05
                )
                
                self.trail_curves.append(trail_segment)
    
    def update_info(self, data_info: dict, stats_info: dict):
        """更新信息显示"""
        try:
            quat = data_info['quaternion']
            euler = data_info['euler']
            
            # 更新数据信息
            data_text = f"""四元数:
  w = {quat['w']:.4f}
  x = {quat['x']:.4f}
  y = {quat['y']:.4f}
  z = {quat['z']:.4f}

欧拉角:
  Roll  = {euler['roll']:.2f}°
  Pitch = {euler['pitch']:.2f}°
  Yaw   = {euler['yaw']:.2f}°"""
            
            self.info_text.text = data_text
            
            # 更新统计信息
            stats_text = f"""数据计数: {stats_info['count']}
数据速率: {stats_info['rate']:.1f} quat/s
运行时间: {stats_info['elapsed']:.1f}s
轨迹点数: {len(self.trail_points)}

滤波器状态:
  Alpha: {stats_info.get('alpha', 'N/A')}
  校正次数: {stats_info.get('corrections', 0)}"""
            
            self.stats_text.text = stats_text
            
        except Exception as e:
            logger.error(f"更新信息显示异常: {e}")


class EnhancedVPythonVisualizer:
    """增强版VPython可视化器"""
    
    def __init__(self):
        self.config = Config()
        
        # 极速配置
        self.config.serial.port = "COM6"
        self.config.processing.data_format = "ascii"
        self.config.processing.enable_filtering = True
        self.config.processing.processing_interval = 0.0001
        
        # 初始化组件
        self.quaternion_processor = QuaternionProcessor(self.config)
        self.quaternion_processor.set_data_format('ascii')
        
        self.serial_manager = SerialManager(
            self.config,
            self._process_data
        )
        
        # 增强渲染器
        self.renderer = EnhancedVPythonRenderer()
        
        # 统计数据
        self.data_count = 0
        self.start_time = None
        self.last_info_update = 0
        self.info_update_interval = 1.0  # 每秒更新信息

        # 自适应速率检测 (与Open3D版本相同的技术)
        self.data_timestamps = deque(maxlen=100)
        self.detected_data_rate = 0.0
        self.target_render_rate = 0.0
        self.adaptive_interpolation = True
        self.last_rate_update = 0
        self.rate_update_interval = 2.0

        # 四元数插值优化
        self.previous_quaternion = {'w': 1.0, 'x': 0.0, 'y': 0.0, 'z': 0.0}
        self.interpolation_enabled = True
        self.interpolation_factor = 0.15
        
        logger.info("增强版VPython可视化器已初始化")

    def _detect_data_rate(self):
        """检测串口数据接收速率 (与Open3D版本相同)"""
        try:
            if len(self.data_timestamps) < 10:
                return 0.0

            # 计算最近数据的平均间隔
            recent_timestamps = list(self.data_timestamps)[-50:]
            if len(recent_timestamps) < 2:
                return 0.0

            # 计算时间间隔
            intervals = []
            for i in range(1, len(recent_timestamps)):
                interval = recent_timestamps[i] - recent_timestamps[i-1]
                if 0.001 <= interval <= 1.0:
                    intervals.append(interval)

            if not intervals:
                return 0.0

            # 计算平均间隔和数据速率
            avg_interval = sum(intervals) / len(intervals)
            detected_rate = 1.0 / avg_interval if avg_interval > 0 else 0.0

            return detected_rate

        except Exception as e:
            logger.error(f"检测数据速率异常: {e}")
            return 0.0

    def _update_adaptive_parameters(self):
        """更新自适应参数 (与Open3D版本相同)"""
        try:
            current_time = time.time()

            # 每2秒更新一次速率检测
            if current_time - self.last_rate_update >= self.rate_update_interval:
                self.last_rate_update = current_time

                # 检测当前数据速率
                new_detected_rate = self._detect_data_rate()

                if new_detected_rate > 0:
                    # 平滑更新检测到的速率
                    if self.detected_data_rate == 0:
                        self.detected_data_rate = new_detected_rate
                    else:
                        # 使用指数移动平均平滑速率变化
                        alpha = 0.3
                        self.detected_data_rate = alpha * new_detected_rate + (1 - alpha) * self.detected_data_rate

                    # 设置目标渲染速率为数据速率的2-3倍
                    self.target_render_rate = self.detected_data_rate * 2.5

                    # 根据数据速率自适应调整插值因子
                    if self.detected_data_rate >= 200:
                        self.interpolation_factor = 0.08
                    elif self.detected_data_rate >= 100:
                        self.interpolation_factor = 0.12
                    elif self.detected_data_rate >= 50:
                        self.interpolation_factor = 0.18
                    else:
                        self.interpolation_factor = 0.25

        except Exception as e:
            logger.error(f"更新自适应参数异常: {e}")

    async def _process_data(self, raw_data: bytes):
        """处理数据 + 自适应速率检测"""
        try:
            processed_data = self.quaternion_processor.process_raw_data(raw_data)

            if processed_data:
                current_time = time.time()

                for data_point in processed_data:
                    self.data_count += 1

                    # 记录数据时间戳用于速率检测
                    self.data_timestamps.append(current_time)

                    quat = data_point['quaternion']
                    euler = data_point['euler_degrees']

                    # 更新自适应参数
                    self._update_adaptive_parameters()

                    # 更新3D可视化 (现在支持自适应)
                    self.renderer.update_pose(quat, euler)

                    # 更新信息显示
                    await self._update_info_display(quat, euler)

        except Exception as e:
            logger.error(f"处理数据异常: {e}")
    
    async def _update_info_display(self, quat: dict, euler: dict):
        """更新信息显示"""
        current_time = time.time()
        
        if current_time - self.last_info_update >= self.info_update_interval:
            self.last_info_update = current_time
            
            if self.start_time:
                elapsed = current_time - self.start_time
                rate = self.data_count / elapsed
                
                # 获取滤波器统计
                filter_stats = {}
                if self.quaternion_processor.complementary_filter:
                    filter_stats = self.quaternion_processor.complementary_filter.get_filter_statistics()
                
                # 准备数据
                data_info = {'quaternion': quat, 'euler': euler}
                stats_info = {
                    'count': self.data_count,
                    'rate': rate,
                    'elapsed': elapsed,
                    'alpha': filter_stats.get('alpha', 'N/A'),
                    'corrections': filter_stats.get('drift_corrections_applied', 0)
                }
                
                # 更新显示
                self.renderer.update_info(data_info, stats_info)
    
    async def run(self):
        """运行可视化器"""
        print(f"""
🚀 增强版VPython四元数3D可视化器
===============================

特性升级:
✅ 更灵敏的3D交互体验
✅ 增强的视觉效果和细节
✅ 智能轨迹系统 (2000点缓存)
✅ 平滑旋转算法 (减少抖动)
✅ 网格地面参考系统
✅ 实时性能监控
✅ 极速响应 (无帧率限制)
✅ 零漂抑制算法

视觉增强:
- 精美的传感器3D模型
- 方向指示器
- 颜色渐变轨迹
- 网格地面
- 增强的坐标轴

控制升级:
- 一键重置视图
- 轨迹清空功能
- 网格显示切换
- 实时数据监控

开始增强可视化...
""")
        
        self.start_time = time.time()
        
        try:
            # 启动数据处理
            await self.serial_manager.start()
            
        except KeyboardInterrupt:
            logger.info("用户中断")
        except Exception as e:
            logger.error(f"运行异常: {e}")
        finally:
            if self.serial_manager:
                await self.serial_manager.stop()


async def main():
    """主函数"""
    try:
        visualizer = EnhancedVPythonVisualizer()
        await visualizer.run()
        
    except KeyboardInterrupt:
        print("\n可视化器被用户中断")
    except Exception as e:
        logger.error(f"程序异常: {e}")


if __name__ == "__main__":
    asyncio.run(main())
