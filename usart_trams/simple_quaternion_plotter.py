#!/usr/bin/env python3
"""
简化版四元数时间轴绘图工具
使用纯Python实现，无需复杂依赖
"""

import asyncio
import logging
import sys
import time
import csv
from pathlib import Path
from collections import deque
import threading
import serial.tools.list_ports

# 添加src目录到路径
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from src.config import Config
from src.serial_manager import SerialManager
from src.quaternion_processor import QuaternionProcessor

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SimpleQuaternionPlotter:
    """简化版四元数绘图器"""
    
    def __init__(self):
        self.data_storage = []
        self.is_running = False
        self.start_time = None
        self.data_count = 0
        
    def list_ports(self):
        """列出可用串口"""
        ports = serial.tools.list_ports.comports()
        return [port.device for port in ports]
    
    def get_user_config(self):
        """获取用户配置"""
        print("\n📊 四元数时间轴绘图工具")
        print("=" * 40)
        
        # 显示可用端口
        available_ports = self.list_ports()
        if not available_ports:
            print("❌ 未发现可用串口")
            return None
            
        print(f"\n可用串口:")
        for i, port in enumerate(available_ports, 1):
            print(f"  {i}. {port}")
        
        # 选择端口
        while True:
            try:
                choice = input(f"\n请选择串口 (1-{len(available_ports)}): ").strip()
                port_index = int(choice) - 1
                if 0 <= port_index < len(available_ports):
                    selected_port = available_ports[port_index]
                    break
                else:
                    print("❌ 无效选择")
            except ValueError:
                print("❌ 请输入数字")
        
        # 选择波特率
        baudrates = [9600, 19200, 38400, 57600, 115200, 128000, 230400, 460800, 921600]
        print(f"\n可用波特率:")
        for i, baud in enumerate(baudrates, 1):
            print(f"  {i}. {baud}")
        
        while True:
            try:
                choice = input(f"\n请选择波特率 (1-{len(baudrates)}, 默认5=115200): ").strip() or "5"
                baud_index = int(choice) - 1
                if 0 <= baud_index < len(baudrates):
                    selected_baudrate = baudrates[baud_index]
                    break
                else:
                    print("❌ 无效选择")
            except ValueError:
                print("❌ 请输入数字")
        
        # 选择数据格式
        formats = ["ascii", "binary"]
        print(f"\n数据格式:")
        for i, fmt in enumerate(formats, 1):
            print(f"  {i}. {fmt}")
        
        while True:
            try:
                choice = input(f"\n请选择数据格式 (1-{len(formats)}, 默认1=ascii): ").strip() or "1"
                fmt_index = int(choice) - 1
                if 0 <= fmt_index < len(formats):
                    selected_format = formats[fmt_index]
                    break
                else:
                    print("❌ 无效选择")
            except ValueError:
                print("❌ 请输入数字")
        
        # 设置记录时长
        while True:
            try:
                duration = input("\n记录时长 (秒, 默认60): ").strip() or "60"
                duration = int(duration)
                if duration > 0:
                    break
                else:
                    print("❌ 时长必须大于0")
            except ValueError:
                print("❌ 请输入有效数字")
        
        return {
            'port': selected_port,
            'baudrate': selected_baudrate,
            'format': selected_format,
            'duration': duration
        }
    
    async def process_data(self, raw_data: bytes):
        """处理数据"""
        try:
            processed_data = self.quaternion_processor.process_raw_data(raw_data)
            
            if processed_data:
                current_time = time.time()
                
                for data_point in processed_data:
                    self.data_count += 1
                    
                    # 记录数据
                    relative_time = current_time - self.start_time
                    quat = data_point['quaternion']
                    euler = data_point['euler_degrees']
                    
                    data_record = {
                        'time': relative_time,
                        'w': quat['w'],
                        'x': quat['x'],
                        'y': quat['y'],
                        'z': quat['z'],
                        'roll': euler['roll'],
                        'pitch': euler['pitch'],
                        'yaw': euler['yaw']
                    }
                    
                    self.data_storage.append(data_record)
                    
                    # 实时显示
                    if self.data_count % 10 == 0:  # 每10个数据点显示一次
                        rate = self.data_count / relative_time if relative_time > 0 else 0
                        print(f"\r📊 时间: {relative_time:.1f}s | 数据: {self.data_count} | 速率: {rate:.1f} Hz | "
                              f"四元数: w={quat['w']:.3f}, x={quat['x']:.3f}, y={quat['y']:.3f}, z={quat['z']:.3f}", end="")
                
        except Exception as e:
            logger.error(f"处理数据异常: {e}")
    
    def save_to_csv(self, filename):
        """保存数据到CSV文件"""
        try:
            with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
                fieldnames = ['time', 'w', 'x', 'y', 'z', 'roll', 'pitch', 'yaw']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                
                writer.writeheader()
                for record in self.data_storage:
                    writer.writerow(record)
                    
            print(f"\n✅ 数据已保存到: {filename}")
            print(f"   总记录数: {len(self.data_storage)}")
            
        except Exception as e:
            print(f"❌ 保存失败: {e}")
    
    def generate_plot_script(self, csv_filename):
        """生成绘图脚本"""
        script_content = f'''#!/usr/bin/env python3
"""
四元数数据绘图脚本
自动生成，用于绘制 {csv_filename} 中的数据
"""

import pandas as pd
import matplotlib.pyplot as plt

# 读取数据
data = pd.read_csv('{csv_filename}')

# 创建图形
fig, axes = plt.subplots(2, 2, figsize=(15, 10))
fig.suptitle('四元数时间轴图', fontsize=16)

# 绘制四元数分量
axes[0, 0].plot(data['time'], data['w'], 'r-', linewidth=1.5, label='W')
axes[0, 0].set_title('W分量')
axes[0, 0].set_ylabel('W')
axes[0, 0].grid(True)
axes[0, 0].legend()

axes[0, 1].plot(data['time'], data['x'], 'g-', linewidth=1.5, label='X')
axes[0, 1].set_title('X分量')
axes[0, 1].set_ylabel('X')
axes[0, 1].grid(True)
axes[0, 1].legend()

axes[1, 0].plot(data['time'], data['y'], 'b-', linewidth=1.5, label='Y')
axes[1, 0].set_title('Y分量')
axes[1, 0].set_ylabel('Y')
axes[1, 0].set_xlabel('时间 (秒)')
axes[1, 0].grid(True)
axes[1, 0].legend()

axes[1, 1].plot(data['time'], data['z'], 'm-', linewidth=1.5, label='Z')
axes[1, 1].set_title('Z分量')
axes[1, 1].set_ylabel('Z')
axes[1, 1].set_xlabel('时间 (秒)')
axes[1, 1].grid(True)
axes[1, 1].legend()

plt.tight_layout()
plt.show()

# 额外绘制欧拉角
fig2, axes2 = plt.subplots(3, 1, figsize=(15, 10))
fig2.suptitle('欧拉角时间轴图', fontsize=16)

axes2[0].plot(data['time'], data['roll'], 'r-', linewidth=1.5)
axes2[0].set_title('Roll角')
axes2[0].set_ylabel('Roll (度)')
axes2[0].grid(True)

axes2[1].plot(data['time'], data['pitch'], 'g-', linewidth=1.5)
axes2[1].set_title('Pitch角')
axes2[1].set_ylabel('Pitch (度)')
axes2[1].grid(True)

axes2[2].plot(data['time'], data['yaw'], 'b-', linewidth=1.5)
axes2[2].set_title('Yaw角')
axes2[2].set_ylabel('Yaw (度)')
axes2[2].set_xlabel('时间 (秒)')
axes2[2].grid(True)

plt.tight_layout()
plt.show()

print("绘图完成！")
'''
        
        script_filename = f"plot_{csv_filename.replace('.csv', '.py')}"
        try:
            with open(script_filename, 'w', encoding='utf-8') as f:
                f.write(script_content)
            print(f"✅ 绘图脚本已生成: {script_filename}")
            print(f"   运行命令: python {script_filename}")
        except Exception as e:
            print(f"❌ 生成绘图脚本失败: {e}")
    
    async def run_data_collection(self, config):
        """运行数据收集"""
        try:
            # 配置串口和数据处理
            cfg = Config()
            cfg.serial.port = config['port']
            cfg.serial.baudrate = config['baudrate']
            cfg.serial.timeout = 0.1
            cfg.processing.data_format = config['format']
            cfg.processing.enable_filtering = False
            
            # 初始化处理器
            self.quaternion_processor = QuaternionProcessor(cfg)
            self.quaternion_processor.set_data_format(config['format'])
            serial_manager = SerialManager(cfg, self.process_data)
            
            print(f"\n🚀 开始数据收集...")
            print(f"   端口: {config['port']}")
            print(f"   波特率: {config['baudrate']}")
            print(f"   格式: {config['format']}")
            print(f"   时长: {config['duration']}秒")
            print(f"\n按 Ctrl+C 可提前停止\n")
            
            # 启动数据收集
            self.start_time = time.time()
            self.data_count = 0
            self.is_running = True
            
            await serial_manager.start()
            
            # 等待指定时长
            await asyncio.sleep(config['duration'])
            
            await serial_manager.stop()
            
        except KeyboardInterrupt:
            print(f"\n\n⏹️  用户中断收集")
        except Exception as e:
            print(f"\n❌ 数据收集异常: {e}")
        finally:
            self.is_running = False
    
    async def run(self):
        """运行程序"""
        try:
            # 获取用户配置
            config = self.get_user_config()
            if not config:
                return
            
            # 运行数据收集
            await self.run_data_collection(config)
            
            # 保存数据
            if self.data_storage:
                timestamp = time.strftime("%Y%m%d_%H%M%S")
                csv_filename = f"quaternion_data_{timestamp}.csv"
                
                print(f"\n\n📊 数据收集完成!")
                print(f"   收集时长: {time.time() - self.start_time:.1f}秒")
                print(f"   数据点数: {len(self.data_storage)}")
                print(f"   平均速率: {len(self.data_storage) / (time.time() - self.start_time):.1f} Hz")
                
                # 保存CSV
                self.save_to_csv(csv_filename)
                
                # 生成绘图脚本
                self.generate_plot_script(csv_filename)
                
                print(f"\n💡 使用说明:")
                print(f"   1. 安装matplotlib: pip install matplotlib pandas")
                print(f"   2. 运行绘图脚本: python plot_{csv_filename.replace('.csv', '.py')}")
                print(f"   3. 或直接用Excel等软件打开CSV文件")
                
            else:
                print(f"\n⚠️  未收集到数据")
                
        except Exception as e:
            print(f"❌ 程序异常: {e}")
            import traceback
            traceback.print_exc()


def main():
    """主函数"""
    print("""
📊 简化版四元数时间轴绘图工具
============================

功能特性:
✅ 手动选择串口和波特率
✅ 支持ASCII和二进制数据格式
✅ 实时数据收集和显示
✅ 自动保存CSV数据文件
✅ 自动生成matplotlib绘图脚本

使用流程:
1. 选择串口、波特率、数据格式
2. 设置记录时长
3. 开始数据收集
4. 自动保存数据和生成绘图脚本
5. 运行绘图脚本查看图表

开始配置...
""")
    
    try:
        plotter = SimpleQuaternionPlotter()
        asyncio.run(plotter.run())
    except KeyboardInterrupt:
        print("\n👋 程序已退出")
    except Exception as e:
        logger.error(f"程序异常: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
