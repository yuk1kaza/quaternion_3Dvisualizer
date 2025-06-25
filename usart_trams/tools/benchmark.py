#!/usr/bin/env python3
"""
性能基准测试工具
用于测试和优化系统性能
"""

import time
import asyncio
import argparse
import statistics
import sys
import os
from typing import List, Dict, Any

# 添加项目根目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.config import Config
from src.data_processor import DataProcessor
from src.serial_manager import SerialManager


class PerformanceBenchmark:
    """性能基准测试类"""
    
    def __init__(self):
        self.config = Config()
        self.results = {}
    
    def run_data_conversion_benchmark(self, iterations: int = 1000) -> Dict[str, Any]:
        """数据转换性能基准测试"""
        print(f"运行数据转换基准测试 ({iterations} 次迭代)...")
        
        processor = DataProcessor(self.config)
        
        # 测试不同数据格式
        formats = ['hex', 'binary', 'ascii']
        test_data = {
            'hex': b'\x12\x34\x56\x78' * 250,  # 1KB
            'binary': b'\x00\x00\x80\x3f' * 250,  # 1KB 浮点数
            'ascii': b'123.45,678.90,111.22,333.44,' * 50  # 1KB ASCII
        }
        
        results = {}
        
        for fmt in formats:
            print(f"  测试 {fmt} 格式...")
            processor.config.processing.data_format = fmt
            
            times = []
            for _ in range(iterations):
                start_time = time.perf_counter()
                result = processor._convert_data_format(test_data[fmt])
                end_time = time.perf_counter()
                
                if result:  # 只记录成功的转换
                    times.append((end_time - start_time) * 1000)  # 转换为毫秒
            
            if times:
                results[fmt] = {
                    'mean_ms': statistics.mean(times),
                    'median_ms': statistics.median(times),
                    'min_ms': min(times),
                    'max_ms': max(times),
                    'std_ms': statistics.stdev(times) if len(times) > 1 else 0,
                    'throughput_mbps': (len(test_data[fmt]) / 1024 / 1024) / (statistics.mean(times) / 1000)
                }
        
        return results
    
    def run_buffer_benchmark(self, buffer_sizes: List[int] = None) -> Dict[str, Any]:
        """缓冲区性能基准测试"""
        if buffer_sizes is None:
            buffer_sizes = [1024, 4096, 8192, 16384, 32768]
        
        print(f"运行缓冲区基准测试...")
        
        results = {}
        
        for size in buffer_sizes:
            print(f"  测试缓冲区大小: {size} bytes")
            
            # 创建测试数据
            test_data = b'x' * size
            buffer = bytearray()
            
            # 测试写入性能
            start_time = time.perf_counter()
            for _ in range(1000):
                buffer.extend(test_data)
                if len(buffer) > size * 10:
                    del buffer[:size * 5]  # 清理一半数据
            end_time = time.perf_counter()
            
            write_time = end_time - start_time
            
            # 测试读取性能
            start_time = time.perf_counter()
            for _ in range(1000):
                if len(buffer) >= size:
                    data = bytes(buffer[:size])
                    del buffer[:size]
            end_time = time.perf_counter()
            
            read_time = end_time - start_time
            
            results[size] = {
                'write_time_ms': write_time * 1000,
                'read_time_ms': read_time * 1000,
                'write_throughput_mbps': (size * 1000 / 1024 / 1024) / write_time,
                'read_throughput_mbps': (size * 1000 / 1024 / 1024) / read_time
            }
        
        return results
    
    async def run_async_benchmark(self, duration_seconds: int = 10) -> Dict[str, Any]:
        """异步处理性能基准测试"""
        print(f"运行异步处理基准测试 ({duration_seconds} 秒)...")
        
        processor = DataProcessor(self.config)
        
        # 统计变量
        packets_sent = 0
        packets_processed = 0
        start_time = time.time()
        
        async def data_sender():
            nonlocal packets_sent
            test_data = b'\x12\x34\x56\x78' * 100  # 400 bytes
            
            while time.time() - start_time < duration_seconds:
                await processor.process_data(test_data)
                packets_sent += 1
                await asyncio.sleep(0.001)  # 1ms间隔
        
        async def data_monitor():
            nonlocal packets_processed
            while time.time() - start_time < duration_seconds:
                current_data = processor.get_processed_data()
                packets_processed = len(current_data)
                await asyncio.sleep(0.1)  # 100ms监控间隔
        
        # 启动处理器
        processor_task = asyncio.create_task(processor.start())
        
        # 运行测试
        await asyncio.gather(
            data_sender(),
            data_monitor(),
            return_exceptions=True
        )
        
        # 停止处理器
        await processor.stop()
        processor_task.cancel()
        
        actual_duration = time.time() - start_time
        
        return {
            'duration_seconds': actual_duration,
            'packets_sent': packets_sent,
            'packets_processed': packets_processed,
            'send_rate_pps': packets_sent / actual_duration,
            'process_rate_pps': packets_processed / actual_duration,
            'processing_efficiency': packets_processed / max(packets_sent, 1)
        }
    
    def run_memory_benchmark(self, data_points: int = 100000) -> Dict[str, Any]:
        """内存使用基准测试"""
        print(f"运行内存基准测试 ({data_points} 数据点)...")
        
        import psutil
        import gc
        
        process = psutil.Process()
        
        # 初始内存
        gc.collect()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # 创建处理器
        processor = DataProcessor(self.config)
        
        # 生成大量数据
        test_data = b'\x12\x34\x56\x78' * (data_points // 2)
        
        start_time = time.time()
        
        # 处理数据
        for i in range(10):
            processor._convert_data_format(test_data)
            
            if i % 2 == 0:  # 每隔一次检查内存
                current_memory = process.memory_info().rss / 1024 / 1024
                print(f"    迭代 {i+1}: {current_memory:.2f} MB")
        
        processing_time = time.time() - start_time
        
        # 最终内存
        gc.collect()
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        return {
            'initial_memory_mb': initial_memory,
            'final_memory_mb': final_memory,
            'memory_increase_mb': final_memory - initial_memory,
            'processing_time_seconds': processing_time,
            'data_points_processed': data_points * 10,
            'memory_per_datapoint_kb': (final_memory - initial_memory) * 1024 / (data_points * 10)
        }
    
    def run_cache_benchmark(self, cache_sizes: List[int] = None) -> Dict[str, Any]:
        """缓存性能基准测试"""
        if cache_sizes is None:
            cache_sizes = [100, 500, 1000, 2000, 5000]
        
        print("运行缓存性能基准测试...")
        
        results = {}
        
        for cache_size in cache_sizes:
            print(f"  测试缓存大小: {cache_size}")
            
            # 配置缓存
            self.config.performance.cache_size = cache_size
            self.config.performance.enable_caching = True
            
            processor = DataProcessor(self.config)
            
            # 生成测试数据
            test_data_sets = [b'\x12\x34\x56\x78' * (i * 10) for i in range(1, 101)]
            
            # 第一轮：填充缓存
            start_time = time.time()
            for data in test_data_sets:
                processor._convert_data_format(data)
            first_round_time = time.time() - start_time
            
            # 第二轮：测试缓存命中
            start_time = time.time()
            for data in test_data_sets:
                processor._convert_data_format(data)
            second_round_time = time.time() - start_time
            
            # 计算缓存效果
            cache_hits = processor.cache_hits
            cache_misses = processor.cache_misses
            hit_rate = cache_hits / (cache_hits + cache_misses) if (cache_hits + cache_misses) > 0 else 0
            
            results[cache_size] = {
                'first_round_time_ms': first_round_time * 1000,
                'second_round_time_ms': second_round_time * 1000,
                'speedup_factor': first_round_time / max(second_round_time, 0.001),
                'cache_hit_rate': hit_rate,
                'cache_hits': cache_hits,
                'cache_misses': cache_misses
            }
        
        return results
    
    def print_results(self, results: Dict[str, Any], title: str):
        """打印测试结果"""
        print(f"\n{'='*60}")
        print(f"{title}")
        print(f"{'='*60}")
        
        for key, value in results.items():
            print(f"\n{key}:")
            if isinstance(value, dict):
                for sub_key, sub_value in value.items():
                    if isinstance(sub_value, float):
                        print(f"  {sub_key}: {sub_value:.3f}")
                    else:
                        print(f"  {sub_key}: {sub_value}")
            else:
                print(f"  {value}")
    
    def save_results(self, filename: str = "benchmark_results.json"):
        """保存测试结果到文件"""
        import json
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False)
        
        print(f"\n测试结果已保存到: {filename}")


async def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="USART Trams 性能基准测试工具")
    parser.add_argument("--iterations", type=int, default=1000, help="迭代次数")
    parser.add_argument("--duration", type=int, default=10, help="异步测试持续时间(秒)")
    parser.add_argument("--data-points", type=int, default=100000, help="内存测试数据点数")
    parser.add_argument("--output", type=str, default="benchmark_results.json", help="结果输出文件")
    parser.add_argument("--test", choices=['all', 'conversion', 'buffer', 'async', 'memory', 'cache'], 
                       default='all', help="要运行的测试类型")
    
    args = parser.parse_args()
    
    benchmark = PerformanceBenchmark()
    
    print("USART Trams 性能基准测试")
    print("=" * 60)
    
    if args.test in ['all', 'conversion']:
        results = benchmark.run_data_conversion_benchmark(args.iterations)
        benchmark.results['data_conversion'] = results
        benchmark.print_results(results, "数据转换性能测试结果")
    
    if args.test in ['all', 'buffer']:
        results = benchmark.run_buffer_benchmark()
        benchmark.results['buffer'] = results
        benchmark.print_results(results, "缓冲区性能测试结果")
    
    if args.test in ['all', 'async']:
        results = await benchmark.run_async_benchmark(args.duration)
        benchmark.results['async'] = results
        benchmark.print_results(results, "异步处理性能测试结果")
    
    if args.test in ['all', 'memory']:
        results = benchmark.run_memory_benchmark(args.data_points)
        benchmark.results['memory'] = results
        benchmark.print_results(results, "内存使用测试结果")
    
    if args.test in ['all', 'cache']:
        results = benchmark.run_cache_benchmark()
        benchmark.results['cache'] = results
        benchmark.print_results(results, "缓存性能测试结果")
    
    # 保存结果
    benchmark.save_results(args.output)
    
    print(f"\n{'='*60}")
    print("基准测试完成！")
    print(f"{'='*60}")


if __name__ == "__main__":
    asyncio.run(main())
