"""
互补滤波器模块
实现四元数数据的互补滤波算法，提高数据精度和稳定性
"""

import math
import numpy as np
import time
import logging
from typing import Optional, Tuple, List
from collections import deque

from .quaternion_processor import Quaternion

logger = logging.getLogger(__name__)


class ComplementaryFilter:
    """互补滤波器 - 专为四元数数据设计，增强零漂抑制"""

    def __init__(self, alpha: float = 0.70, gyro_weight: float = 0.60):
        """
        初始化互补滤波器 - 激进的零漂抑制配置

        Args:
            alpha: 高通滤波系数 (0.6-0.8)，大幅降低以减少零漂
            gyro_weight: 陀螺仪权重 (0.5-0.7)，大幅降低以增强零漂抑制
        """
        self.alpha = alpha
        self.gyro_weight = gyro_weight
        self.accel_weight = 1.0 - gyro_weight

        # 滤波状态
        self.filtered_quaternion = None
        self.last_time = None
        self.initialized = False

        # 历史数据用于平滑和零漂检测
        self.history_size = 10  # 增加历史窗口
        self.quaternion_history = deque(maxlen=self.history_size)

        # 零漂抑制参数 - 激进版
        self.drift_detection_window = 20  # 缩短检测窗口，更快响应
        self.drift_history = deque(maxlen=self.drift_detection_window)
        self.drift_threshold = 0.0001  # 极敏感的零漂检测阈值
        self.drift_correction_strength = 0.5  # 强力零漂校正

        # Roll轴特殊处理（分析显示Roll轴漂移最严重）
        self.roll_drift_threshold = 0.1  # Roll轴漂移阈值（度）
        self.roll_correction_strength = 0.8  # Roll轴强力校正

        # Yaw轴特殊处理
        self.yaw_drift_threshold = 0.3  # 降低Yaw轴漂移阈值
        self.yaw_correction_strength = 0.6  # 增强Yaw轴校正强度

        # 基准四元数（用于零漂校正）
        self.reference_quaternion = None
        self.reference_update_interval = 50  # 每50帧更新一次基准（更频繁）
        self.reference_counter = 0

        # 定期重置机制
        self.reset_interval = 1000  # 每1000帧强制重置基准
        self.reset_counter = 0

        # 统计信息
        self.filter_count = 0
        self.total_drift_correction = 0.0
        self.drift_corrections_applied = 0

        logger.info(f"增强零漂抑制滤波器初始化: alpha={alpha}, gyro_weight={gyro_weight}")
    
    def reset(self):
        """重置滤波器状态"""
        self.filtered_quaternion = None
        self.last_time = None
        self.initialized = False
        self.quaternion_history.clear()
        self.drift_history.clear()
        self.reference_quaternion = None
        self.reference_counter = 0
        self.filter_count = 0
        self.total_drift_correction = 0.0
        self.drift_corrections_applied = 0
        logger.info("增强零漂抑制滤波器已重置")
    
    def filter_quaternion(self, raw_quaternion: Quaternion, 
                         gyro_data: Optional[Tuple[float, float, float]] = None,
                         accel_data: Optional[Tuple[float, float, float]] = None,
                         dt: Optional[float] = None) -> Quaternion:
        """
        对四元数进行互补滤波
        
        Args:
            raw_quaternion: 原始四元数
            gyro_data: 陀螺仪数据 (gx, gy, gz) 弧度/秒
            accel_data: 加速度计数据 (ax, ay, az) m/s²
            dt: 时间间隔，如果为None则自动计算
            
        Returns:
            滤波后的四元数
        """
        current_time = time.time()
        
        # 计算时间间隔
        if dt is None:
            if self.last_time is not None:
                dt = current_time - self.last_time
            else:
                dt = 0.02  # 默认50Hz
        
        self.last_time = current_time
        
        # 确保四元数归一化
        raw_quaternion.normalize()
        
        # 第一次调用，直接使用原始数据
        if not self.initialized:
            self.filtered_quaternion = Quaternion(
                raw_quaternion.w, raw_quaternion.x, 
                raw_quaternion.y, raw_quaternion.z
            )
            self.initialized = True
            self.quaternion_history.append(self.filtered_quaternion)
            return self.filtered_quaternion
        
        # 应用互补滤波
        if gyro_data is not None and accel_data is not None:
            # 完整的互补滤波（有陀螺仪和加速度计数据）
            filtered = self._full_complementary_filter(
                raw_quaternion, gyro_data, accel_data, dt
            )
        else:
            # 简化的互补滤波（仅有四元数数据）
            filtered = self._simplified_complementary_filter(raw_quaternion, dt)

        # 零漂检测和校正
        drift_corrected = self._apply_drift_suppression(filtered, dt)

        # Roll轴特殊零漂抑制（最重要）
        roll_corrected = self._apply_roll_drift_suppression(drift_corrected, dt)

        # Yaw轴特殊零漂抑制
        yaw_corrected = self._apply_yaw_drift_suppression(roll_corrected, dt)

        # 定期重置检查
        final_corrected = self._check_periodic_reset(yaw_corrected)

        # 添加到历史记录
        self.quaternion_history.append(final_corrected)

        # 应用移动平均平滑
        smoothed = self._apply_moving_average()

        # 更新基准四元数
        self._update_reference_quaternion(smoothed)

        self.filtered_quaternion = smoothed
        self.filter_count += 1

        return smoothed
    
    def _full_complementary_filter(self, raw_quat: Quaternion,
                                  gyro_data: Tuple[float, float, float],
                                  accel_data: Tuple[float, float, float],
                                  dt: float) -> Quaternion:
        """完整的互补滤波算法"""
        gx, gy, gz = gyro_data
        ax, ay, az = accel_data
        
        # 陀螺仪积分预测
        gyro_quat = self._integrate_gyroscope(self.filtered_quaternion, gx, gy, gz, dt)
        
        # 加速度计姿态估计
        accel_quat = self._estimate_from_accelerometer(ax, ay, az)
        
        # 互补滤波融合
        filtered = self._quaternion_slerp(
            accel_quat, gyro_quat, self.gyro_weight
        )
        
        return filtered
    
    def _simplified_complementary_filter(self, raw_quat: Quaternion, dt: float) -> Quaternion:
        """简化的互补滤波（仅使用四元数数据）"""
        # 使用低通滤波平滑四元数
        alpha = self.alpha
        
        # 球面线性插值 (SLERP)
        filtered = self._quaternion_slerp(
            self.filtered_quaternion, raw_quat, 1.0 - alpha
        )
        
        # 漂移校正
        drift_correction = self._calculate_drift_correction(raw_quat)
        if abs(drift_correction) > 0.001:  # 阈值
            filtered = self._apply_drift_correction(filtered, drift_correction, dt)
            self.total_drift_correction += abs(drift_correction)
        
        return filtered
    
    def _integrate_gyroscope(self, current_quat: Quaternion,
                           gx: float, gy: float, gz: float, dt: float) -> Quaternion:
        """陀螺仪数据积分"""
        # 角速度四元数
        omega_quat = Quaternion(0, gx * dt * 0.5, gy * dt * 0.5, gz * dt * 0.5)
        
        # 四元数乘法积分
        result = self._quaternion_multiply(current_quat, omega_quat)
        result.normalize()
        
        return result
    
    def _estimate_from_accelerometer(self, ax: float, ay: float, az: float) -> Quaternion:
        """从加速度计估计姿态"""
        # 归一化加速度向量
        norm = np.sqrt(ax*ax + ay*ay + az*az)
        if norm == 0:
            return Quaternion(1, 0, 0, 0)
        
        ax, ay, az = ax/norm, ay/norm, az/norm
        
        # 计算Roll和Pitch
        roll = np.arctan2(ay, az)
        pitch = np.arctan2(-ax, np.sqrt(ay*ay + az*az))
        yaw = 0  # 加速度计无法确定Yaw
        
        # 欧拉角转四元数
        return self._euler_to_quaternion(roll, pitch, yaw)
    
    def _euler_to_quaternion(self, roll: float, pitch: float, yaw: float) -> Quaternion:
        """欧拉角转四元数"""
        cr = np.cos(roll * 0.5)
        sr = np.sin(roll * 0.5)
        cp = np.cos(pitch * 0.5)
        sp = np.sin(pitch * 0.5)
        cy = np.cos(yaw * 0.5)
        sy = np.sin(yaw * 0.5)
        
        w = cr * cp * cy + sr * sp * sy
        x = sr * cp * cy - cr * sp * sy
        y = cr * sp * cy + sr * cp * sy
        z = cr * cp * sy - sr * sp * cy
        
        return Quaternion(w, x, y, z)
    
    def _quaternion_multiply(self, q1: Quaternion, q2: Quaternion) -> Quaternion:
        """四元数乘法"""
        w = q1.w * q2.w - q1.x * q2.x - q1.y * q2.y - q1.z * q2.z
        x = q1.w * q2.x + q1.x * q2.w + q1.y * q2.z - q1.z * q2.y
        y = q1.w * q2.y - q1.x * q2.z + q1.y * q2.w + q1.z * q2.x
        z = q1.w * q2.z + q1.x * q2.y - q1.y * q2.x + q1.z * q2.w
        
        return Quaternion(w, x, y, z)
    
    def _quaternion_slerp(self, q1: Quaternion, q2: Quaternion, t: float) -> Quaternion:
        """球面线性插值 (SLERP)"""
        # 计算点积
        dot = q1.w * q2.w + q1.x * q2.x + q1.y * q2.y + q1.z * q2.z
        
        # 如果点积为负，取反一个四元数以选择较短路径
        if dot < 0.0:
            q2 = Quaternion(-q2.w, -q2.x, -q2.y, -q2.z)
            dot = -dot
        
        # 如果四元数非常接近，使用线性插值
        if dot > 0.9995:
            w = q1.w + t * (q2.w - q1.w)
            x = q1.x + t * (q2.x - q1.x)
            y = q1.y + t * (q2.y - q1.y)
            z = q1.z + t * (q2.z - q1.z)
            result = Quaternion(w, x, y, z)
            result.normalize()
            return result
        
        # 球面插值
        theta_0 = np.arccos(abs(dot))
        sin_theta_0 = np.sin(theta_0)
        theta = theta_0 * t
        sin_theta = np.sin(theta)
        
        s0 = np.cos(theta) - dot * sin_theta / sin_theta_0
        s1 = sin_theta / sin_theta_0
        
        w = s0 * q1.w + s1 * q2.w
        x = s0 * q1.x + s1 * q2.x
        y = s0 * q1.y + s1 * q2.y
        z = s0 * q1.z + s1 * q2.z
        
        result = Quaternion(w, x, y, z)
        result.normalize()
        return result
    
    def _calculate_drift_correction(self, raw_quat: Quaternion) -> float:
        """计算漂移校正量"""
        if len(self.quaternion_history) < 3:
            return 0.0
        
        # 计算最近几个四元数的变化趋势
        recent_quats = list(self.quaternion_history)[-3:]
        
        # 计算角度变化率
        angle_changes = []
        for i in range(1, len(recent_quats)):
            angle_diff = self._quaternion_angle_difference(recent_quats[i-1], recent_quats[i])
            angle_changes.append(angle_diff)
        
        # 如果变化过于剧烈，可能是噪声
        if len(angle_changes) > 0:
            avg_change = np.mean(angle_changes)
            current_change = self._quaternion_angle_difference(self.filtered_quaternion, raw_quat)
            
            # 如果当前变化远大于平均变化，应用校正
            if current_change > avg_change * 2.0:
                return (current_change - avg_change) * 0.1  # 校正强度
        
        return 0.0
    
    def _quaternion_angle_difference(self, q1: Quaternion, q2: Quaternion) -> float:
        """计算两个四元数之间的角度差"""
        dot = abs(q1.w * q2.w + q1.x * q2.x + q1.y * q2.y + q1.z * q2.z)
        dot = min(1.0, dot)  # 防止数值误差
        return 2.0 * np.arccos(dot)
    
    def _apply_drift_correction(self, quat: Quaternion, correction: float, dt: float) -> Quaternion:
        """应用漂移校正"""
        # 简单的比例校正
        correction_factor = 1.0 - correction * dt * 0.1
        correction_factor = max(0.9, min(1.1, correction_factor))
        
        # 应用校正到四元数的向量部分
        corrected = Quaternion(
            quat.w,
            quat.x * correction_factor,
            quat.y * correction_factor,
            quat.z * correction_factor
        )
        corrected.normalize()
        
        return corrected

    def _apply_drift_suppression(self, quat: Quaternion, dt: float) -> Quaternion:
        """应用零漂抑制算法"""
        if not self.initialized or len(self.quaternion_history) < 5:
            return quat

        # 检测零漂
        drift_detected, drift_magnitude = self._detect_drift(quat)

        if drift_detected:
            # 应用零漂校正
            corrected_quat = self._correct_drift(quat, drift_magnitude, dt)
            self.drift_corrections_applied += 1
            self.total_drift_correction += drift_magnitude

            logger.debug(f"零漂校正: 幅度={drift_magnitude:.6f}, 校正次数={self.drift_corrections_applied}")
            return corrected_quat

        return quat

    def _detect_drift(self, current_quat: Quaternion) -> Tuple[bool, float]:
        """检测零漂"""
        if len(self.quaternion_history) < self.history_size:
            return False, 0.0

        # 计算最近几个四元数的变化趋势
        recent_quats = list(self.quaternion_history)[-5:]

        # 计算平均变化率
        total_change = 0.0
        for i in range(1, len(recent_quats)):
            change = self._quaternion_angle_difference(recent_quats[i-1], recent_quats[i])
            total_change += change

        avg_change_rate = total_change / (len(recent_quats) - 1) if len(recent_quats) > 1 else 0.0

        # 计算当前变化
        current_change = self._quaternion_angle_difference(self.quaternion_history[-1], current_quat)

        # 检测是否存在持续的小幅度变化（零漂特征）
        self.drift_history.append(current_change)

        if len(self.drift_history) >= self.drift_detection_window:
            # 计算漂移趋势
            recent_drifts = list(self.drift_history)[-10:]
            drift_variance = np.var(recent_drifts)
            drift_mean = np.mean(recent_drifts)

            # 零漂特征：小幅度但持续的变化
            is_drift = (
                drift_mean > self.drift_threshold and
                drift_variance < self.drift_threshold * 0.5 and
                current_change > avg_change_rate * 1.5
            )

            return is_drift, drift_mean

        return False, 0.0

    def _correct_drift(self, quat: Quaternion, drift_magnitude: float, dt: float) -> Quaternion:
        """校正零漂"""
        if self.reference_quaternion is None:
            return quat

        # 计算与基准四元数的偏差
        deviation = self._quaternion_angle_difference(self.reference_quaternion, quat)

        # 如果偏差较大，应用校正
        if deviation > self.drift_threshold * 2:
            # 向基准四元数方向校正
            correction_factor = self.drift_correction_strength * dt
            corrected = self._quaternion_slerp(quat, self.reference_quaternion, correction_factor)

            logger.debug(f"零漂校正: 偏差={deviation:.6f}, 校正因子={correction_factor:.3f}")
            return corrected

        # 应用简单的衰减校正
        decay_factor = 1.0 - drift_magnitude * self.drift_correction_strength * dt
        decay_factor = max(0.95, min(1.0, decay_factor))

        corrected = Quaternion(
            quat.w,
            quat.x * decay_factor,
            quat.y * decay_factor,
            quat.z * decay_factor
        )
        corrected.normalize()

        return corrected

    def _update_reference_quaternion(self, quat: Quaternion):
        """更新基准四元数"""
        self.reference_counter += 1

        # 初始化基准
        if self.reference_quaternion is None:
            self.reference_quaternion = Quaternion(quat.w, quat.x, quat.y, quat.z)
            return

        # 定期更新基准（在数据稳定时）
        if self.reference_counter >= self.reference_update_interval:
            if len(self.drift_history) >= 10:
                recent_stability = np.var(list(self.drift_history)[-10:])

                # 只在数据稳定时更新基准
                if recent_stability < self.drift_threshold * 0.1:
                    # 缓慢更新基准，避免突变
                    self.reference_quaternion = self._quaternion_slerp(
                        self.reference_quaternion, quat, 0.01
                    )
                    logger.debug("基准四元数已更新")

            self.reference_counter = 0

    def _apply_yaw_drift_suppression(self, quat: Quaternion, dt: float) -> Quaternion:
        """专门针对Yaw轴的零漂抑制"""
        if not self.initialized or len(self.quaternion_history) < 10:
            return quat

        # 计算当前欧拉角
        roll, pitch, yaw = quat.to_euler_angles()

        # 计算Yaw轴变化率
        if len(self.quaternion_history) >= 5:
            recent_quats = list(self.quaternion_history)[-5:]
            yaw_changes = []

            for i in range(1, len(recent_quats)):
                _, _, prev_yaw = recent_quats[i-1].to_euler_angles()
                _, _, curr_yaw = recent_quats[i].to_euler_angles()

                # 处理角度跳跃（-180到180度边界）
                yaw_diff = curr_yaw - prev_yaw
                if yaw_diff > math.pi:
                    yaw_diff -= 2 * math.pi
                elif yaw_diff < -math.pi:
                    yaw_diff += 2 * math.pi

                yaw_changes.append(abs(yaw_diff))

            if yaw_changes:
                avg_yaw_change = np.mean(yaw_changes)

                # 如果Yaw轴变化过于缓慢且持续（零漂特征）
                if avg_yaw_change < math.radians(self.yaw_drift_threshold) and len(yaw_changes) >= 3:
                    # 计算Yaw轴校正
                    if self.reference_quaternion:
                        _, _, ref_yaw = self.reference_quaternion_obj.to_euler_angles()

                        yaw_drift = yaw - ref_yaw

                        # 处理角度跳跃
                        if yaw_drift > math.pi:
                            yaw_drift -= 2 * math.pi
                        elif yaw_drift < -math.pi:
                            yaw_drift += 2 * math.pi

                        # 如果Yaw漂移超过阈值，应用校正
                        if abs(yaw_drift) > math.radians(self.yaw_drift_threshold):
                            # 计算校正后的Yaw角
                            corrected_yaw = yaw - yaw_drift * self.yaw_correction_strength * dt

                            # 重新构建四元数（保持Roll和Pitch不变）
                            corrected_quat = self._euler_to_quaternion(roll, pitch, corrected_yaw)

                            logger.debug(f"Yaw轴零漂校正: 漂移={math.degrees(yaw_drift):.2f}°, "
                                       f"校正后Yaw={math.degrees(corrected_yaw):.2f}°")

                            return corrected_quat

        return quat

    def _apply_roll_drift_suppression(self, quat: Quaternion, dt: float) -> Quaternion:
        """专门针对Roll轴的零漂抑制（最重要的优化）"""
        if not self.initialized or len(self.quaternion_history) < 5:
            return quat

        # 计算当前欧拉角
        roll, pitch, yaw = quat.to_euler_angles()

        # 计算Roll轴变化率
        if len(self.quaternion_history) >= 3:
            recent_quats = list(self.quaternion_history)[-3:]
            roll_changes = []

            for i in range(1, len(recent_quats)):
                prev_roll, _, _ = recent_quats[i-1].to_euler_angles()
                curr_roll, _, _ = recent_quats[i].to_euler_angles()

                # 处理角度跳跃
                roll_diff = curr_roll - prev_roll
                if roll_diff > math.pi:
                    roll_diff -= 2 * math.pi
                elif roll_diff < -math.pi:
                    roll_diff += 2 * math.pi

                roll_changes.append(abs(roll_diff))

            if roll_changes:
                avg_roll_change = np.mean(roll_changes)

                # 如果Roll轴变化过于缓慢且持续（零漂特征）
                if avg_roll_change < math.radians(self.roll_drift_threshold):
                    # 计算Roll轴校正
                    if self.reference_quaternion:
                        ref_roll, _, _ = self.reference_quaternion.to_euler_angles()

                        roll_drift = roll - ref_roll

                        # 处理角度跳跃
                        if roll_drift > math.pi:
                            roll_drift -= 2 * math.pi
                        elif roll_drift < -math.pi:
                            roll_drift += 2 * math.pi

                        # 如果Roll漂移超过阈值，应用强力校正
                        if abs(roll_drift) > math.radians(self.roll_drift_threshold):
                            # 计算校正后的Roll角
                            corrected_roll = roll - roll_drift * self.roll_correction_strength * dt

                            # 重新构建四元数（保持Pitch和Yaw不变）
                            corrected_quat = self._euler_to_quaternion(corrected_roll, pitch, yaw)

                            logger.debug(f"Roll轴零漂校正: 漂移={math.degrees(roll_drift):.3f}°, "
                                       f"校正后Roll={math.degrees(corrected_roll):.3f}°")

                            return corrected_quat

        return quat

    def _check_periodic_reset(self, quat: Quaternion) -> Quaternion:
        """定期重置基准以防止长期累积漂移"""
        self.reset_counter += 1

        if self.reset_counter >= self.reset_interval:
            # 重置基准四元数为当前值
            self.reference_quaternion = Quaternion(quat.w, quat.x, quat.y, quat.z)
            self.reset_counter = 0

            logger.info(f"定期重置基准四元数: w={quat.w:.4f}, x={quat.x:.4f}, y={quat.y:.4f}, z={quat.z:.4f}")

        return quat

    @property
    def reference_quaternion_obj(self):
        """获取基准四元数对象"""
        # reference_quaternion已经是Quaternion对象，直接返回
        return self.reference_quaternion

    def _apply_moving_average(self) -> Quaternion:
        """应用移动平均平滑"""
        if len(self.quaternion_history) < 2:
            return self.quaternion_history[-1]
        
        # 加权平均，最新的数据权重更大
        weights = np.array([0.1, 0.2, 0.3, 0.4])  # 最多4个历史点
        quats = list(self.quaternion_history)[-len(weights):]
        
        if len(quats) < len(weights):
            weights = weights[-len(quats):]
        
        # 归一化权重
        weights = weights / np.sum(weights)
        
        # 加权平均
        w = sum(q.w * w for q, w in zip(quats, weights))
        x = sum(q.x * w for q, w in zip(quats, weights))
        y = sum(q.y * w for q, w in zip(quats, weights))
        z = sum(q.z * w for q, w in zip(quats, weights))
        
        result = Quaternion(w, x, y, z)
        result.normalize()
        
        return result
    
    def get_filter_statistics(self) -> dict:
        """获取滤波器统计信息"""
        drift_rate = self.drift_corrections_applied / max(1, self.filter_count) * 100
        avg_drift = self.total_drift_correction / max(1, self.drift_corrections_applied)

        return {
            'filter_count': self.filter_count,
            'total_drift_correction': self.total_drift_correction,
            'avg_drift_correction': self.total_drift_correction / max(1, self.filter_count),
            'drift_corrections_applied': self.drift_corrections_applied,
            'drift_correction_rate': drift_rate,
            'avg_drift_magnitude': avg_drift,
            'history_size': len(self.quaternion_history),
            'drift_history_size': len(self.drift_history),
            'alpha': self.alpha,
            'gyro_weight': self.gyro_weight,
            'has_reference': self.reference_quaternion is not None,
            'initialized': self.initialized
        }
    
    def set_parameters(self, alpha: Optional[float] = None, 
                      gyro_weight: Optional[float] = None):
        """动态调整滤波器参数"""
        if alpha is not None:
            self.alpha = max(0.5, min(0.999, alpha))
            logger.info(f"互补滤波器alpha调整为: {self.alpha}")
        
        if gyro_weight is not None:
            self.gyro_weight = max(0.5, min(0.999, gyro_weight))
            self.accel_weight = 1.0 - self.gyro_weight
            logger.info(f"陀螺仪权重调整为: {self.gyro_weight}")


class AdaptiveComplementaryFilter(ComplementaryFilter):
    """自适应互补滤波器 - 根据数据质量自动调整参数"""
    
    def __init__(self, alpha: float = 0.98, gyro_weight: float = 0.98):
        super().__init__(alpha, gyro_weight)
        
        # 自适应参数
        self.noise_threshold = 0.1
        self.stability_window = 10
        self.stability_history = deque(maxlen=self.stability_window)
        
        # 动态参数范围
        self.alpha_range = (0.90, 0.99)
        self.gyro_weight_range = (0.90, 0.99)
        
        logger.info("自适应互补滤波器已初始化")
    
    def filter_quaternion(self, raw_quaternion: Quaternion, 
                         gyro_data: Optional[Tuple[float, float, float]] = None,
                         accel_data: Optional[Tuple[float, float, float]] = None,
                         dt: Optional[float] = None) -> Quaternion:
        """自适应滤波"""
        # 评估数据稳定性
        stability = self._assess_data_stability(raw_quaternion)
        self.stability_history.append(stability)
        
        # 根据稳定性调整参数
        self._adapt_parameters()
        
        # 应用滤波
        return super().filter_quaternion(raw_quaternion, gyro_data, accel_data, dt)
    
    def _assess_data_stability(self, raw_quat: Quaternion) -> float:
        """评估数据稳定性 (0-1, 1表示最稳定)"""
        if not self.initialized or len(self.quaternion_history) < 2:
            return 1.0
        
        # 计算与上一个四元数的角度差
        last_quat = self.quaternion_history[-1]
        angle_diff = self._quaternion_angle_difference(last_quat, raw_quat)
        
        # 将角度差映射到稳定性分数
        stability = max(0.0, 1.0 - angle_diff / self.noise_threshold)
        
        return stability
    
    def _adapt_parameters(self):
        """根据稳定性历史自适应调整参数"""
        if len(self.stability_history) < self.stability_window:
            return
        
        avg_stability = np.mean(self.stability_history)
        
        # 稳定性高时，增加alpha（更信任历史数据）
        # 稳定性低时，减少alpha（更快响应新数据）
        alpha_min, alpha_max = self.alpha_range
        self.alpha = alpha_min + (alpha_max - alpha_min) * avg_stability
        
        # 类似地调整陀螺仪权重
        gyro_min, gyro_max = self.gyro_weight_range
        self.gyro_weight = gyro_min + (gyro_max - gyro_min) * avg_stability
        self.accel_weight = 1.0 - self.gyro_weight
