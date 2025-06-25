"""
配置管理模块
"""

import json
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Dict, Any


@dataclass
class SerialConfig:
    """串口配置"""
    port: str = "COM3"  # Windows默认，Linux使用 /dev/ttyUSB0
    baudrate: int = 115200
    timeout: float = 0.1
    bytesize: int = 8
    parity: str = 'N'
    stopbits: int = 1
    xonxoff: bool = False
    rtscts: bool = False
    dsrdtr: bool = False


@dataclass
class ProcessingConfig:
    """数据处理配置"""
    buffer_size: int = 8192  # 缓冲区大小
    batch_size: int = 100    # 批处理大小
    max_queue_size: int = 1000  # 最大队列大小
    processing_interval: float = 0.01  # 处理间隔(秒)
    data_format: str = "hex"  # 数据格式: hex, ascii, binary
    enable_filtering: bool = True  # 启用数据过滤
    filter_threshold: float = 0.1  # 过滤阈值


@dataclass
class VisualizationConfig:
    """可视化配置"""
    window_width: int = 1200
    window_height: int = 800
    update_interval: float = 0.05  # 更新间隔(秒)
    max_points: int = 1000  # 最大显示点数
    line_width: float = 2.0
    background_color: str = "black"
    line_color: str = "green"
    enable_realtime: bool = True
    show_statistics: bool = True


@dataclass
class PerformanceConfig:
    """性能优化配置"""
    use_multiprocessing: bool = True
    worker_processes: int = 2
    use_numpy_acceleration: bool = True
    enable_caching: bool = True
    cache_size: int = 1000
    memory_limit_mb: int = 512


class Config:
    """主配置类"""
    
    def __init__(self, config_file: str = "config.json"):
        self.config_file = Path(config_file)
        
        # 默认配置
        self.serial = SerialConfig()
        self.processing = ProcessingConfig()
        self.visualization = VisualizationConfig()
        self.performance = PerformanceConfig()
        
        # 加载配置文件
        self.load_config()
    
    def load_config(self):
        """从文件加载配置"""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
                
                # 更新配置
                if 'serial' in config_data:
                    self._update_dataclass(self.serial, config_data['serial'])
                
                if 'processing' in config_data:
                    self._update_dataclass(self.processing, config_data['processing'])
                
                if 'visualization' in config_data:
                    self._update_dataclass(self.visualization, config_data['visualization'])
                
                if 'performance' in config_data:
                    self._update_dataclass(self.performance, config_data['performance'])
                    
            except Exception as e:
                print(f"加载配置文件失败: {e}")
    
    def save_config(self):
        """保存配置到文件"""
        try:
            config_data = {
                'serial': asdict(self.serial),
                'processing': asdict(self.processing),
                'visualization': asdict(self.visualization),
                'performance': asdict(self.performance)
            }
            
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            print(f"保存配置文件失败: {e}")
    
    def _update_dataclass(self, obj, data: Dict[str, Any]):
        """更新数据类对象"""
        for key, value in data.items():
            if hasattr(obj, key):
                setattr(obj, key, value)
    
    def get_optimal_settings(self) -> Dict[str, Any]:
        """获取优化设置建议"""
        import psutil
        
        # 获取系统信息
        cpu_count = psutil.cpu_count()
        memory_gb = psutil.virtual_memory().total / (1024**3)
        
        suggestions = {}
        
        # CPU优化建议
        if cpu_count >= 4:
            suggestions['worker_processes'] = min(cpu_count - 1, 4)
            suggestions['use_multiprocessing'] = True
        else:
            suggestions['worker_processes'] = 1
            suggestions['use_multiprocessing'] = False
        
        # 内存优化建议
        if memory_gb >= 8:
            suggestions['buffer_size'] = 16384
            suggestions['max_queue_size'] = 2000
            suggestions['cache_size'] = 2000
        elif memory_gb >= 4:
            suggestions['buffer_size'] = 8192
            suggestions['max_queue_size'] = 1000
            suggestions['cache_size'] = 1000
        else:
            suggestions['buffer_size'] = 4096
            suggestions['max_queue_size'] = 500
            suggestions['cache_size'] = 500
        
        return suggestions
    
    def apply_optimal_settings(self):
        """应用优化设置"""
        suggestions = self.get_optimal_settings()
        
        for key, value in suggestions.items():
            if hasattr(self.processing, key):
                setattr(self.processing, key, value)
            elif hasattr(self.performance, key):
                setattr(self.performance, key, value)
