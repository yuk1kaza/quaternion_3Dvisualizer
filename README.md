# 🎯 四元数与六轴数据可视化工具集

这是一个功能完整的Python工具集，用于实时可视化四元数和六轴IMU数据，支持从串口读取数据并进行3D可视化、时间序列绘图和姿态解算。

## ✨ 功能特性

- 🎯 **实时3D四元数可视化** - 支持重置功能和自适应速率匹配
- 📊 **六轴数据姿态解算** - 互补滤波融合加速度计和陀螺仪数据
- 📈 **时间序列数据绘图** - 实时绘图和历史数据保持
- 🔌 **多格式串口数据采集** - 支持ASCII和二进制格式
- ⚡ **高性能数据处理** - 异步处理和多线程优化
- 🎮 **交互式3D控制** - 鼠标操作和键盘快捷键
- 🔧 **智能诊断工具** - 串口检测和数据验证

## 🚀 快速开始

### 安装依赖
```bash
pip install -r requirements.txt
```

### 统一启动器（推荐新用户）
```bash
python adaptive_visualizer_launcher.py
```

### 直接启动特定功能
```bash
# 带重置功能的3D可视化（最新版本）
python quaternion_3d_final_reset.py

# 完整功能的3D可视化
python quaternion_3d_visualizer.py

# 六轴数据3D可视化
python six_axis_3d_visualizer.py

# 时间序列绘图
python quaternion_time_plotter.py

# 串口诊断
python com12_port_checker.py
```

## 📊 支持的数据格式

### 四元数数据
- **ASCII格式**: `w,x,y,z` (一行一个四元数)
- **二进制格式**: 4个连续的float32值

### 六轴IMU数据
- **CSV格式**: `ax,ay,az,gx,gy,gz`
  - `ax,ay,az`: 加速度计数据 (m/s²)
  - `gx,gy,gz`: 陀螺仪数据 (度/秒)

## 🎮 主要工具介绍

### 1. 🎯 带重置功能的3D可视化器
**文件**: `quaternion_3d_final_reset.py`

**特色功能**:
- ✅ **R键重置**: 将当前位置设为初始姿态
- ✅ **真正的位姿重置**: 不影响相机视角，只重置模型姿态
- ✅ **四元数偏移计算**: 使用数学准确的四元数运算

**使用方法**:
- 在控制台窗口按 **R** 键重置模型位姿
- 在控制台窗口按 **ESC** 键退出程序
- 在3D窗口中鼠标操作（旋转、平移、缩放）

### 2. 📊 六轴数据3D可视化器
**文件**: `six_axis_3d_visualizer.py`

**特色功能**:
- ✅ **原始六轴数据输入**: 直接处理加速度计和陀螺仪数据
- ✅ **互补滤波算法**: 自动融合六轴数据为四元数
- ✅ **自动校准**: 启动时自动进行陀螺仪零点校准
- ✅ **实时姿态解算**: 显示Roll、Pitch、Yaw角度

**算法原理**:
```
姿态角 = α × 陀螺仪积分 + β × 加速度计倾斜角
α = 0.98 (陀螺仪权重), β = 0.02 (加速度计权重)
```

### 3. 🎨 完整功能3D可视化器
**文件**: `quaternion_3d_visualizer.py`

**特色功能**:
- ✅ **自适应速率匹配**: 自动调整渲染频率匹配数据传输速率
- ✅ **运动轨迹显示**: 可选显示传感器运动轨迹
- ✅ **零漂抑制**: 内置互补滤波器减少累积误差
- ✅ **多种显示模式**: 支持不同的可视化效果

### 4. 📈 增强版时间轴绘图工具
**文件**: `quaternion_time_plotter.py`

**特色功能**:
- ✅ **实时绘图**: 动态更新的时间序列图表
- ✅ **完整历史保持**: 保留所有历史数据而非滑动窗口
- ✅ **多显示模式**: 四元数分量、欧拉角、模长等
- ✅ **交互式控制**: 暂停、恢复、清除等操作

### 5. 🔧 串口诊断工具
**文件**: `com12_port_checker.py`

**特色功能**:
- ✅ **端口检测**: 自动检测可用串口
- ✅ **数据格式识别**: 自动识别ASCII/二进制格式
- ✅ **连接测试**: 验证串口连接和数据传输
- ✅ **问题诊断**: 提供详细的错误信息和解决建议

## 🗂️ 项目结构

```
📁 usart_trams/
├── 🚀 主要可视化器
│   ├── quaternion_3d_final_reset.py    # ⭐ 带重置功能3D可视化器
│   ├── quaternion_3d_visualizer.py     # ⭐ 完整功能3D可视化器
│   ├── simple_quaternion_3d.py         # 精简版3D可视化器
│   └── six_axis_3d_visualizer.py       # ⭐ 六轴数据3D可视化器
├── 📊 绘图工具
│   ├── quaternion_time_plotter.py      # ⭐ 增强版时间轴绘图
│   └── simple_quaternion_plotter.py    # 简化版绘图工具
├── 🎮 启动器和工具
│   ├── adaptive_visualizer_launcher.py # ⭐ 统一启动器
│   └── com12_port_checker.py           # 串口诊断工具
├── 📚 核心库
│   └── src/
│       ├── config.py                   # 配置管理
│       ├── serial_manager.py           # 串口管理
│       ├── quaternion_processor.py     # 四元数处理
│       └── complementary_filter.py     # 互补滤波器
├── 📖 文档
│   ├── README.md                       # 项目文档
│   ├── PROJECT_STRUCTURE.md            # 项目结构说明
│   └── requirements.txt                # 依赖包列表
```

## 🎯 使用场景推荐

### 新用户入门
```bash
python adaptive_visualizer_launcher.py  # 统一启动器，选择不同方法
```

### 需要重置功能
```bash
python quaternion_3d_final_reset.py     # 支持R键重置模型位姿
```

### 原始IMU数据处理
```bash
python six_axis_3d_visualizer.py        # 直接处理六轴数据
```

### 专业级应用
```bash
python quaternion_3d_visualizer.py      # 完整功能，自适应速率
```

### 数据分析
```bash
python quaternion_time_plotter.py       # 实时绘图和数据分析
```

### 问题排查
```bash
python com12_port_checker.py            # 串口连接诊断
```

## ⚙️ 配置选项

### 串口配置
- **端口**: COM3, COM6, COM12, COM14 等
- **波特率**: 9600, 115200, 128000, 230400, 460800 等
- **超时**: 可配置读取超时时间

### 数据处理
- **格式检测**: 自动识别ASCII/二进制格式
- **滤波选项**: 可选启用互补滤波器
- **校准模式**: 自动或手动校准

### 可视化设置
- **渲染质量**: 可调整渲染精度和性能
- **显示模式**: 多种可视化效果选择
- **交互控制**: 自定义键盘和鼠标操作
## 🔧 技术特性

### 高性能处理
- **异步I/O**: 使用asyncio进行高效数据处理
- **多线程**: 数据处理和渲染分离
- **内存优化**: 智能缓存和垃圾回收

### 数学算法
- **四元数运算**: 完整的四元数数学库
- **互补滤波**: 减少传感器噪声和漂移
- **姿态解算**: 从原始IMU数据计算姿态

### 用户体验
- **智能配置**: 自动检测和推荐设置
- **错误处理**: 详细的错误信息和恢复机制
- **实时反馈**: 状态信息和性能监控

## 📋 系统要求

### Python版本
- Python 3.7 或更高版本

### 主要依赖
- `open3d` - 3D可视化
- `matplotlib` - 2D绘图
- `numpy` - 数值计算
- `pyserial` - 串口通信
- `asyncio` - 异步处理

### 操作系统
- Windows 10/11 (主要测试平台)
- Linux (Ubuntu 18.04+)
- macOS (10.14+)

## 🐛 故障排除

### 常见问题

**1. 串口连接失败**
```bash
python com12_port_checker.py  # 使用诊断工具检查
```

**2. 数据格式错误**
- 检查数据格式是否为 `w,x,y,z` 或 `ax,ay,az,gx,gy,gz`
- 确认波特率设置正确

**3. 3D窗口无响应**
- 确保安装了正确版本的Open3D
- 检查显卡驱动是否支持OpenGL

**4. 重置功能不工作**
- 确保在控制台窗口（不是3D窗口）按R键
- 检查程序是否正在接收数据

### 性能优化建议

1. **降低数据传输频率**: 如果出现延迟，可以降低传感器数据输出频率
2. **关闭不必要的功能**: 使用精简版可视化器提高性能
3. **调整渲染质量**: 在配置中降低渲染精度

## 🤝 贡献指南

欢迎提交Issue和Pull Request来改进这个项目！

### 开发环境设置
```bash
git clone <repository-url>
cd usart_trams
pip install -r requirements.txt
```

### 代码规范
- 使用Python PEP 8代码风格
- 添加适当的注释和文档字符串
- 编写单元测试

## 📄 许可证

MIT License - 详见LICENSE文件

## 🙏 致谢

感谢所有为这个项目做出贡献的开发者和用户！

---

**🎯 开始使用**: `python adaptive_visualizer_launcher.py`

**📖 详细文档**: 查看 `PROJECT_STRUCTURE.md`

**🐛 问题反馈**: 请提交Issue或联系开发者
