#!/usr/bin/env python3
"""
六轴数据3D可视化器
直接输入原始六轴数据（加速度计+陀螺仪），显示模型位姿变化
支持互补滤波算法融合六轴数据为四元数
"""

import asyncio
import logging
import sys
import time
import math
import numpy as np
from pathlib import Path
import threading

# 添加src目录到路径
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from src.config import Config
from src.serial_manager import SerialManager

# 配置日志
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

try:
    import open3d as o3d
except ImportError:
    print("❌ 需要安装Open3D: pip install open3d")
    sys.exit(1)


class SixAxisProcessor:
    """六轴数据处理器 - 融合加速度计和陀螺仪数据"""
    
    def __init__(self):
        # 互补滤波参数
        self.alpha = 0.98  # 陀螺仪权重
        self.beta = 0.02   # 加速度计权重
        
        # 当前姿态角（弧度）
        self.roll = 0.0
        self.pitch = 0.0
        self.yaw = 0.0
        
        # 上次更新时间
        self.last_time = time.time()
        
        # 陀螺仪偏移校准
        self.gyro_offset = {'x': 0.0, 'y': 0.0, 'z': 0.0}
        self.calibration_samples = 0
        self.calibration_count = 100  # 校准样本数
        
    def calibrate_gyro(self, gyro_data):
        """陀螺仪零点校准"""
        if self.calibration_samples < self.calibration_count:
            self.gyro_offset['x'] += gyro_data['x']
            self.gyro_offset['y'] += gyro_data['y']
            self.gyro_offset['z'] += gyro_data['z']
            self.calibration_samples += 1
            
            if self.calibration_samples == self.calibration_count:
                self.gyro_offset['x'] /= self.calibration_count
                self.gyro_offset['y'] /= self.calibration_count
                self.gyro_offset['z'] /= self.calibration_count
                print(f"🔧 陀螺仪校准完成: x={self.gyro_offset['x']:.3f}, y={self.gyro_offset['y']:.3f}, z={self.gyro_offset['z']:.3f}")
            return True
        return False
    
    def process_six_axis_data(self, accel_data, gyro_data):
        """处理六轴数据，返回四元数"""
        current_time = time.time()
        dt = current_time - self.last_time
        self.last_time = current_time
        
        # 如果还在校准阶段
        if self.calibrate_gyro(gyro_data):
            return self.euler_to_quaternion(0, 0, 0)
        
        # 去除陀螺仪偏移
        gyro_x = gyro_data['x'] - self.gyro_offset['x']
        gyro_y = gyro_data['y'] - self.gyro_offset['y']
        gyro_z = gyro_data['z'] - self.gyro_offset['z']
        
        # 从加速度计计算倾斜角
        accel_roll = math.atan2(accel_data['y'], accel_data['z'])
        accel_pitch = math.atan2(-accel_data['x'], math.sqrt(accel_data['y']**2 + accel_data['z']**2))
        
        # 陀螺仪积分
        self.roll += gyro_x * dt
        self.pitch += gyro_y * dt
        self.yaw += gyro_z * dt
        
        # 互补滤波融合
        self.roll = self.alpha * self.roll + self.beta * accel_roll
        self.pitch = self.alpha * self.pitch + self.beta * accel_pitch
        # Yaw只能通过陀螺仪积分（加速度计无法提供Yaw信息）
        
        # 转换为四元数
        return self.euler_to_quaternion(self.roll, self.pitch, self.yaw)
    
    def euler_to_quaternion(self, roll, pitch, yaw):
        """欧拉角转四元数"""
        cr = math.cos(roll * 0.5)
        sr = math.sin(roll * 0.5)
        cp = math.cos(pitch * 0.5)
        sp = math.sin(pitch * 0.5)
        cy = math.cos(yaw * 0.5)
        sy = math.sin(yaw * 0.5)
        
        w = cr * cp * cy + sr * sp * sy
        x = sr * cp * cy - cr * sp * sy
        y = cr * sp * cy + sr * cp * sy
        z = cr * cp * sy - sr * sp * cy
        
        return {'w': w, 'x': x, 'y': y, 'z': z}


class SixAxisDataParser:
    """六轴数据解析器"""
    
    def __init__(self, data_format="csv"):
        self.data_format = data_format
        
    def parse_raw_data(self, raw_data):
        """解析原始数据"""
        try:
            data_str = raw_data.decode('utf-8').strip()
            if not data_str:
                return None
            
            lines = data_str.split('\n')
            parsed_data = []
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                    
                if self.data_format == "csv":
                    # CSV格式: ax,ay,az,gx,gy,gz
                    parts = line.split(',')
                    if len(parts) >= 6:
                        try:
                            accel = {
                                'x': float(parts[0]),
                                'y': float(parts[1]),
                                'z': float(parts[2])
                            }
                            gyro = {
                                'x': math.radians(float(parts[3])),  # 转换为弧度/秒
                                'y': math.radians(float(parts[4])),
                                'z': math.radians(float(parts[5]))
                            }
                            parsed_data.append({'accel': accel, 'gyro': gyro})
                        except ValueError:
                            continue
            
            return parsed_data
            
        except Exception as e:
            logger.error(f"数据解析异常: {e}")
            return None


class SixAxis3DVisualizer:
    """六轴数据3D可视化器"""
    
    def __init__(self, port="COM12", baudrate=115200):
        print(f"📊 六轴数据3D可视化器")
        print(f"   端口: {port}")
        print(f"   波特率: {baudrate}")
        
        # 基本配置
        self.config = Config()
        self.config.serial.port = port
        self.config.serial.baudrate = baudrate
        self.config.serial.timeout = 0.1
        
        # 初始化数据处理
        self.data_parser = SixAxisDataParser("csv")
        self.six_axis_processor = SixAxisProcessor()
        self.serial_manager = SerialManager(self.config, self._process_data)
        
        # 当前四元数
        self.current_quaternion = {'w': 1.0, 'x': 0.0, 'y': 0.0, 'z': 0.0}
        self.data_lock = threading.Lock()
        self.data_updated = False
        
        # 统计信息
        self.data_count = 0
        self.start_time = time.time()
        
        # 3D对象
        self.vis = None
        self.sensor_mesh = None
        
        # 预计算的立方体顶点
        self.original_vertices = np.array([
            [-1.0, -0.5, -0.25], [1.0, -0.5, -0.25], [1.0, 0.5, -0.25], [-1.0, 0.5, -0.25],
            [-1.0, -0.5, 0.25], [1.0, -0.5, 0.25], [1.0, 0.5, 0.25], [-1.0, 0.5, 0.25]
        ])
        
        print("✅ 初始化完成")
    
    async def _process_data(self, raw_data: bytes):
        """处理串口数据"""
        try:
            parsed_data = self.data_parser.parse_raw_data(raw_data)
            
            if parsed_data:
                for data_point in parsed_data:
                    self.data_count += 1
                    
                    # 处理六轴数据，得到四元数
                    quaternion = self.six_axis_processor.process_six_axis_data(
                        data_point['accel'], 
                        data_point['gyro']
                    )
                    
                    with self.data_lock:
                        self.current_quaternion = quaternion
                        self.data_updated = True
        
        except Exception as e:
            logger.error(f"数据处理异常: {e}")
    
    def _quaternion_to_rotation_matrix(self, q):
        """四元数转旋转矩阵"""
        # 归一化
        norm = math.sqrt(q['w']**2 + q['x']**2 + q['y']**2 + q['z']**2)
        if norm > 0:
            w, x, y, z = q['w']/norm, q['x']/norm, q['y']/norm, q['z']/norm
        else:
            w, x, y, z = 1, 0, 0, 0
        
        return np.array([
            [1-2*(y*y+z*z), 2*(x*y-w*z), 2*(x*z+w*y)],
            [2*(x*y+w*z), 1-2*(x*x+z*z), 2*(y*z-w*x)],
            [2*(x*z-w*y), 2*(y*z+w*x), 1-2*(x*x+y*y)]
        ])
    
    def _create_visualizer(self):
        """创建3D可视化器"""
        print("🖥️ 创建3D可视化器...")
        
        # 创建可视化器
        self.vis = o3d.visualization.Visualizer()
        
        # 创建窗口
        success = self.vis.create_window(
            window_name="六轴数据3D可视化器",
            width=900,
            height=700,
            left=200,
            top=100
        )
        
        if not success:
            raise RuntimeError("窗口创建失败")
        
        # 创建传感器立方体
        self.sensor_mesh = o3d.geometry.TriangleMesh.create_box(width=2.0, height=1.0, depth=0.5)
        self.sensor_mesh.translate([-1.0, -0.5, -0.25])
        self.sensor_mesh.paint_uniform_color([1.0, 0.2, 0.2])  # 红色
        self.sensor_mesh.compute_vertex_normals()
        
        # 创建坐标轴
        coordinate_frame = o3d.geometry.TriangleMesh.create_coordinate_frame(size=2.5)
        
        # 添加到场景
        self.vis.add_geometry(self.sensor_mesh)
        self.vis.add_geometry(coordinate_frame)
        
        # 设置渲染选项
        render_option = self.vis.get_render_option()
        render_option.background_color = np.array([0.05, 0.05, 0.05])
        render_option.light_on = True
        
        # 设置相机视角
        view_control = self.vis.get_view_control()
        view_control.set_front([0.5, 0.5, 0.5])
        view_control.set_lookat([0, 0, 0])
        view_control.set_up([0, 0, 1])
        view_control.set_zoom(0.7)
        
        print("✅ 3D可视化器创建完成")
    
    def _update_model(self):
        """更新模型姿态"""
        try:
            with self.data_lock:
                if not self.data_updated:
                    return
                quat = self.current_quaternion.copy()
                self.data_updated = False
            
            # 转换为旋转矩阵
            rotation_matrix = self._quaternion_to_rotation_matrix(quat)
            
            # 应用旋转
            rotated_vertices = np.dot(self.original_vertices, rotation_matrix.T)
            
            # 更新立方体
            self.sensor_mesh.vertices = o3d.utility.Vector3dVector(rotated_vertices)
            self.sensor_mesh.compute_vertex_normals()
            self.vis.update_geometry(self.sensor_mesh)
            
        except Exception as e:
            logger.error(f"更新模型异常: {e}")
    
    def _start_data_processing(self):
        """启动数据处理线程"""
        def run_async():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(self.serial_manager.start())
            except Exception as e:
                logger.error(f"数据处理异常: {e}")
            finally:
                loop.close()
        
        thread = threading.Thread(target=run_async, daemon=True)
        thread.start()
        print("✅ 数据处理已启动")
    
    def run(self):
        """运行可视化器"""
        print(f"""
📊 六轴数据3D可视化器
===================

数据格式:
- CSV格式: ax,ay,az,gx,gy,gz
- ax,ay,az: 加速度计数据 (m/s²)
- gx,gy,gz: 陀螺仪数据 (度/秒)

算法:
- 互补滤波融合六轴数据
- 自动陀螺仪零点校准
- 实时姿态解算

操作:
- 左键拖拽: 旋转视角
- 右键拖拽: 平移视图
- 滚轮: 缩放视图
- ESC: 退出

开始可视化...
""")
        
        try:
            # 创建3D可视化器
            self._create_visualizer()
            
            # 启动数据处理
            self._start_data_processing()
            
            print("🎮 3D可视化器已启动")
            print("📊 正在校准陀螺仪零点，请保持传感器静止...")
            
            # 主循环
            last_info_time = 0
            while True:
                # 更新模型姿态
                self._update_model()
                
                # 检查窗口事件
                if not self.vis.poll_events():
                    break
                
                # 渲染
                self.vis.update_renderer()
                
                # 显示状态信息
                current_time = time.time()
                if current_time - last_info_time >= 5.0:
                    last_info_time = current_time
                    elapsed = current_time - self.start_time
                    data_rate = self.data_count / elapsed if elapsed > 0 else 0
                    
                    with self.data_lock:
                        quat = self.current_quaternion.copy()
                    
                    # 转换为欧拉角显示
                    roll = math.degrees(self.six_axis_processor.roll)
                    pitch = math.degrees(self.six_axis_processor.pitch)
                    yaw = math.degrees(self.six_axis_processor.yaw)
                    
                    print(f"📊 状态: 数据={self.data_count}, 速率={data_rate:.1f} Hz")
                    print(f"   姿态角: Roll={roll:.1f}°, Pitch={pitch:.1f}°, Yaw={yaw:.1f}°")
                    print(f"   四元数: w={quat['w']:.3f}, x={quat['x']:.3f}, y={quat['y']:.3f}, z={quat['z']:.3f}")
                
                # 小延迟
                time.sleep(0.001)
        
        except KeyboardInterrupt:
            print("\n用户中断")
        except Exception as e:
            print(f"❌ 运行异常: {e}")
        finally:
            try:
                if self.vis:
                    self.vis.destroy_window()
                print("✅ 可视化器已退出")
            except:
                pass


def get_user_config():
    """获取用户配置"""
    print("🔧 配置六轴数据3D可视化器")
    print("=" * 35)
    
    # 端口配置
    ports = ["COM3", "COM6", "COM12", "COM14","COM15"]
    print("可用端口:")
    for i, port in enumerate(ports, 1):
        print(f"  {i}. {port}")
    
    while True:
        try:
            choice = input(f"\n选择端口 (1-{len(ports)}, 默认3=COM12): ").strip() or "3"
            port_index = int(choice) - 1
            if 0 <= port_index < len(ports):
                selected_port = ports[port_index]
                break
            else:
                print("❌ 无效选择")
        except ValueError:
            print("❌ 请输入数字")
    
    # 波特率配置
    baudrates = [9600, 19200, 38400, 57600, 115200, 230400, 460800]
    print(f"\n可用波特率:")
    for i, baud in enumerate(baudrates, 1):
        print(f"  {i}. {baud}")
    
    while True:
        try:
            choice = input(f"\n选择波特率 (1-{len(baudrates)}, 默认5=115200): ").strip() or "5"
            baud_index = int(choice) - 1
            if 0 <= baud_index < len(baudrates):
                selected_baudrate = baudrates[baud_index]
                break
            else:
                print("❌ 无效选择")
        except ValueError:
            print("❌ 请输入数字")
    
    return selected_port, selected_baudrate


def main():
    """主函数"""
    print("""
📊 六轴数据3D可视化器
===================

功能特性:
✅ 直接输入原始六轴数据（加速度计+陀螺仪）
✅ 互补滤波算法融合六轴数据为四元数
✅ 自动陀螺仪零点校准
✅ 实时3D姿态显示
✅ 支持CSV格式数据输入

数据格式示例:
ax,ay,az,gx,gy,gz
0.1,-0.2,9.8,0.5,-0.3,0.1

开始配置...
""")
    
    try:
        # 获取用户配置
        port, baudrate = get_user_config()
        
        print(f"\n✅ 配置完成:")
        print(f"   端口: {port}")
        print(f"   波特率: {baudrate}")
        print(f"   数据格式: CSV (ax,ay,az,gx,gy,gz)")
        
        # 创建并运行可视化器
        visualizer = SixAxis3DVisualizer(port=port, baudrate=baudrate)
        visualizer.run()
        
    except KeyboardInterrupt:
        print("\n👋 用户取消")
    except Exception as e:
        print(f"❌ 程序异常: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
