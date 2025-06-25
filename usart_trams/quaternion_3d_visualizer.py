#!/usr/bin/env python3
"""
四元数3D可视化器 - 最终版本
整合了所有最佳功能：超响应、多端口支持、完美视角控制
"""

import asyncio
import logging
import sys
import time
import math
import numpy as np
from pathlib import Path
from collections import deque
import threading

# 添加src目录到路径
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from src.config import Config
from src.serial_manager import SerialManager
from src.quaternion_processor import QuaternionProcessor

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

try:
    import open3d as o3d
    logger.info("Open3D 可用")
except ImportError:
    logger.error("Open3D 不可用，请安装: pip install open3d")
    sys.exit(1)


class Quaternion3DVisualizer:
    """四元数3D可视化器 - 最终版本"""
    
    def __init__(self, port="COM6", baudrate=460800, data_format="ascii"):
        print(f"⚡ 初始化四元数3D可视化器...")
        print(f"   端口: {port}")
        print(f"   波特率: {baudrate}")
        print(f"   数据格式: {data_format}")
        
        self.config = Config()
        
        # 配置参数
        self.config.serial.port = port
        self.config.serial.baudrate = baudrate
        self.config.serial.timeout = 0.1
        
        self.config.processing.data_format = data_format
        self.config.processing.enable_filtering = True
        self.config.processing.processing_interval = 0.0001  # 极速处理
        self.config.processing.buffer_size = 4096
        self.config.processing.batch_size = 1
        
        # 初始化数据处理
        try:
            self.quaternion_processor = QuaternionProcessor(self.config)
            self.quaternion_processor.set_data_format(data_format)
            self.serial_manager = SerialManager(self.config, self._process_data)
            print("✅ 数据处理组件初始化成功")
        except Exception as e:
            print(f"❌ 数据处理组件初始化失败: {e}")
            raise
        
        # 超响应数据传递 - 直接变量，无队列延迟
        self.latest_quaternion = {'w': 1.0, 'x': 0.0, 'y': 0.0, 'z': 0.0}
        self.latest_euler = {'roll': 0.0, 'pitch': 0.0, 'yaw': 0.0}
        self.data_count = 0
        self.data_lock = threading.Lock()
        self.data_updated = False
        
        # 3D对象
        self.vis = None
        self.sensor_mesh = None
        self.coordinate_frame = None
        self.trail_line = None
        self.trail_points = deque(maxlen=200)
        
        # 丝滑度优化
        self.trail_update_counter = 0
        self.trail_update_interval = 30  # 减少轨迹更新频率，提高主模型丝滑度

        # 四元数插值优化
        self.previous_quaternion = {'w': 1.0, 'x': 0.0, 'y': 0.0, 'z': 0.0}
        self.interpolation_enabled = True
        self.interpolation_factor = 0.15  # 插值平滑因子

        # 自适应速率检测
        self.data_timestamps = deque(maxlen=100)  # 保存最近100个数据时间戳
        self.detected_data_rate = 0.0
        self.target_render_rate = 0.0
        self.adaptive_interpolation = True
        self.last_rate_update = 0
        self.rate_update_interval = 2.0  # 每2秒更新一次速率检测
        
        # 预计算数据
        self.original_vertices = np.array([
            [-1.0, -0.5, -0.25], [1.0, -0.5, -0.25], [1.0, 0.5, -0.25], [-1.0, 0.5, -0.25],
            [-1.0, -0.5, 0.25], [1.0, -0.5, 0.25], [1.0, 0.5, 0.25], [-1.0, 0.5, 0.25]
        ])
        
        print("✅ 四元数3D可视化器初始化完成")
    
    async def _process_data(self, raw_data: bytes):
        """超响应数据处理 + 速率检测"""
        try:
            processed_data = self.quaternion_processor.process_raw_data(raw_data)

            if processed_data:
                current_time = time.time()

                # 只保留最新数据，立即更新
                latest_point = processed_data[-1]
                self.data_count += len(processed_data)

                # 记录数据时间戳用于速率检测
                for _ in processed_data:
                    self.data_timestamps.append(current_time)

                # 原子更新，最小锁定时间
                with self.data_lock:
                    self.latest_quaternion = latest_point['quaternion'].copy()
                    self.latest_euler = latest_point['euler_degrees'].copy()
                    self.data_updated = True

        except Exception as e:
            logger.error(f"数据处理异常: {e}")
    
    def _create_visualizer(self):
        """创建可视化器"""
        print("🖥️ 创建3D可视化器...")
        
        # 创建可视化器
        self.vis = o3d.visualization.Visualizer()
        
        # 创建窗口
        success = self.vis.create_window(
            window_name=f"四元数3D可视化器 - {self.config.serial.port}",
            width=1400,
            height=900,
            left=100,
            top=100
        )
        
        if not success:
            raise RuntimeError("窗口创建失败")
        
        print("✅ 窗口创建成功")
        
        # 创建几何体
        self.sensor_mesh = o3d.geometry.TriangleMesh.create_box(width=2.0, height=1.0, depth=0.5)
        self.sensor_mesh.translate([-1.0, -0.5, -0.25])
        self.sensor_mesh.paint_uniform_color([0.0, 0.8, 1.0])
        self.sensor_mesh.compute_vertex_normals()
        
        self.coordinate_frame = o3d.geometry.TriangleMesh.create_coordinate_frame(size=3.0)
        self.trail_line = o3d.geometry.LineSet()
        
        # 添加几何体
        self.vis.add_geometry(self.sensor_mesh)
        self.vis.add_geometry(self.coordinate_frame)
        self.vis.add_geometry(self.trail_line)
        
        # 设置渲染选项
        render_option = self.vis.get_render_option()
        render_option.background_color = np.array([0.1, 0.1, 0.1])
        render_option.light_on = True
        render_option.point_size = 3.0
        render_option.line_width = 2.0
        
        # 设置相机
        view_control = self.vis.get_view_control()
        view_control.set_front([0.5, 0.5, 0.5])
        view_control.set_lookat([0, 0, 0])
        view_control.set_up([0, 0, 1])
        view_control.set_zoom(0.8)
        
        print("✅ 3D可视化器创建完成")

    def _detect_data_rate(self):
        """检测串口数据接收速率"""
        try:
            if len(self.data_timestamps) < 10:
                return 0.0

            # 计算最近数据的平均间隔
            recent_timestamps = list(self.data_timestamps)[-50:]  # 最近50个数据点
            if len(recent_timestamps) < 2:
                return 0.0

            # 计算时间间隔
            intervals = []
            for i in range(1, len(recent_timestamps)):
                interval = recent_timestamps[i] - recent_timestamps[i-1]
                if 0.001 <= interval <= 1.0:  # 过滤异常间隔
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
        """更新自适应参数"""
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

                    # 设置目标渲染速率为数据速率的2-3倍，确保丝滑
                    self.target_render_rate = self.detected_data_rate * 2.5

                    # 根据数据速率自适应调整插值因子
                    if self.detected_data_rate >= 200:  # 高频数据
                        self.interpolation_factor = 0.08  # 更小的插值因子，更快响应
                    elif self.detected_data_rate >= 100:  # 中频数据
                        self.interpolation_factor = 0.12
                    elif self.detected_data_rate >= 50:   # 低频数据
                        self.interpolation_factor = 0.18
                    else:  # 很低频数据
                        self.interpolation_factor = 0.25  # 更大的插值因子，更平滑

                    logger.debug(f"自适应参数更新: 数据速率={self.detected_data_rate:.1f}Hz, "
                               f"目标渲染速率={self.target_render_rate:.1f}Hz, "
                               f"插值因子={self.interpolation_factor:.3f}")

        except Exception as e:
            logger.error(f"更新自适应参数异常: {e}")

    def _slerp_quaternion(self, q1, q2, t):
        """四元数球面线性插值 (SLERP) - 提高丝滑度"""
        try:
            # 计算点积
            dot = q1['w']*q2['w'] + q1['x']*q2['x'] + q1['y']*q2['y'] + q1['z']*q2['z']

            # 如果点积为负，取反其中一个四元数以选择较短路径
            if dot < 0.0:
                q2 = {'w': -q2['w'], 'x': -q2['x'], 'y': -q2['y'], 'z': -q2['z']}
                dot = -dot

            # 如果四元数非常接近，使用线性插值
            if dot > 0.9995:
                result = {
                    'w': q1['w'] + t * (q2['w'] - q1['w']),
                    'x': q1['x'] + t * (q2['x'] - q1['x']),
                    'y': q1['y'] + t * (q2['y'] - q1['y']),
                    'z': q1['z'] + t * (q2['z'] - q1['z'])
                }
            else:
                # 球面线性插值
                theta_0 = math.acos(abs(dot))
                sin_theta_0 = math.sin(theta_0)
                theta = theta_0 * t
                sin_theta = math.sin(theta)

                s0 = math.cos(theta) - dot * sin_theta / sin_theta_0
                s1 = sin_theta / sin_theta_0

                result = {
                    'w': s0 * q1['w'] + s1 * q2['w'],
                    'x': s0 * q1['x'] + s1 * q2['x'],
                    'y': s0 * q1['y'] + s1 * q2['y'],
                    'z': s0 * q1['z'] + s1 * q2['z']
                }

            # 归一化
            norm = math.sqrt(result['w']**2 + result['x']**2 + result['y']**2 + result['z']**2)
            if norm > 0:
                result = {k: v/norm for k, v in result.items()}

            return result

        except Exception as e:
            logger.error(f"四元数插值异常: {e}")
            return q2

    def _update_sensor_ultra_smooth(self):
        """超丝滑传感器更新"""
        try:
            # 快速获取最新数据
            with self.data_lock:
                if not self.data_updated:
                    # 没有新数据时，仍然可以进行插值平滑
                    if self.interpolation_enabled:
                        # 继续向目标四元数插值
                        current_quat = self.previous_quaternion.copy()
                    else:
                        return
                else:
                    current_quat = self.latest_quaternion.copy()
                    self.data_updated = False

            # 四元数平滑插值
            if self.interpolation_enabled:
                smoothed_quat = self._slerp_quaternion(
                    self.previous_quaternion,
                    current_quat,
                    self.interpolation_factor
                )
                self.previous_quaternion = smoothed_quat
            else:
                smoothed_quat = current_quat
                self.previous_quaternion = current_quat

            w, x, y, z = smoothed_quat['w'], smoothed_quat['x'], smoothed_quat['y'], smoothed_quat['z']

            # 四元数归一化
            norm = math.sqrt(w*w + x*x + y*y + z*z)
            if norm > 0:
                w, x, y, z = w/norm, x/norm, y/norm, z/norm

            # 四元数到旋转矩阵
            rotation_matrix = np.array([
                [1-2*(y*y+z*z), 2*(x*y-w*z), 2*(x*z+w*y)],
                [2*(x*y+w*z), 1-2*(x*x+z*z), 2*(y*z-w*x)],
                [2*(x*z-w*y), 2*(y*z+w*x), 1-2*(x*x+y*y)]
            ])

            # 极速应用旋转
            rotated_vertices = np.dot(self.original_vertices, rotation_matrix.T)

            # 直接更新顶点
            self.sensor_mesh.vertices = o3d.utility.Vector3dVector(rotated_vertices)
            self.sensor_mesh.compute_vertex_normals()

            # 立即更新几何体
            self.vis.update_geometry(self.sensor_mesh)

        except Exception as e:
            logger.error(f"更新传感器异常: {e}")
    
    def _update_trail_ultra_fast(self):
        """超快速轨迹更新"""
        try:
            self.trail_update_counter += 1
            
            # 降频更新轨迹，避免影响主要响应速度
            if self.trail_update_counter >= self.trail_update_interval:
                self.trail_update_counter = 0
                
                with self.data_lock:
                    euler = self.latest_euler.copy()
                
                # 添加轨迹点
                trail_point = np.array([
                    euler['roll'] * 0.02,
                    euler['pitch'] * 0.02,
                    euler['yaw'] * 0.02
                ])
                
                self.trail_points.append(trail_point)
                
                # 快速更新轨迹线
                if len(self.trail_points) > 1:
                    points = np.array(list(self.trail_points))
                    lines = [[i, i + 1] for i in range(len(points) - 1)]
                    colors = [[1.0, i/len(lines), 0.0] for i in range(len(lines))]
                    
                    self.trail_line.points = o3d.utility.Vector3dVector(points)
                    self.trail_line.lines = o3d.utility.Vector2iVector(lines)
                    self.trail_line.colors = o3d.utility.Vector3dVector(colors)
                    
                    self.vis.update_geometry(self.trail_line)
                
        except Exception as e:
            logger.error(f"更新轨迹异常: {e}")
    
    def start_data_processing(self):
        """启动数据处理"""
        print("📡 启动数据处理...")
        
        def run_async():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(self.serial_manager.start())
            except Exception as e:
                logger.error(f"数据处理异常: {e}")
            finally:
                loop.close()
        
        self.thread = threading.Thread(target=run_async, daemon=True)
        self.thread.start()
        print("✅ 数据处理已启动")
    
    def run(self):
        """运行可视化器"""
        print(f"""
🎯 四元数3D可视化器 - 自适应超丝滑版本
===================================

配置:
✅ 端口: {self.config.serial.port}
✅ 波特率: {self.config.serial.baudrate}
✅ 数据格式: {self.config.processing.data_format}
✅ 超响应优化: 启用
✅ 完美视角控制: 启用
✅ 零漂抑制: 启用
✅ 四元数SLERP插值: 启用 (丝滑度优化)
✅ 智能平滑算法: 启用
✅ 自适应速率检测: 启用 (实时匹配串口速率)
✅ 动态插值调整: 启用 (根据数据频率优化)

开始自适应超丝滑可视化...
""")
        
        try:
            # 创建可视化器
            self._create_visualizer()
            
            # 启动数据处理
            self.start_data_processing()
            
            print("""
🎮 控制说明:
============
- 左键拖拽: 旋转视角
- 右键拖拽: 平移视图
- 滚轮: 缩放视图
- ESC: 退出程序

模型现在应该瞬间响应传感器动作！
""")
            
            # 自适应超丝滑主循环
            start_time = time.time()
            last_info_time = 0
            frame_count = 0
            last_frame_time = 0

            while True:
                current_time = time.time()

                # 更新自适应参数
                self._update_adaptive_parameters()

                # 计算自适应帧间隔
                if self.target_render_rate > 0:
                    target_frame_interval = 1.0 / self.target_render_rate
                else:
                    target_frame_interval = 0  # 无限制

                # 自适应帧率控制
                if target_frame_interval > 0:
                    frame_elapsed = current_time - last_frame_time
                    if frame_elapsed < target_frame_interval:
                        # 如果还没到下一帧时间，继续处理但不强制渲染
                        pass
                    else:
                        last_frame_time = current_time
                else:
                    # 无限制模式
                    last_frame_time = current_time

                # 立即更新可视化（自适应超丝滑模式）
                self._update_sensor_ultra_smooth()
                self._update_trail_ultra_fast()

                # 检查窗口事件
                if not self.vis.poll_events():
                    break

                # 渲染
                self.vis.update_renderer()
                frame_count += 1

                # 显示信息
                if current_time - last_info_time >= 3.0:
                    last_info_time = current_time
                    elapsed = current_time - start_time

                    with self.data_lock:
                        data_count = self.data_count
                        euler = self.latest_euler.copy()

                    data_rate = data_count / elapsed if elapsed > 0 else 0
                    render_fps = frame_count / elapsed if elapsed > 0 else 0

                    print(f"🎯 自适应运行: 渲染FPS={render_fps:.0f}, 数据={data_count}, 检测速率={self.detected_data_rate:.1f}Hz")
                    print(f"   目标渲染={self.target_render_rate:.1f}Hz, 插值因子={self.interpolation_factor:.3f}")
                    print(f"   姿态: Roll={euler['roll']:.1f}°, Pitch={euler['pitch']:.1f}°, Yaw={euler['yaw']:.1f}°")

                # 自适应微延迟（根据目标速率）
                if target_frame_interval > 0.001:  # 如果目标间隔大于1ms
                    sleep_time = max(0, target_frame_interval * 0.1)  # 睡眠目标间隔的10%
                    if sleep_time > 0:
                        time.sleep(sleep_time)
        
        except KeyboardInterrupt:
            print("\n用户中断")
        except Exception as e:
            print(f"❌ 运行异常: {e}")
            import traceback
            traceback.print_exc()
        finally:
            try:
                if self.vis:
                    self.vis.destroy_window()
                print("✅ 可视化器已退出")
            except:
                pass


def main():
    """主函数 - 支持环境变量配置"""
    import os

    # 检查是否有环境变量配置 (来自启动器)
    env_port = os.environ.get('ADAPTIVE_PORT')
    env_baudrate = os.environ.get('ADAPTIVE_BAUDRATE')
    env_format = os.environ.get('ADAPTIVE_FORMAT')

    if env_port and env_baudrate and env_format:
        # 从环境变量启动 (启动器模式)
        print(f"🎯 自适应Open3D可视化器 - 启动器模式")
        print(f"   端口: {env_port}")
        print(f"   波特率: {env_baudrate}")
        print(f"   数据格式: {env_format}")

        visualizer = Quaternion3DVisualizer(
            port=env_port,
            baudrate=int(env_baudrate),
            data_format=env_format
        )
        visualizer.run()
        return

    # 直接启动模式
    print("🚀 四元数3D可视化器启动器")
    print("="*40)

    # 预设配置 - 全部支持自适应速率匹配
    configs = {
        "1": {"port": "COM6", "baudrate": 460800, "data_format": "ascii", "name": "COM6 ASCII (自适应)"},
        "2": {"port": "COM12", "baudrate": 128000, "data_format": "ascii", "name": "COM12 ASCII (自适应)"},
        "3": {"port": "COM6", "baudrate": 921600, "data_format": "ascii", "name": "COM6 高速 (自适应)"},
        "4": {"port": "COM3", "baudrate": 115200, "data_format": "ascii", "name": "COM3 标准 (自适应)"},
        "5": {"port": "COM4", "baudrate": 230400, "data_format": "ascii", "name": "COM4 中速 (自适应)"},
        "6": {"port": "COM5", "baudrate": 57600, "data_format": "ascii", "name": "COM5 低速 (自适应)"},
    }

    print("选择配置 (全部支持自适应速率匹配):")
    for key, config in configs.items():
        print(f"  {key}. {config['name']}")

    print(f"\n🎯 自适应技术特性:")
    print(f"  ✅ 自动检测串口数据速率")
    print(f"  ✅ 动态调整渲染频率匹配")
    print(f"  ✅ 智能插值因子优化")
    print(f"  ✅ 完美丝滑运动效果")

    try:
        choice = input(f"\n请选择 (1-{len(configs)}, 默认1): ").strip() or "1"

        if choice in configs:
            config = configs[choice]
            print(f"\n✅ 选择: {config['name']}")

            visualizer = Quaternion3DVisualizer(
                port=config['port'],
                baudrate=config['baudrate'],
                data_format=config['data_format']
            )
            visualizer.run()
        else:
            print("❌ 无效选择")

    except Exception as e:
        logger.error(f"程序异常: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
