"""
四元数数据处理器
专门处理四元数数据的解析、验证和转换
"""

import struct
import math
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from collections import deque
import logging

logger = logging.getLogger(__name__)


class Quaternion:
    """四元数类"""
    
    def __init__(self, w: float = 1.0, x: float = 0.0, y: float = 0.0, z: float = 0.0):
        self.w = w  # 标量部分
        self.x = x  # 向量部分
        self.y = y
        self.z = z
    
    def __str__(self):
        return f"Quaternion(w={self.w:.4f}, x={self.x:.4f}, y={self.y:.4f}, z={self.z:.4f})"
    
    def __repr__(self):
        return self.__str__()
    
    def normalize(self):
        """归一化四元数"""
        norm = math.sqrt(self.w**2 + self.x**2 + self.y**2 + self.z**2)
        if norm > 0:
            self.w /= norm
            self.x /= norm
            self.y /= norm
            self.z /= norm
        return self
    
    def conjugate(self):
        """四元数共轭"""
        return Quaternion(self.w, -self.x, -self.y, -self.z)
    
    def to_rotation_matrix(self) -> np.ndarray:
        """转换为旋转矩阵"""
        w, x, y, z = self.w, self.x, self.y, self.z
        
        # 归一化
        norm = math.sqrt(w**2 + x**2 + y**2 + z**2)
        if norm > 0:
            w, x, y, z = w/norm, x/norm, y/norm, z/norm
        
        # 计算旋转矩阵
        matrix = np.array([
            [1 - 2*(y**2 + z**2), 2*(x*y - w*z), 2*(x*z + w*y)],
            [2*(x*y + w*z), 1 - 2*(x**2 + z**2), 2*(y*z - w*x)],
            [2*(x*z - w*y), 2*(y*z + w*x), 1 - 2*(x**2 + y**2)]
        ])
        
        return matrix
    
    def to_euler_angles(self) -> Tuple[float, float, float]:
        """转换为欧拉角 (roll, pitch, yaw) 单位：弧度"""
        w, x, y, z = self.w, self.x, self.y, self.z
        
        # 归一化
        norm = math.sqrt(w**2 + x**2 + y**2 + z**2)
        if norm > 0:
            w, x, y, z = w/norm, x/norm, y/norm, z/norm
        
        # Roll (x-axis rotation)
        sinr_cosp = 2 * (w * x + y * z)
        cosr_cosp = 1 - 2 * (x * x + y * y)
        roll = math.atan2(sinr_cosp, cosr_cosp)
        
        # Pitch (y-axis rotation)
        sinp = 2 * (w * y - z * x)
        if abs(sinp) >= 1:
            pitch = math.copysign(math.pi / 2, sinp)  # use 90 degrees if out of range
        else:
            pitch = math.asin(sinp)
        
        # Yaw (z-axis rotation)
        siny_cosp = 2 * (w * z + x * y)
        cosy_cosp = 1 - 2 * (y * y + z * z)
        yaw = math.atan2(siny_cosp, cosy_cosp)
        
        return roll, pitch, yaw
    
    def to_axis_angle(self) -> Tuple[np.ndarray, float]:
        """转换为轴角表示"""
        # 归一化
        norm = math.sqrt(self.w**2 + self.x**2 + self.y**2 + self.z**2)
        if norm > 0:
            w, x, y, z = self.w/norm, self.x/norm, self.y/norm, self.z/norm
        else:
            return np.array([0, 0, 1]), 0
        
        # 计算角度
        angle = 2 * math.acos(abs(w))
        
        # 计算轴
        sin_half_angle = math.sqrt(1 - w**2)
        if sin_half_angle < 1e-6:
            # 接近单位四元数，任意轴
            axis = np.array([1, 0, 0])
        else:
            axis = np.array([x, y, z]) / sin_half_angle
        
        return axis, angle
    
    def to_dict(self) -> Dict[str, float]:
        """转换为字典"""
        return {
            'w': self.w,
            'x': self.x,
            'y': self.y,
            'z': self.z
        }


class QuaternionProcessor:
    """四元数数据处理器"""
    
    def __init__(self, config):
        self.config = config
        self.quaternion_history = deque(maxlen=1000)  # 保存历史四元数
        self.euler_history = deque(maxlen=1000)       # 保存历史欧拉角
        
        # 数据解析格式
        self.data_formats = {
            'float32': self._parse_float32_quaternion,
            'float64': self._parse_float64_quaternion,
            'ascii': self._parse_ascii_quaternion,
            'binary': self._parse_binary_quaternion,  # 添加二进制格式支持
            'custom': self._parse_custom_quaternion
        }
        
        # 当前使用的解析格式
        self.current_format = 'float32'
        
        # 数据验证
        self.validation_enabled = True
        self.max_quaternion_norm_deviation = 0.1  # 允许的归一化偏差
        
        # 统计信息
        self.total_packets = 0
        self.valid_packets = 0
        self.invalid_packets = 0

        # ASCII数据缓冲区 - 用于处理不完整的行
        self.ascii_buffer = b''

        # 互补滤波器
        self.enable_filtering = config.processing.enable_filtering
        self.complementary_filter = None
        if self.enable_filtering:
            from .complementary_filter import AdaptiveComplementaryFilter
            self.complementary_filter = AdaptiveComplementaryFilter(
                alpha=0.65,  # 激进降低alpha以强力减少零漂
                gyro_weight=0.55  # 激进降低陀螺仪权重，最大化零漂抑制
            )
            logger.info("增强零漂抑制滤波器已启用")
    
    def process_raw_data(self, raw_data: bytes) -> List[Dict[str, Any]]:
        """处理原始串口数据"""
        try:
            quaternions = self.data_formats[self.current_format](raw_data)
            processed_data = []
            
            for quat in quaternions:
                if self.validation_enabled and not self._validate_quaternion(quat):
                    self.invalid_packets += 1
                    continue
                
                # 归一化四元数
                quat.normalize()

                # 应用互补滤波
                if self.complementary_filter:
                    filtered_quat = self.complementary_filter.filter_quaternion(quat)
                else:
                    filtered_quat = quat

                # 计算欧拉角
                roll, pitch, yaw = filtered_quat.to_euler_angles()

                # 创建数据点
                data_point = {
                    'timestamp': self._get_timestamp(),
                    'quaternion': filtered_quat.to_dict(),
                    'quaternion_raw': quat.to_dict(),  # 保留原始数据
                    'euler_angles': {
                        'roll': roll,
                        'pitch': pitch,
                        'yaw': yaw
                    },
                    'euler_degrees': {
                        'roll': math.degrees(roll),
                        'pitch': math.degrees(pitch),
                        'yaw': math.degrees(yaw)
                    },
                    'rotation_matrix': filtered_quat.to_rotation_matrix().tolist(),
                    'filtered': self.enable_filtering
                }
                
                processed_data.append(data_point)
                
                # 保存到历史记录（使用滤波后的数据）
                self.quaternion_history.append(filtered_quat)
                self.euler_history.append((roll, pitch, yaw))
                
                self.valid_packets += 1
            
            self.total_packets += len(quaternions)
            return processed_data
            
        except Exception as e:
            logger.error(f"处理四元数数据时发生错误: {e}")
            return []
    
    def _parse_float32_quaternion(self, data: bytes) -> List[Quaternion]:
        """解析32位浮点数四元数 (w, x, y, z)"""
        quaternions = []
        
        # 每个四元数需要16字节 (4个float32)
        if len(data) < 16:
            return quaternions
        
        for i in range(0, len(data) - 15, 16):
            try:
                # 解包4个float32值 (小端序)
                w, x, y, z = struct.unpack('<ffff', data[i:i+16])
                quaternions.append(Quaternion(w, x, y, z))
            except struct.error:
                continue
        
        return quaternions
    
    def _parse_float64_quaternion(self, data: bytes) -> List[Quaternion]:
        """解析64位浮点数四元数 (w, x, y, z)"""
        quaternions = []
        
        # 每个四元数需要32字节 (4个float64)
        if len(data) < 32:
            return quaternions
        
        for i in range(0, len(data) - 31, 32):
            try:
                # 解包4个float64值 (小端序)
                w, x, y, z = struct.unpack('<dddd', data[i:i+32])
                quaternions.append(Quaternion(w, x, y, z))
            except struct.error:
                continue
        
        return quaternions
    
    def _parse_ascii_quaternion(self, data: bytes) -> List[Quaternion]:
        """解析ASCII格式四元数 "w,x,y,z\n" """
        quaternions = []

        try:
            # 将新数据添加到缓冲区
            self.ascii_buffer += data

            # 解码缓冲区数据
            text = self.ascii_buffer.decode('ascii', errors='ignore')
            logger.debug(f"缓冲区数据: {repr(text[:100])}")  # 调试信息

            # 分割行，保留最后一行（可能不完整）
            lines = text.replace('\r\n', '\n').replace('\r', '\n').split('\n')

            # 处理完整的行（除了最后一行）
            complete_lines = lines[:-1]
            incomplete_line = lines[-1] if lines else ''

            for line_num, line in enumerate(complete_lines):
                line = line.strip()
                if not line:
                    continue

                logger.debug(f"处理第{line_num+1}行: {repr(line)}")

                # 解析逗号分隔的值
                parts = line.split(',')
                if len(parts) >= 4:
                    try:
                        # 尝试解析四个浮点数
                        w = float(parts[0].strip())
                        x = float(parts[1].strip())
                        y = float(parts[2].strip())
                        z = float(parts[3].strip())

                        quat = Quaternion(w, x, y, z)
                        quaternions.append(quat)
                        logger.debug(f"成功解析四元数: w={w:.4f}, x={x:.4f}, y={y:.4f}, z={z:.4f}")

                    except (ValueError, IndexError) as e:
                        logger.warning(f"解析行失败 '{line}': {e}")
                        continue
                else:
                    logger.warning(f"数据格式错误，期望4个值，得到{len(parts)}个: {line}")

            # 保留不完整的行到缓冲区
            self.ascii_buffer = incomplete_line.encode('ascii', errors='ignore')

            # 限制缓冲区大小，防止内存泄漏
            if len(self.ascii_buffer) > 1000:  # 最大1KB缓冲
                self.ascii_buffer = self.ascii_buffer[-500:]  # 保留后500字节

        except Exception as e:
            logger.error(f"解析ASCII四元数数据失败: {e}")
            # 清空缓冲区以防止错误累积
            self.ascii_buffer = b''

        logger.debug(f"总共解析出 {len(quaternions)} 个四元数")
        return quaternions

    def _parse_binary_quaternion(self, data: bytes) -> List[Quaternion]:
        """解析二进制格式四元数数据"""
        quaternions = []

        try:
            # 二进制数据通常是连续的float值
            # 尝试不同的格式：小端序和大端序

            # 每个四元数需要16字节（4个float32）
            quaternion_size = 16

            if len(data) < quaternion_size:
                logger.debug(f"二进制数据不足，需要{quaternion_size}字节，实际{len(data)}字节")
                return quaternions

            # 处理所有完整的四元数
            for i in range(0, len(data) - quaternion_size + 1, quaternion_size):
                chunk = data[i:i + quaternion_size]

                # 尝试小端序解析
                try:
                    values = struct.unpack('<ffff', chunk)  # 小端序
                    w, x, y, z = values

                    # 验证四元数合理性（模长应该接近1）
                    magnitude = math.sqrt(w*w + x*x + y*y + z*z)

                    if 0.1 <= magnitude <= 2.0:  # 合理的四元数范围
                        quat = Quaternion(w, x, y, z)
                        quaternions.append(quat)
                        logger.debug(f"解析二进制四元数: {quat}, 模长: {magnitude:.4f}")
                        continue

                except struct.error:
                    pass

                # 如果小端序失败，尝试大端序
                try:
                    values = struct.unpack('>ffff', chunk)  # 大端序
                    w, x, y, z = values

                    # 验证四元数合理性
                    magnitude = math.sqrt(w*w + x*x + y*y + z*z)

                    if 0.1 <= magnitude <= 2.0:
                        quat = Quaternion(w, x, y, z)
                        quaternions.append(quat)
                        logger.debug(f"解析二进制四元数(大端): {quat}, 模长: {magnitude:.4f}")
                        continue

                except struct.error:
                    pass

                # 如果都失败，尝试其他可能的格式
                # 可能是x,y,z,w的顺序
                try:
                    values = struct.unpack('<ffff', chunk)
                    x, y, z, w = values  # 不同的顺序

                    magnitude = math.sqrt(w*w + x*x + y*y + z*z)

                    if 0.1 <= magnitude <= 2.0:
                        quat = Quaternion(w, x, y, z)
                        quaternions.append(quat)
                        logger.debug(f"解析二进制四元数(xyzw): {quat}, 模长: {magnitude:.4f}")
                        continue

                except struct.error:
                    pass

                logger.debug(f"无法解析二进制数据块: {chunk.hex()}")

        except Exception as e:
            logger.error(f"解析二进制四元数数据失败: {e}")

        logger.debug(f"二进制格式解析出 {len(quaternions)} 个四元数")
        return quaternions

    def _parse_custom_quaternion(self, data: bytes) -> List[Quaternion]:
        """自定义格式解析 - 可根据具体协议修改"""
        # 这里可以根据您的具体数据格式进行定制
        # 示例：假设数据格式为 [header(2bytes)] + [w,x,y,z(16bytes)] + [checksum(2bytes)]
        quaternions = []
        
        packet_size = 20  # 2 + 16 + 2
        if len(data) < packet_size:
            return quaternions
        
        for i in range(0, len(data) - packet_size + 1, packet_size):
            try:
                # 检查包头 (示例: 0xAA55)
                header = struct.unpack('<H', data[i:i+2])[0]
                if header != 0xAA55:
                    continue
                
                # 解析四元数
                w, x, y, z = struct.unpack('<ffff', data[i+2:i+18])
                
                # 检查校验和 (简单示例)
                checksum = struct.unpack('<H', data[i+18:i+20])[0]
                # 这里可以添加校验和验证逻辑
                
                quaternions.append(Quaternion(w, x, y, z))
                
            except struct.error:
                continue
        
        return quaternions
    
    def _validate_quaternion(self, quat: Quaternion) -> bool:
        """验证四元数的有效性"""
        # 检查是否为NaN或无穷大
        if any(math.isnan(val) or math.isinf(val) for val in [quat.w, quat.x, quat.y, quat.z]):
            return False
        
        # 检查模长是否接近1 (允许一定偏差)
        norm = math.sqrt(quat.w**2 + quat.x**2 + quat.y**2 + quat.z**2)
        if abs(norm - 1.0) > self.max_quaternion_norm_deviation:
            logger.debug(f"四元数模长偏差过大: {norm}")
            return False
        
        return True
    
    def _get_timestamp(self) -> float:
        """获取时间戳"""
        import time
        return time.time()
    
    def get_latest_quaternion(self) -> Optional[Quaternion]:
        """获取最新的四元数"""
        return self.quaternion_history[-1] if self.quaternion_history else None
    
    def get_latest_euler_angles(self) -> Optional[Tuple[float, float, float]]:
        """获取最新的欧拉角"""
        return self.euler_history[-1] if self.euler_history else None
    
    def get_quaternion_history(self, count: int = 100) -> List[Quaternion]:
        """获取四元数历史记录"""
        return list(self.quaternion_history)[-count:]
    
    def get_euler_history(self, count: int = 100) -> List[Tuple[float, float, float]]:
        """获取欧拉角历史记录"""
        return list(self.euler_history)[-count:]
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取处理统计信息"""
        success_rate = self.valid_packets / max(self.total_packets, 1) * 100
        
        return {
            'total_packets': self.total_packets,
            'valid_packets': self.valid_packets,
            'invalid_packets': self.invalid_packets,
            'success_rate': success_rate,
            'current_format': self.current_format,
            'history_size': len(self.quaternion_history)
        }
    
    def set_data_format(self, format_name: str):
        """设置数据解析格式"""
        if format_name in self.data_formats:
            self.current_format = format_name
            logger.info(f"数据格式已设置为: {format_name}")
        else:
            logger.error(f"不支持的数据格式: {format_name}")
    
    def clear_history(self):
        """清空历史记录"""
        self.quaternion_history.clear()
        self.euler_history.clear()
        logger.info("四元数历史记录已清空")
