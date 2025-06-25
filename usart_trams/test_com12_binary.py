#!/usr/bin/env python3
"""
COM12二进制数据测试工具
测试修复后的二进制四元数解析功能
"""

import asyncio
import logging
import sys
import time
import struct
from pathlib import Path

# 添加src目录到路径
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from src.config import Config
from src.serial_manager import SerialManager
from src.quaternion_processor import QuaternionProcessor

# 配置日志
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


class COM12BinaryTester:
    """COM12二进制数据测试器"""
    
    def __init__(self):
        self.config = Config()
        self.config.serial.port = "COM12"
        self.config.serial.baudrate = 128000
        self.config.serial.timeout = 0.1
        
        self.config.processing.data_format = "binary"
        self.config.processing.enable_filtering = False  # 关闭滤波，便于测试
        
        # 初始化处理器
        self.quaternion_processor = QuaternionProcessor(self.config)
        self.quaternion_processor.set_data_format('binary')
        
        # 统计数据
        self.data_count = 0
        self.quaternion_count = 0
        self.start_time = None
        
        print("✅ COM12二进制测试器初始化完成")
    
    async def process_test_data(self, raw_data: bytes):
        """处理测试数据"""
        try:
            self.data_count += 1
            
            print(f"\n📦 数据包 {self.data_count}:")
            print(f"   长度: {len(raw_data)} 字节")
            print(f"   十六进制: {raw_data.hex()}")
            
            # 尝试手动解析
            if len(raw_data) >= 16:
                print(f"   手动解析尝试:")
                
                # 小端序 w,x,y,z
                try:
                    w, x, y, z = struct.unpack('<ffff', raw_data[:16])
                    magnitude = (w*w + x*x + y*y + z*z) ** 0.5
                    print(f"     小端(wxyz): w={w:.4f}, x={x:.4f}, y={y:.4f}, z={z:.4f}, |q|={magnitude:.4f}")
                except:
                    print(f"     小端(wxyz): 解析失败")
                
                # 小端序 x,y,z,w
                try:
                    x, y, z, w = struct.unpack('<ffff', raw_data[:16])
                    magnitude = (w*w + x*x + y*y + z*z) ** 0.5
                    print(f"     小端(xyzw): w={w:.4f}, x={x:.4f}, y={y:.4f}, z={z:.4f}, |q|={magnitude:.4f}")
                except:
                    print(f"     小端(xyzw): 解析失败")
                
                # 大端序 w,x,y,z
                try:
                    w, x, y, z = struct.unpack('>ffff', raw_data[:16])
                    magnitude = (w*w + x*x + y*y + z*z) ** 0.5
                    print(f"     大端(wxyz): w={w:.4f}, x={x:.4f}, y={y:.4f}, z={z:.4f}, |q|={magnitude:.4f}")
                except:
                    print(f"     大端(wxyz): 解析失败")
            
            # 使用处理器解析
            processed_data = self.quaternion_processor.process_raw_data(raw_data)
            
            if processed_data:
                self.quaternion_count += len(processed_data)
                print(f"   ✅ 处理器解析成功: {len(processed_data)} 个四元数")
                
                for i, data_point in enumerate(processed_data):
                    quat = data_point['quaternion']
                    euler = data_point['euler_degrees']
                    
                    print(f"     四元数 {i+1}: w={quat['w']:.4f}, x={quat['x']:.4f}, y={quat['y']:.4f}, z={quat['z']:.4f}")
                    print(f"     欧拉角 {i+1}: roll={euler['roll']:.1f}°, pitch={euler['pitch']:.1f}°, yaw={euler['yaw']:.1f}°")
            else:
                print(f"   ❌ 处理器解析失败")
            
        except Exception as e:
            print(f"   ❌ 处理异常: {e}")
    
    async def run_test(self, duration=30):
        """运行测试"""
        print(f"""
🧪 COM12二进制数据测试
====================

配置:
- 端口: {self.config.serial.port}
- 波特率: {self.config.serial.baudrate}
- 数据格式: binary
- 测试时长: {duration}秒

开始测试...
""")
        
        try:
            # 创建串口管理器
            serial_manager = SerialManager(self.config, self.process_test_data)
            
            self.start_time = time.time()
            
            # 启动串口
            await serial_manager.start()
            
            # 运行测试
            await asyncio.sleep(duration)
            
            # 停止串口
            await serial_manager.stop()
            
            # 显示统计
            elapsed = time.time() - self.start_time
            data_rate = self.data_count / elapsed if elapsed > 0 else 0
            quat_rate = self.quaternion_count / elapsed if elapsed > 0 else 0
            
            print(f"""
📊 测试结果:
============
运行时间: {elapsed:.1f}秒
数据包数: {self.data_count}
四元数数: {self.quaternion_count}
数据包速率: {data_rate:.1f} packets/s
四元数速率: {quat_rate:.1f} quat/s

""")
            
            if self.quaternion_count > 0:
                print("✅ 二进制解析功能正常工作")
                print("💡 可以使用COM12配置运行3D可视化")
            else:
                print("❌ 二进制解析未能提取四元数")
                print("💡 可能需要调整数据格式或解析逻辑")
        
        except Exception as e:
            print(f"❌ 测试失败: {e}")
            import traceback
            traceback.print_exc()


async def main():
    """主函数"""
    try:
        tester = COM12BinaryTester()
        await tester.run_test(duration=20)
        
    except Exception as e:
        logger.error(f"测试异常: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
