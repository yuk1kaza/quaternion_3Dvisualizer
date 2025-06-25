"""
高性能数据处理器
优化数据转换和处理延迟
"""

import asyncio
import logging
import time
import numpy as np
from typing import List, Dict, Any, Optional, Callable
from collections import deque
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
import struct

from .config import Config

logger = logging.getLogger(__name__)


class DataProcessor:
    """高性能数据处理器"""
    
    def __init__(self, config: Config):
        self.config = config
        self.running = False
        
        # 数据队列
        self.raw_data_queue = asyncio.Queue(
            maxsize=self.config.processing.max_queue_size
        )
        self.processed_data_queue = asyncio.Queue(
            maxsize=self.config.processing.max_queue_size
        )
        
        # 数据存储
        self.processed_data = deque(
            maxlen=self.config.visualization.max_points
        )
        
        # 线程池和进程池
        self.thread_executor = ThreadPoolExecutor(max_workers=4)
        if self.config.performance.use_multiprocessing:
            self.process_executor = ProcessPoolExecutor(
                max_workers=self.config.performance.worker_processes
            )
        else:
            self.process_executor = None
        
        # 性能统计
        self.processed_packets = 0
        self.processing_time_total = 0.0
        self.last_stats_time = time.time()
        
        # 数据缓存
        if self.config.performance.enable_caching:
            self.data_cache = {}
            self.cache_hits = 0
            self.cache_misses = 0
        
        # 数据过滤器
        self.data_filter = DataFilter(config) if config.processing.enable_filtering else None
    
    async def process_data(self, raw_data: bytes):
        """处理原始数据（异步接口）"""
        try:
            await self.raw_data_queue.put(raw_data)
        except asyncio.QueueFull:
            logger.warning("原始数据队列已满，丢弃数据")
    
    async def start(self):
        """启动数据处理"""
        self.running = True
        logger.info("启动数据处理器...")
        
        try:
            # 启动处理任务
            process_task = asyncio.create_task(self._process_raw_data())
            convert_task = asyncio.create_task(self._convert_processed_data())
            stats_task = asyncio.create_task(self._update_statistics())
            
            await asyncio.gather(
                process_task,
                convert_task,
                stats_task,
                return_exceptions=True
            )
            
        except Exception as e:
            logger.error(f"数据处理异常: {e}")
    
    async def stop(self):
        """停止数据处理"""
        self.running = False
        
        # 关闭执行器
        self.thread_executor.shutdown(wait=True)
        if self.process_executor:
            self.process_executor.shutdown(wait=True)
    
    async def _process_raw_data(self):
        """处理原始数据"""
        while self.running:
            try:
                # 获取原始数据
                raw_data = await asyncio.wait_for(
                    self.raw_data_queue.get(),
                    timeout=1.0
                )
                
                start_time = time.time()
                
                # 选择处理方式
                if self.config.performance.use_multiprocessing and self.process_executor:
                    # 使用进程池处理大数据
                    if len(raw_data) > 1024:
                        processed = await self._process_with_multiprocessing(raw_data)
                    else:
                        processed = await self._process_with_threading(raw_data)
                else:
                    # 使用线程池处理
                    processed = await self._process_with_threading(raw_data)
                
                # 记录处理时间
                processing_time = time.time() - start_time
                self.processing_time_total += processing_time
                self.processed_packets += 1
                
                # 将处理结果放入队列
                if processed is not None:
                    try:
                        await self.processed_data_queue.put(processed)
                    except asyncio.QueueFull:
                        logger.warning("处理数据队列已满，丢弃数据")
                
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"处理原始数据时发生错误: {e}")
                await asyncio.sleep(0.1)
    
    async def _process_with_threading(self, raw_data: bytes):
        """使用线程池处理数据"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self.thread_executor,
            self._convert_data_format,
            raw_data
        )
    
    async def _process_with_multiprocessing(self, raw_data: bytes):
        """使用进程池处理数据"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self.process_executor,
            process_data_chunk,
            raw_data,
            self.config.processing.data_format
        )
    
    def _convert_data_format(self, raw_data: bytes) -> Optional[List[float]]:
        """转换数据格式"""
        try:
            # 检查缓存
            if self.config.performance.enable_caching:
                cache_key = hash(raw_data)
                if cache_key in self.data_cache:
                    self.cache_hits += 1
                    return self.data_cache[cache_key]
                self.cache_misses += 1
            
            # 根据配置的数据格式进行转换
            if self.config.processing.data_format == "hex":
                converted = self._convert_hex_data(raw_data)
            elif self.config.processing.data_format == "ascii":
                converted = self._convert_ascii_data(raw_data)
            elif self.config.processing.data_format == "binary":
                converted = self._convert_binary_data(raw_data)
            elif self.config.processing.data_format == "quaternion":
                # 四元数数据直接传递给四元数处理器
                return None  # 由四元数处理器处理
            else:
                logger.warning(f"未知的数据格式: {self.config.processing.data_format}")
                return None
            
            # 应用数据过滤
            if self.data_filter and converted:
                converted = self.data_filter.filter_data(converted)
            
            # 缓存结果
            if self.config.performance.enable_caching and converted:
                if len(self.data_cache) < self.config.performance.cache_size:
                    self.data_cache[cache_key] = converted
            
            return converted
            
        except Exception as e:
            logger.error(f"数据格式转换失败: {e}")
            return None
    
    def _convert_hex_data(self, raw_data: bytes) -> List[float]:
        """转换十六进制数据"""
        try:
            # 将字节数据转换为十六进制字符串
            hex_str = raw_data.hex()
            
            # 按照2字节为一组进行解析
            values = []
            for i in range(0, len(hex_str), 4):  # 每4个字符代表2字节
                if i + 4 <= len(hex_str):
                    hex_value = hex_str[i:i+4]
                    # 转换为16位有符号整数
                    int_value = int(hex_value, 16)
                    if int_value > 32767:  # 处理负数
                        int_value -= 65536
                    values.append(float(int_value))
            
            return values
            
        except Exception as e:
            logger.error(f"十六进制数据转换失败: {e}")
            return []
    
    def _convert_ascii_data(self, raw_data: bytes) -> List[float]:
        """转换ASCII数据"""
        try:
            # 解码为字符串
            text = raw_data.decode('ascii', errors='ignore')
            
            # 提取数字
            import re
            numbers = re.findall(r'-?\d+\.?\d*', text)
            
            return [float(num) for num in numbers if num]
            
        except Exception as e:
            logger.error(f"ASCII数据转换失败: {e}")
            return []
    
    def _convert_binary_data(self, raw_data: bytes) -> List[float]:
        """转换二进制数据"""
        try:
            values = []
            
            # 假设数据是32位浮点数
            for i in range(0, len(raw_data), 4):
                if i + 4 <= len(raw_data):
                    # 解包为浮点数（小端序）
                    value = struct.unpack('<f', raw_data[i:i+4])[0]
                    values.append(value)
            
            return values
            
        except Exception as e:
            logger.error(f"二进制数据转换失败: {e}")
            return []
    
    async def _convert_processed_data(self):
        """转换处理后的数据"""
        while self.running:
            try:
                # 获取处理后的数据
                processed_data = await asyncio.wait_for(
                    self.processed_data_queue.get(),
                    timeout=1.0
                )
                
                if processed_data:
                    # 添加时间戳
                    timestamp = time.time()
                    
                    # 存储数据点
                    for value in processed_data:
                        data_point = {
                            'timestamp': timestamp,
                            'value': value,
                            'index': len(self.processed_data)
                        }
                        self.processed_data.append(data_point)
                
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"转换处理数据时发生错误: {e}")
                await asyncio.sleep(0.1)
    
    async def _update_statistics(self):
        """更新性能统计"""
        while self.running:
            try:
                current_time = time.time()
                time_diff = current_time - self.last_stats_time
                
                if time_diff >= 5.0:  # 每5秒更新一次统计
                    avg_processing_time = (
                        self.processing_time_total / max(self.processed_packets, 1)
                    )
                    
                    cache_hit_rate = 0.0
                    if self.config.performance.enable_caching:
                        total_requests = self.cache_hits + self.cache_misses
                        if total_requests > 0:
                            cache_hit_rate = self.cache_hits / total_requests
                    
                    logger.info(
                        f"数据处理统计 - "
                        f"处理包数: {self.processed_packets}, "
                        f"平均处理时间: {avg_processing_time*1000:.2f}ms, "
                        f"缓存命中率: {cache_hit_rate*100:.1f}%, "
                        f"队列大小: {self.raw_data_queue.qsize()}/{self.processed_data_queue.qsize()}"
                    )
                    
                    # 重置统计
                    self.processed_packets = 0
                    self.processing_time_total = 0.0
                    self.last_stats_time = current_time
                
                await asyncio.sleep(5.0)
                
            except Exception as e:
                logger.error(f"更新统计信息时发生错误: {e}")
                await asyncio.sleep(5.0)
    
    def get_processed_data(self) -> List[Dict[str, Any]]:
        """获取处理后的数据"""
        return list(self.processed_data)
    
    def get_latest_data(self, count: int = 100) -> List[Dict[str, Any]]:
        """获取最新的数据"""
        return list(self.processed_data)[-count:]
    
    def clear_data(self):
        """清空数据"""
        self.processed_data.clear()


class DataFilter:
    """数据过滤器"""
    
    def __init__(self, config: Config):
        self.config = config
        self.threshold = config.processing.filter_threshold
        self.previous_value = None
    
    def filter_data(self, data: List[float]) -> List[float]:
        """过滤数据"""
        if not data:
            return data
        
        filtered_data = []
        
        for value in data:
            # 简单的阈值过滤
            if self.previous_value is not None:
                diff = abs(value - self.previous_value)
                if diff > self.threshold:
                    filtered_data.append(value)
                    self.previous_value = value
            else:
                filtered_data.append(value)
                self.previous_value = value
        
        return filtered_data


def process_data_chunk(raw_data: bytes, data_format: str) -> List[float]:
    """在进程池中处理数据块"""
    try:
        if data_format == "hex":
            hex_str = raw_data.hex()
            values = []
            for i in range(0, len(hex_str), 4):
                if i + 4 <= len(hex_str):
                    hex_value = hex_str[i:i+4]
                    int_value = int(hex_value, 16)
                    if int_value > 32767:
                        int_value -= 65536
                    values.append(float(int_value))
            return values
        
        elif data_format == "binary":
            values = []
            for i in range(0, len(raw_data), 4):
                if i + 4 <= len(raw_data):
                    value = struct.unpack('<f', raw_data[i:i+4])[0]
                    values.append(value)
            return values
        
        else:
            return []
            
    except Exception:
        return []
