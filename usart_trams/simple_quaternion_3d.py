#!/usr/bin/env python3
"""
精简版四元数3D可视化器
仅保留核心功能：串口四元数数据的3D可视化
去除所有附加功能，专注于基本的3D显示
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
logging.basicConfig(level=logging.WARNING)  # 减少日志输出
logger = logging.getLogger(__name__)

try:
    import open3d as o3d
except ImportError:
    print("❌ 需要安装Open3D: pip install open3d")
    sys.exit(1)


class SimpleQuaternion3D:
    """精简版四元数3D可视化器"""
    
    def __init__(self, port="COM12", baudrate=128000):
        print(f"🎯 精简版四元数3D可视化器")
        print(f"   端口: {port}")
        print(f"   波特率: {baudrate}")
        
        # 基本配置
        self.config = Config()
        self.config.serial.port = port
        self.config.serial.baudrate = baudrate
        self.config.serial.timeout = 0.1
        self.config.processing.data_format = "ascii"
        self.config.processing.enable_filtering = False  # 关闭滤波
        
        # 初始化数据处理
        self.quaternion_processor = QuaternionProcessor(self.config)
        self.quaternion_processor.set_data_format('ascii')
        self.serial_manager = SerialManager(self.config, self._process_data)
        
        # 当前四元数数据
        self.current_quaternion = {'w': 1.0, 'x': 0.0, 'y': 0.0, 'z': 0.0}
        self.data_lock = threading.Lock()
        self.data_updated = False
        
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
            processed_data = self.quaternion_processor.process_raw_data(raw_data)
            
            if processed_data:
                # 只保留最新数据
                latest_point = processed_data[-1]
                
                with self.data_lock:
                    self.current_quaternion = latest_point['quaternion'].copy()
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
            window_name="精简版四元数3D可视化器",
            width=800,
            height=600,
            left=200,
            top=200
        )
        
        if not success:
            raise RuntimeError("窗口创建失败")
        
        # 创建传感器立方体
        self.sensor_mesh = o3d.geometry.TriangleMesh.create_box(width=2.0, height=1.0, depth=0.5)
        self.sensor_mesh.translate([-1.0, -0.5, -0.25])
        self.sensor_mesh.paint_uniform_color([0.2, 0.6, 1.0])  # 蓝色
        self.sensor_mesh.compute_vertex_normals()
        
        # 创建坐标轴
        coordinate_frame = o3d.geometry.TriangleMesh.create_coordinate_frame(size=2.0)
        
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
    
    def _update_sensor(self):
        """更新传感器姿态"""
        try:
            # 获取最新四元数
            with self.data_lock:
                if not self.data_updated:
                    return
                quat = self.current_quaternion.copy()
                self.data_updated = False
            
            w, x, y, z = quat['w'], quat['x'], quat['y'], quat['z']
            
            # 四元数归一化
            norm = math.sqrt(w*w + x*x + y*y + z*z)
            if norm > 0:
                w, x, y, z = w/norm, x/norm, y/norm, z/norm
            
            # 四元数转旋转矩阵
            rotation_matrix = np.array([
                [1-2*(y*y+z*z), 2*(x*y-w*z), 2*(x*z+w*y)],
                [2*(x*y+w*z), 1-2*(x*x+z*z), 2*(y*z-w*x)],
                [2*(x*z-w*y), 2*(y*z+w*x), 1-2*(x*x+y*y)]
            ])
            
            # 应用旋转
            rotated_vertices = np.dot(self.original_vertices, rotation_matrix.T)
            
            # 更新立方体
            self.sensor_mesh.vertices = o3d.utility.Vector3dVector(rotated_vertices)
            self.sensor_mesh.compute_vertex_normals()
            self.vis.update_geometry(self.sensor_mesh)
            
        except Exception as e:
            logger.error(f"更新传感器异常: {e}")
    
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
🎯 精简版四元数3D可视化器
========================

功能:
✅ 串口四元数数据接收
✅ 实时3D立方体旋转显示
✅ 鼠标交互控制视角

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
            
            print("🎮 3D可视化器已启动，立方体将跟随四元数数据旋转")
            
            # 主循环
            while True:
                # 更新传感器姿态
                self._update_sensor()
                
                # 检查窗口事件
                if not self.vis.poll_events():
                    break
                
                # 渲染
                self.vis.update_renderer()
                
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
    print("🔧 配置精简版四元数3D可视化器")
    print("=" * 40)
    
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
🎯 精简版四元数3D可视化器
========================

特点:
✅ 极简设计，只保留核心3D可视化功能
✅ 无附加功能，专注于基本显示
✅ 轻量级，启动快速
✅ 直观的3D立方体旋转显示

开始配置...
""")
    
    try:
        # 获取用户配置
        port, baudrate = get_user_config()
        
        print(f"\n✅ 配置完成:")
        print(f"   端口: {port}")
        print(f"   波特率: {baudrate}")
        
        # 创建并运行可视化器
        visualizer = SimpleQuaternion3D(port=port, baudrate=baudrate)
        visualizer.run()
        
    except KeyboardInterrupt:
        print("\n👋 用户取消")
    except Exception as e:
        print(f"❌ 程序异常: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
