"""
性能测试模块
测试数据处理和转换的性能
"""

import pytest
import asyncio
import time
import numpy as np
from unittest.mock import Mock, AsyncMock

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.config import Config
from src.data_processor import DataProcessor
from src.serial_manager import SerialManager


class TestDataProcessorPerformance:
    """数据处理器性能测试"""
    
    @pytest.fixture
    def config(self):
        """测试配置"""
        config = Config()
        config.processing.batch_size = 1000
        config.processing.buffer_size = 8192
        config.performance.use_multiprocessing = True
        config.performance.enable_caching = True
        return config
    
    @pytest.fixture
    def processor(self, config):
        """数据处理器实例"""
        return DataProcessor(config)
    
    def test_hex_conversion_performance(self, processor):
        """测试十六进制转换性能"""
        # 生成测试数据
        test_data = b'\x12\x34\x56\x78' * 1000  # 4KB数据
        
        start_time = time.time()
        
        # 执行转换
        result = processor._convert_data_format(test_data)
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        # 性能断言
        assert processing_time < 0.01  # 应该在10ms内完成
        assert len(result) == 1000  # 应该有1000个数据点
        
        print(f"十六进制转换性能: {processing_time*1000:.2f}ms for {len(test_data)} bytes")
    
    def test_binary_conversion_performance(self, processor):
        """测试二进制转换性能"""
        # 生成测试数据（浮点数）
        test_values = np.random.random(1000).astype(np.float32)
        test_data = test_values.tobytes()
        
        start_time = time.time()
        
        # 设置为二进制格式
        processor.config.processing.data_format = "binary"
        result = processor._convert_data_format(test_data)
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        # 性能断言
        assert processing_time < 0.005  # 应该在5ms内完成
        assert len(result) == 1000
        
        print(f"二进制转换性能: {processing_time*1000:.2f}ms for {len(test_data)} bytes")
    
    def test_cache_performance(self, processor):
        """测试缓存性能"""
        test_data = b'\x12\x34\x56\x78' * 100
        
        # 第一次转换（缓存未命中）
        start_time = time.time()
        result1 = processor._convert_data_format(test_data)
        first_time = time.time() - start_time
        
        # 第二次转换（缓存命中）
        start_time = time.time()
        result2 = processor._convert_data_format(test_data)
        second_time = time.time() - start_time
        
        # 验证结果一致性
        assert result1 == result2
        
        # 缓存应该显著提高性能
        assert second_time < first_time * 0.5
        
        print(f"缓存性能提升: {first_time/second_time:.2f}x")
    
    @pytest.mark.asyncio
    async def test_async_processing_performance(self, processor):
        """测试异步处理性能"""
        # 生成多个数据包
        test_packets = [b'\x12\x34\x56\x78' * 100 for _ in range(100)]
        
        start_time = time.time()
        
        # 启动处理器
        processor_task = asyncio.create_task(processor.start())
        
        # 发送数据包
        for packet in test_packets:
            await processor.process_data(packet)
        
        # 等待处理完成
        await asyncio.sleep(1.0)
        
        # 停止处理器
        await processor.stop()
        processor_task.cancel()
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # 获取处理结果
        processed_data = processor.get_processed_data()
        
        # 性能断言
        assert len(processed_data) > 0
        assert total_time < 2.0  # 应该在2秒内完成
        
        throughput = len(test_packets) / total_time
        print(f"异步处理吞吐量: {throughput:.2f} packets/second")


class TestSerialManagerPerformance:
    """串口管理器性能测试"""
    
    @pytest.fixture
    def config(self):
        """测试配置"""
        config = Config()
        config.serial.port = "MOCK"  # 使用模拟串口
        config.processing.batch_size = 100
        return config
    
    @pytest.fixture
    def mock_callback(self):
        """模拟数据回调"""
        return AsyncMock()
    
    def test_buffer_management_performance(self, config, mock_callback):
        """测试缓冲区管理性能"""
        manager = SerialManager(config, mock_callback)
        
        # 模拟大量数据写入缓冲区
        large_data = b'x' * 10000
        
        start_time = time.time()
        
        # 模拟缓冲区操作
        for i in range(100):
            manager.read_buffer.extend(large_data[:100])
        
        end_time = time.time()
        buffer_time = end_time - start_time
        
        # 性能断言
        assert buffer_time < 0.1  # 应该在100ms内完成
        assert len(manager.read_buffer) == 10000
        
        print(f"缓冲区管理性能: {buffer_time*1000:.2f}ms for 1MB data")


class TestMemoryPerformance:
    """内存性能测试"""
    
    def test_memory_usage(self):
        """测试内存使用情况"""
        import psutil
        import gc
        
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # 创建大量数据
        config = Config()
        processor = DataProcessor(config)
        
        # 处理大量数据
        large_data = b'\x12\x34' * 50000  # 100KB
        for _ in range(100):
            processor._convert_data_format(large_data)
        
        # 强制垃圾回收
        gc.collect()
        
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory
        
        # 内存增长应该在合理范围内
        assert memory_increase < 100  # 不应该超过100MB
        
        print(f"内存使用: 初始 {initial_memory:.2f}MB, 最终 {final_memory:.2f}MB, 增长 {memory_increase:.2f}MB")


class TestThroughputBenchmark:
    """吞吐量基准测试"""
    
    def test_data_throughput_benchmark(self):
        """数据吞吐量基准测试"""
        config = Config()
        config.processing.batch_size = 1000
        config.performance.enable_caching = True
        
        processor = DataProcessor(config)
        
        # 生成测试数据
        data_sizes = [1024, 4096, 16384, 65536]  # 1KB, 4KB, 16KB, 64KB
        
        results = {}
        
        for size in data_sizes:
            test_data = b'\x12\x34\x56\x78' * (size // 4)
            
            start_time = time.time()
            
            # 处理100次
            for _ in range(100):
                processor._convert_data_format(test_data)
            
            end_time = time.time()
            total_time = end_time - start_time
            
            throughput = (size * 100) / total_time / 1024 / 1024  # MB/s
            results[size] = throughput
            
            print(f"数据大小 {size} bytes: {throughput:.2f} MB/s")
        
        # 验证吞吐量随数据大小的变化
        assert results[65536] > results[1024]  # 大数据块应该有更高的吞吐量


if __name__ == "__main__":
    # 运行性能测试
    pytest.main([__file__, "-v", "-s"])
