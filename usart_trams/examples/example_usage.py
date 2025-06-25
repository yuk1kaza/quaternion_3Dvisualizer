#!/usr/bin/env python3
"""
USART Trams 使用示例
演示如何使用各个组件
"""

import asyncio
import sys
import os
import time
import random

# 添加项目根目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.config import Config
from src.data_processor import DataProcessor
from src.serial_manager import SerialManager


class MockSerialData:
    """模拟串口数据生成器"""
    
    def __init__(self):
        self.running = False
        self.data_callback = None
    
    async def start_simulation(self, callback, duration=30):
        """开始模拟数据生成"""
        self.data_callback = callback
        self.running = True
        
        print("开始模拟串口数据生成...")
        start_time = time.time()
        
        while self.running and (time.time() - start_time) < duration:
            # 生成模拟数据
            data = self._generate_mock_data()
            
            # 发送数据
            if self.data_callback:
                await self.data_callback(data)
            
            # 模拟数据间隔
            await asyncio.sleep(0.01)  # 10ms间隔
        
        print("模拟数据生成结束")
    
    def _generate_mock_data(self):
        """生成模拟数据"""
        # 生成正弦波数据
        timestamp = time.time()
        value = int(1000 * (1 + 0.8 * math.sin(timestamp * 2) + 0.2 * random.random()))
        
        # 转换为十六进制字节
        return value.to_bytes(2, byteorder='little', signed=False)
    
    def stop(self):
        """停止模拟"""
        self.running = False


async def example_basic_usage():
    """基本使用示例"""
    print("=" * 60)
    print("基本使用示例")
    print("=" * 60)
    
    # 创建配置
    config = Config()
    config.processing.data_format = "hex"
    config.processing.batch_size = 50
    
    # 创建数据处理器
    processor = DataProcessor(config)
    
    # 启动处理器
    processor_task = asyncio.create_task(processor.start())
    
    # 模拟数据生成
    mock_data = MockSerialData()
    
    # 运行模拟
    await mock_data.start_simulation(processor.process_data, duration=10)
    
    # 获取处理结果
    processed_data = processor.get_processed_data()
    print(f"处理了 {len(processed_data)} 个数据点")
    
    if processed_data:
        latest_data = processed_data[-10:]  # 最后10个数据点
        print("最新数据点:")
        for i, point in enumerate(latest_data):
            print(f"  {i+1}: 时间={point['timestamp']:.3f}, 值={point['value']:.2f}")
    
    # 停止处理器
    await processor.stop()
    processor_task.cancel()


async def example_performance_monitoring():
    """性能监控示例"""
    print("\n" + "=" * 60)
    print("性能监控示例")
    print("=" * 60)
    
    # 创建高性能配置
    config = Config()
    config.processing.batch_size = 100
    config.processing.buffer_size = 16384
    config.performance.enable_caching = True
    config.performance.use_multiprocessing = True
    
    # 创建数据处理器
    processor = DataProcessor(config)
    
    # 启动处理器
    processor_task = asyncio.create_task(processor.start())
    
    # 性能监控
    start_time = time.time()
    data_count = 0
    
    async def performance_monitor():
        nonlocal data_count
        while True:
            await asyncio.sleep(2.0)  # 每2秒报告一次
            
            current_time = time.time()
            elapsed = current_time - start_time
            
            processed_data = processor.get_processed_data()
            current_count = len(processed_data)
            
            rate = (current_count - data_count) / 2.0  # 每秒处理数据点数
            data_count = current_count
            
            print(f"性能统计 - 运行时间: {elapsed:.1f}s, "
                  f"总数据点: {current_count}, "
                  f"处理速率: {rate:.1f} points/s")
            
            if elapsed > 15:  # 运行15秒后停止
                break
    
    # 启动监控任务
    monitor_task = asyncio.create_task(performance_monitor())
    
    # 模拟高速数据
    mock_data = MockSerialData()
    data_task = asyncio.create_task(
        mock_data.start_simulation(processor.process_data, duration=15)
    )
    
    # 等待完成
    await asyncio.gather(monitor_task, data_task, return_exceptions=True)
    
    # 停止处理器
    await processor.stop()
    processor_task.cancel()


async def example_data_formats():
    """数据格式示例"""
    print("\n" + "=" * 60)
    print("数据格式转换示例")
    print("=" * 60)
    
    config = Config()
    processor = DataProcessor(config)
    
    # 测试不同数据格式
    formats = ['hex', 'binary', 'ascii']
    test_data = {
        'hex': b'\x12\x34\x56\x78\x9A\xBC\xDE\xF0',
        'binary': b'\x00\x00\x80\x3f\x00\x00\x00\x40',  # 浮点数 1.0, 2.0
        'ascii': b'123.45,678.90,111.22,333.44'
    }
    
    for fmt in formats:
        print(f"\n测试 {fmt.upper()} 格式:")
        print(f"原始数据: {test_data[fmt]}")
        
        processor.config.processing.data_format = fmt
        result = processor._convert_data_format(test_data[fmt])
        
        if result:
            print(f"转换结果: {result[:5]}...")  # 显示前5个值
            print(f"数据点数: {len(result)}")
        else:
            print("转换失败")


async def example_configuration():
    """配置示例"""
    print("\n" + "=" * 60)
    print("配置管理示例")
    print("=" * 60)
    
    # 创建默认配置
    config = Config()
    
    print("默认配置:")
    print(f"  串口: {config.serial.port}")
    print(f"  波特率: {config.serial.baudrate}")
    print(f"  批处理大小: {config.processing.batch_size}")
    print(f"  缓冲区大小: {config.processing.buffer_size}")
    print(f"  启用缓存: {config.performance.enable_caching}")
    
    # 获取优化建议
    suggestions = config.get_optimal_settings()
    print(f"\n系统优化建议:")
    for key, value in suggestions.items():
        print(f"  {key}: {value}")
    
    # 应用优化设置
    config.apply_optimal_settings()
    print(f"\n应用优化后:")
    print(f"  批处理大小: {config.processing.batch_size}")
    print(f"  缓冲区大小: {config.processing.buffer_size}")
    print(f"  工作进程数: {config.performance.worker_processes}")
    
    # 保存配置
    config.save_config()
    print("\n配置已保存到 config.json")


async def example_error_handling():
    """错误处理示例"""
    print("\n" + "=" * 60)
    print("错误处理示例")
    print("=" * 60)
    
    config = Config()
    processor = DataProcessor(config)
    
    # 测试无效数据处理
    invalid_data_sets = [
        b'',  # 空数据
        b'\xFF' * 3,  # 奇数长度数据
        b'invalid_ascii_data_with_no_numbers',  # 无效ASCII数据
    ]
    
    for i, data in enumerate(invalid_data_sets):
        print(f"\n测试无效数据 {i+1}: {data}")
        
        try:
            result = processor._convert_data_format(data)
            if result:
                print(f"  处理成功: {len(result)} 个数据点")
            else:
                print("  处理失败: 返回空结果")
        except Exception as e:
            print(f"  捕获异常: {e}")


import math  # 添加缺失的导入

async def main():
    """主函数"""
    print("USART Trams 使用示例")
    print("=" * 60)
    
    try:
        # 运行各种示例
        await example_basic_usage()
        await example_performance_monitoring()
        await example_data_formats()
        await example_configuration()
        await example_error_handling()
        
        print("\n" + "=" * 60)
        print("所有示例运行完成！")
        print("=" * 60)
        
    except KeyboardInterrupt:
        print("\n示例被用户中断")
    except Exception as e:
        print(f"\n示例运行出错: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
