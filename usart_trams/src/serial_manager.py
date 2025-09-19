"""
高性能异步串口管理器
优化串口数据接收和传输延迟
"""

import asyncio
import logging
import time
from typing import Callable, Optional, List
import serial
import serial.tools.list_ports
from concurrent.futures import ThreadPoolExecutor

from .config import Config

logger = logging.getLogger(__name__)


class SerialManager:
    """异步串口管理器"""
    
    def __init__(self, config: Config, data_callback: Callable):
        self.config = config
        self.data_callback = data_callback
        self.serial_port: Optional[serial.Serial] = None
        self.running = False
        self.executor = ThreadPoolExecutor(max_workers=2)
        
        # 性能统计
        self.bytes_received = 0
        self.packets_received = 0
        self.last_stats_time = time.time()
        self.receive_rate = 0.0
        
        # 数据缓冲
        self.read_buffer = bytearray()
        self.buffer_lock = asyncio.Lock()
    
    @staticmethod
    def list_available_ports() -> List[str]:
        """列出可用的串口"""
        ports = []
        for port in serial.tools.list_ports.comports():
            ports.append(port.device)
        return ports
    
    async def connect(self) -> bool:
        """连接串口"""
        try:
            # 在线程池中执行串口连接
            loop = asyncio.get_event_loop()
            self.serial_port = await loop.run_in_executor(
                self.executor,
                self._create_serial_connection
            )
            
            if self.serial_port and self.serial_port.is_open:
                logger.info(f"串口连接成功: {self.config.serial.port}")
                return True
            else:
                logger.error("串口连接失败")
                return False
                
        except Exception as e:
            logger.error(f"串口连接异常: {e}")
            return False
    
    def _create_serial_connection(self) -> serial.Serial:
        """创建串口连接（在线程池中执行）"""
        return serial.Serial(
            port=self.config.serial.port,
            baudrate=self.config.serial.baudrate,
            timeout=self.config.serial.timeout,
            bytesize=self.config.serial.bytesize,
            parity=self.config.serial.parity,
            stopbits=self.config.serial.stopbits,
            xonxoff=self.config.serial.xonxoff,
            rtscts=self.config.serial.rtscts,
            dsrdtr=self.config.serial.dsrdtr
        )
    
    async def disconnect(self):
        """断开串口连接"""
        if self.serial_port and self.serial_port.is_open:
            try:
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(
                    self.executor,
                    self.serial_port.close
                )
                logger.info("串口已断开")
            except Exception as e:
                logger.error(f"断开串口时发生错误: {e}")
    
    async def start(self):
        """启动串口数据接收"""
        if not await self.connect():
            return
        
        self.running = True
        logger.info("开始接收串口数据...")
        
        try:
            # 启动数据接收任务
            receive_task = asyncio.create_task(self._receive_data())
            process_task = asyncio.create_task(self._process_buffer())
            stats_task = asyncio.create_task(self._update_statistics())
            
            await asyncio.gather(
                receive_task,
                process_task,
                stats_task,
                return_exceptions=True
            )
            
        except Exception as e:
            logger.error(f"串口数据接收异常: {e}")
        finally:
            await self.disconnect()
    
    async def stop(self):
        """停止串口数据接收"""
        self.running = False
        await self.disconnect()
        self.executor.shutdown(wait=True)
    
    async def _receive_data(self):
        """异步接收串口数据"""
        loop = asyncio.get_event_loop()
        
        while self.running and self.serial_port and self.serial_port.is_open:
            try:
                # 在线程池中读取数据
                data = await loop.run_in_executor(
                    self.executor,
                    self._read_serial_data
                )
                
                if data:
                    async with self.buffer_lock:
                        self.read_buffer.extend(data)
                        self.bytes_received += len(data)
                
                # 最小休眠，最大响应速度
                await asyncio.sleep(0.0001)  # 极高响应速度
                
            except Exception as e:
                logger.error(f"接收数据时发生错误: {e}")
                await asyncio.sleep(0.1)
    
    def _read_serial_data(self) -> bytes:
        """读取串口数据（在线程池中执行）"""
        if self.serial_port and self.serial_port.is_open:
            try:
                # 检查是否有数据可读
                if self.serial_port.in_waiting > 0:
                    # 读取可用数据，最大读取缓冲区大小
                    max_read = min(
                        self.serial_port.in_waiting,
                        self.config.processing.buffer_size
                    )
                    data = self.serial_port.read(max_read)

                    # 调试信息：显示接收到的原始数据
                    if data:
                        logger.debug(f"接收到 {len(data)} 字节数据: {data[:100]}...")  # 只显示前100字节
                        try:
                            # 尝试解码为文本以便调试
                            text_preview = data.decode('ascii', errors='ignore')[:50]
                            logger.debug(f"数据预览: {repr(text_preview)}")
                        except:
                            pass

                    return data
            except Exception as e:
                logger.error(f"读取串口数据失败: {e}")
        return b''
    
    async def _process_buffer(self):
        """处理缓冲区数据"""
        while self.running:
            try:
                async with self.buffer_lock:
                    # 对于ASCII数据，按行处理而不是按固定大小
                    if len(self.read_buffer) > 0:
                        # 检查是否有完整的行
                        buffer_data = bytes(self.read_buffer)

                        # 查找换行符
                        if b'\n' in buffer_data or b'\r' in buffer_data:
                            # 找到最后一个换行符的位置
                            last_newline = max(
                                buffer_data.rfind(b'\n'),
                                buffer_data.rfind(b'\r')
                            )

                            if last_newline >= 0:
                                # 提取到最后一个换行符的数据
                                batch_data = buffer_data[:last_newline + 1]

                                # 从缓冲区中移除已处理的数据
                                del self.read_buffer[:last_newline + 1]

                                # 异步处理数据
                                if self.data_callback and batch_data:
                                    asyncio.create_task(
                                        self._call_data_callback(batch_data)
                                    )

                                self.packets_received += 1

                        # 如果缓冲区太大但没有换行符，强制处理
                        elif len(self.read_buffer) > 1000:
                            batch_data = bytes(self.read_buffer)
                            self.read_buffer.clear()

                            if self.data_callback:
                                asyncio.create_task(
                                    self._call_data_callback(batch_data)
                                )

                            self.packets_received += 1

                # 处理间隔
                await asyncio.sleep(self.config.processing.processing_interval)

            except Exception as e:
                logger.error(f"处理缓冲区数据时发生错误: {e}")
                await asyncio.sleep(0.1)
    
    async def _call_data_callback(self, data: bytes):
        """调用数据回调函数"""
        try:
            if asyncio.iscoroutinefunction(self.data_callback):
                await self.data_callback(data)
            else:
                # 在线程池中执行同步回调
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(
                    self.executor,
                    self.data_callback,
                    data
                )
        except Exception as e:
            logger.error(f"数据回调函数执行失败: {e}")
    
    async def _update_statistics(self):
        """更新性能统计"""
        while self.running:
            try:
                current_time = time.time()
                time_diff = current_time - self.last_stats_time
                
                if time_diff >= 1.0:  # 每秒更新一次统计
                    self.receive_rate = self.bytes_received / time_diff
                    
                    logger.debug(
                        f"串口统计 - 接收速率: {self.receive_rate:.2f} bytes/s, "
                        f"数据包: {self.packets_received}, "
                        f"缓冲区大小: {len(self.read_buffer)}"
                    )
                    
                    # 重置统计
                    self.bytes_received = 0
                    self.last_stats_time = current_time
                
                await asyncio.sleep(1.0)
                
            except Exception as e:
                logger.error(f"更新统计信息时发生错误: {e}")
                await asyncio.sleep(1.0)
    
    async def send_data(self, data: bytes) -> bool:
        """发送数据到串口"""
        if not self.serial_port or not self.serial_port.is_open:
            logger.error("串口未连接，无法发送数据")
            return False
        
        try:
            loop = asyncio.get_event_loop()
            bytes_written = await loop.run_in_executor(
                self.executor,
                self.serial_port.write,
                data
            )
            
            # 确保数据发送完成
            await loop.run_in_executor(
                self.executor,
                self.serial_port.flush
            )
            
            logger.debug(f"发送数据成功: {bytes_written} bytes")
            return True
            
        except Exception as e:
            logger.error(f"发送数据失败: {e}")
            return False
    
    def get_statistics(self) -> dict:
        """获取性能统计信息"""
        return {
            'receive_rate': self.receive_rate,
            'packets_received': self.packets_received,
            'buffer_size': len(self.read_buffer),
            'is_connected': self.serial_port and self.serial_port.is_open,
            'port': self.config.serial.port,
            'baudrate': self.config.serial.baudrate
        }
