#!/usr/bin/env python3
"""
最终正确的四元数3D可视化器 - 带重置功能
修正逻辑：用四元数计算模型朝向，正确记录偏移量，不重置视角
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
from src.quaternion_processor import QuaternionProcessor

# 配置日志
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

try:
    import open3d as o3d
except ImportError:
    print("❌ 需要安装Open3D: pip install open3d")
    sys.exit(1)


class QuaternionMath:
    """四元数数学运算"""
    
    @staticmethod
    def normalize(q):
        """四元数归一化"""
        norm = math.sqrt(q['w']**2 + q['x']**2 + q['y']**2 + q['z']**2)
        if norm > 0:
            return {'w': q['w']/norm, 'x': q['x']/norm, 'y': q['y']/norm, 'z': q['z']/norm}
        return q
    
    @staticmethod
    def conjugate(q):
        """四元数共轭（逆）"""
        return {'w': q['w'], 'x': -q['x'], 'y': -q['y'], 'z': -q['z']}
    
    @staticmethod
    def multiply(q1, q2):
        """四元数乘法"""
        w = q1['w']*q2['w'] - q1['x']*q2['x'] - q1['y']*q2['y'] - q1['z']*q2['z']
        x = q1['w']*q2['x'] + q1['x']*q2['w'] + q1['y']*q2['z'] - q1['z']*q2['y']
        y = q1['w']*q2['y'] - q1['x']*q2['z'] + q1['y']*q2['w'] + q1['z']*q2['x']
        z = q1['w']*q2['z'] + q1['x']*q2['y'] - q1['y']*q2['x'] + q1['z']*q2['w']
        return {'w': w, 'x': x, 'y': y, 'z': z}
    
    @staticmethod
    def remove_offset(q_current, q_offset):
        """从当前四元数中移除偏移量
        公式：q_result = q_offset^(-1) * q_current
        这样当q_current = q_offset时，结果为单位四元数(1,0,0,0)
        """
        q_offset_inv = QuaternionMath.conjugate(q_offset)
        return QuaternionMath.multiply(q_offset_inv, q_current)
    
    @staticmethod
    def to_rotation_matrix(q):
        """四元数转旋转矩阵"""
        q = QuaternionMath.normalize(q)
        w, x, y, z = q['w'], q['x'], q['y'], q['z']
        
        return np.array([
            [1-2*(y*y+z*z), 2*(x*y-w*z), 2*(x*z+w*y)],
            [2*(x*y+w*z), 1-2*(x*x+z*z), 2*(y*z-w*x)],
            [2*(x*z-w*y), 2*(y*z+w*x), 1-2*(x*x+y*y)]
        ])


class FinalQuaternion3DReset:
    """最终正确的四元数3D可视化器"""
    
    def __init__(self, port="COM12", baudrate=128000):
        print(f"🎯 最终正确的四元数3D可视化器")
        print(f"   端口: {port}")
        print(f"   波特率: {baudrate}")
        
        # 基本配置
        self.config = Config()
        self.config.serial.port = port
        self.config.serial.baudrate = baudrate
        self.config.serial.timeout = 0.1
        self.config.processing.data_format = "ascii"
        self.config.processing.enable_filtering = False
        
        # 初始化数据处理
        self.quaternion_processor = QuaternionProcessor(self.config)
        self.quaternion_processor.set_data_format('ascii')
        self.serial_manager = SerialManager(self.config, self._process_data)
        
        # 四元数数据 - 正确的重置逻辑
        self.sensor_quaternion = {'w': 1.0, 'x': 0.0, 'y': 0.0, 'z': 0.0}  # 传感器原始四元数
        self.offset_quaternion = {'w': 1.0, 'x': 0.0, 'y': 0.0, 'z': 0.0}  # 偏移量四元数（重置时记录）
        self.model_quaternion = {'w': 1.0, 'x': 0.0, 'y': 0.0, 'z': 0.0}   # 模型显示四元数（移除偏移量后）
        
        self.data_lock = threading.Lock()
        self.data_updated = False
        
        # 重置功能
        self.reset_requested = False
        self.reset_count = 0
        
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
        """处理串口数据 - 正确的偏移量逻辑"""
        try:
            processed_data = self.quaternion_processor.process_raw_data(raw_data)
            
            if processed_data:
                latest_point = processed_data[-1]
                
                with self.data_lock:
                    # 1. 保存传感器原始四元数
                    self.sensor_quaternion = latest_point['quaternion'].copy()
                    
                    # 2. 检查是否需要重置
                    if self.reset_requested:
                        # 记录当前传感器四元数作为偏移量
                        self.offset_quaternion = self.sensor_quaternion.copy()
                        self.reset_requested = False
                        self.reset_count += 1
                        
                        print(f"🔄 重置 #{self.reset_count}: 记录偏移量四元数")
                        print(f"   偏移量: w={self.offset_quaternion['w']:.3f}, x={self.offset_quaternion['x']:.3f}, y={self.offset_quaternion['y']:.3f}, z={self.offset_quaternion['z']:.3f}")
                        print(f"   ✅ 偏移量已记录，模型将重置到初始姿态")
                    
                    # 3. 计算模型四元数 = 移除偏移量后的四元数
                    # 公式：model_quat = offset_quat^(-1) * sensor_quat
                    # 当sensor_quat = offset_quat时，model_quat = (1,0,0,0)
                    self.model_quaternion = QuaternionMath.remove_offset(self.sensor_quaternion, self.offset_quaternion)
                    
                    self.data_updated = True
        
        except Exception as e:
            logger.error(f"数据处理异常: {e}")
    
    def _create_visualizer(self):
        """创建3D可视化器"""
        print("🖥️ 创建3D可视化器...")
        
        # 创建可视化器
        self.vis = o3d.visualization.Visualizer()
        
        # 创建窗口
        success = self.vis.create_window(
            window_name="最终正确的四元数3D可视化器",
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
        self.sensor_mesh.paint_uniform_color([0.0, 0.8, 1.0])  # 青色
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
        
        # 设置相机视角（固定，不会被重置影响）
        view_control = self.vis.get_view_control()
        view_control.set_front([0.5, 0.5, 0.5])
        view_control.set_lookat([0, 0, 0])
        view_control.set_up([0, 0, 1])
        view_control.set_zoom(0.7)
        
        print("✅ 3D可视化器创建完成")
    
    def _update_model(self):
        """更新模型姿态 - 使用移除偏移量后的四元数"""
        try:
            # 获取模型四元数（已经移除偏移量的）
            with self.data_lock:
                if not self.data_updated:
                    return
                model_quat = self.model_quaternion.copy()
                self.data_updated = False
            
            # 转换为旋转矩阵
            rotation_matrix = QuaternionMath.to_rotation_matrix(model_quat)
            
            # 应用旋转到模型
            rotated_vertices = np.dot(self.original_vertices, rotation_matrix.T)
            
            # 更新立方体
            self.sensor_mesh.vertices = o3d.utility.Vector3dVector(rotated_vertices)
            self.sensor_mesh.compute_vertex_normals()
            self.vis.update_geometry(self.sensor_mesh)
            
        except Exception as e:
            logger.error(f"更新模型异常: {e}")
    
    def _check_key_input(self):
        """检查键盘输入"""
        try:
            import msvcrt
            if msvcrt.kbhit():
                key = msvcrt.getch().decode('utf-8').lower()
                if key == 'r':
                    self.request_reset()
                    return True
                elif key == '\x1b':  # ESC键
                    return False
        except:
            pass
        return True
    
    def request_reset(self):
        """请求重置"""
        with self.data_lock:
            self.reset_requested = True
        print("🔄 重置请求已发送...")
    
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
🎯 最终正确的四元数3D可视化器
=============================

正确的重置逻辑:
1. 用四元数计算模型朝向（不是欧拉角）
2. 按R键时，记录当前传感器四元数作为偏移量
3. 之后每次计算：模型四元数 = 偏移量^(-1) × 传感器四元数
4. 当传感器四元数等于偏移量时，模型四元数为(1,0,0,0)
5. 不重置视角，只重置模型位姿

操作:
- 左键拖拽: 旋转视角
- 右键拖拽: 平移视图
- 滚轮: 缩放视图
- 在控制台按R键: 重置模型位姿到初始状态
- 在控制台按ESC键: 退出

开始可视化...
""")
        
        try:
            # 创建3D可视化器
            self._create_visualizer()
            
            # 启动数据处理
            self._start_data_processing()
            
            print("🎮 3D可视化器已启动")
            print("💡 在控制台窗口按 R 键可重置模型位姿")
            print("💡 重置只影响模型姿态，不影响相机视角")
            
            # 主循环
            last_info_time = 0
            while True:
                # 检查键盘输入
                if not self._check_key_input():
                    break
                
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
                    with self.data_lock:
                        sensor_q = self.sensor_quaternion.copy()
                        offset_q = self.offset_quaternion.copy()
                        model_q = self.model_quaternion.copy()
                    
                    print(f"📊 状态: 重置次数={self.reset_count}")
                    print(f"   传感器四元数: w={sensor_q['w']:.3f}, x={sensor_q['x']:.3f}, y={sensor_q['y']:.3f}, z={sensor_q['z']:.3f}")
                    if self.reset_count > 0:
                        print(f"   偏移量四元数: w={offset_q['w']:.3f}, x={offset_q['x']:.3f}, y={offset_q['y']:.3f}, z={offset_q['z']:.3f}")
                    print(f"   模型四元数: w={model_q['w']:.3f}, x={model_q['x']:.3f}, y={model_q['y']:.3f}, z={model_q['z']:.3f}")
                    print(f"   公式: 模型 = 偏移量^(-1) × 传感器")
                
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
    print("🔧 配置最终正确的四元数3D可视化器")
    print("=" * 45)
    
    # 端口配置
    ports = ["COM3", "COM6", "COM12", "COM14"]
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
    baudrates = [115200, 128000, 230400, 460800]
    print(f"\n可用波特率:")
    for i, baud in enumerate(baudrates, 1):
        print(f"  {i}. {baud}")
    
    while True:
        try:
            choice = input(f"\n选择波特率 (1-{len(baudrates)}, 默认2=128000): ").strip() or "2"
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
🎯 最终正确的四元数3D可视化器
=============================

修正的逻辑:
✅ 用四元数计算模型朝向（不是欧拉角）
✅ 正确记录偏移量四元数
✅ 正确的数学公式：模型 = 偏移量^(-1) × 传感器
✅ 不重置视角，只重置模型位姿
✅ 重置后模型回到(1,0,0,0)初始姿态

开始配置...
""")
    
    try:
        # 获取用户配置
        port, baudrate = get_user_config()
        
        print(f"\n✅ 配置完成:")
        print(f"   端口: {port}")
        print(f"   波特率: {baudrate}")
        
        # 创建并运行可视化器
        visualizer = FinalQuaternion3DReset(port=port, baudrate=baudrate)
        visualizer.run()
        
    except KeyboardInterrupt:
        print("\n👋 用户取消")
    except Exception as e:
        print(f"❌ 程序异常: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
