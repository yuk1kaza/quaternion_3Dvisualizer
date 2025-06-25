#!/usr/bin/env python3
"""
高性能串口数据处理系统
优化数据转换延迟的主程序
"""

import asyncio
import logging
import sys
from pathlib import Path

from src.serial_manager import SerialManager
from src.data_processor import DataProcessor
from src.visualizer import DataVisualizer
from src.config import Config

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('usart_trams.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)


class USARTTramsApp:
    """主应用程序类"""
    
    def __init__(self):
        self.config = Config()
        self.serial_manager = None
        self.data_processor = None
        self.visualizer = None
        self.running = False
        
    async def initialize(self):
        """初始化所有组件"""
        try:
            logger.info("初始化USART Trams应用程序...")
            
            # 初始化数据处理器
            self.data_processor = DataProcessor(self.config)
            
            # 初始化串口管理器
            self.serial_manager = SerialManager(
                self.config, 
                self.data_processor.process_data
            )
            
            # 初始化可视化器
            self.visualizer = DataVisualizer(
                self.config,
                self.data_processor.get_processed_data
            )
            
            logger.info("所有组件初始化完成")
            return True
            
        except Exception as e:
            logger.error(f"初始化失败: {e}")
            return False
    
    async def start(self):
        """启动应用程序"""
        if not await self.initialize():
            return False
            
        try:
            logger.info("启动应用程序...")
            self.running = True
            
            # 启动串口管理器
            serial_task = asyncio.create_task(
                self.serial_manager.start()
            )
            
            # 启动数据处理器
            processor_task = asyncio.create_task(
                self.data_processor.start()
            )
            
            # 启动可视化器
            visualizer_task = asyncio.create_task(
                self.visualizer.start()
            )
            
            # 等待所有任务完成
            await asyncio.gather(
                serial_task,
                processor_task,
                visualizer_task,
                return_exceptions=True
            )
            
        except KeyboardInterrupt:
            logger.info("接收到中断信号，正在关闭...")
        except Exception as e:
            logger.error(f"运行时错误: {e}")
        finally:
            await self.stop()
    
    async def stop(self):
        """停止应用程序"""
        logger.info("正在停止应用程序...")
        self.running = False
        
        if self.serial_manager:
            await self.serial_manager.stop()
        
        if self.data_processor:
            await self.data_processor.stop()
        
        if self.visualizer:
            await self.visualizer.stop()
        
        logger.info("应用程序已停止")


async def main():
    """主函数"""
    app = USARTTramsApp()
    await app.start()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("程序被用户中断")
    except Exception as e:
        logger.error(f"程序异常退出: {e}")
        sys.exit(1)
