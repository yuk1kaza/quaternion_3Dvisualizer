# 四元数3D可视化系统

专为COM6串口四元数数据设计的高性能3D可视化和图表分析系统。

## 🎯 主要功能

### 3D可视化 (VPython)
- **实时3D姿态显示** - 立体显示传感器姿态
- **交互式3D场景** - 鼠标控制视角、缩放、平移
- **姿态轨迹追踪** - 显示姿态变化轨迹
- **坐标系参考** - 清晰的XYZ坐标轴显示
- **实时信息面板** - 显示四元数、欧拉角、FPS等信息

### 数据图表 (Matplotlib)
- **四元数分量图** - w, x, y, z 四个分量的实时曲线
- **欧拉角图表** - Roll, Pitch, Yaw 角度变化曲线
- **角度单位切换** - 支持度和弧度显示
- **数据导出功能** - 保存图表为PNG图片
- **交互式控制** - 开始/停止、清空数据等操作

### 数据处理
- **多格式支持** - Float32, Float64, ASCII, 自定义格式
- **实时数据验证** - 四元数有效性检查和归一化
- **高性能处理** - 异步数据处理，低延迟响应
- **统计监控** - 数据包成功率、处理速度等统计

## 🚀 快速开始

### 1. 安装依赖
```bash
pip install vpython matplotlib pyserial numpy
```

### 2. 连接设备
- 将四元数传感器连接到COM6串口
- 确保设备正常工作并发送四元数数据

### 3. 启动系统
```bash
# 方式1: 使用启动脚本 (推荐)
run_quaternion_visualizer.bat

# 方式2: 直接运行
python quaternion_visualizer.py

# 方式3: 自定义参数
python quaternion_visualizer.py --port COM6 --baudrate 115200 --format float32
```

### 4. 测试系统
```bash
python test_quaternion_visualizer.py
```

## 📊 数据格式

系统支持多种四元数数据格式：

### Float32 格式 (默认)
- **数据长度**: 16字节
- **数据结构**: w(4字节) + x(4字节) + y(4字节) + z(4字节)
- **字节序**: 小端序 (Little Endian)
- **示例**: `3F800000 00000000 00000000 00000000` (单位四元数)

### Float64 格式
- **数据长度**: 32字节
- **数据结构**: w(8字节) + x(8字节) + y(8字节) + z(8字节)
- **字节序**: 小端序

### ASCII 格式
- **数据格式**: `w,x,y,z\n`
- **示例**: `1.0,0.0,0.0,0.0\n`
- **分隔符**: 逗号
- **行结束**: 换行符

### 自定义格式
- **包结构**: [包头2字节] + [四元数16字节] + [校验和2字节]
- **包头**: 0xAA55
- **可根据实际协议修改**

## 🎮 操作说明

### VPython 3D窗口
- **鼠标左键拖拽**: 旋转视角
- **鼠标滚轮**: 缩放视图
- **鼠标右键拖拽**: 平移视图
- **重置视图按钮**: 恢复默认视角
- **清空轨迹按钮**: 清除姿态轨迹
- **切换轨迹按钮**: 显示/隐藏轨迹

### Matplotlib 图表窗口
- **开始/停止按钮**: 控制数据采集
- **清空数据按钮**: 清除历史数据
- **保存图表按钮**: 导出PNG图片
- **显示选项**: 切换四元数/欧拉角显示
- **角度单位**: 度/弧度切换

## ⚙️ 配置选项

### 串口配置
```json
{
  "serial": {
    "port": "COM6",
    "baudrate": 115200,
    "timeout": 0.1
  }
}
```

### 数据处理配置
```json
{
  "processing": {
    "data_format": "float32",
    "batch_size": 50,
    "processing_interval": 0.02,
    "enable_filtering": true
  }
}
```

### 可视化配置
```json
{
  "visualization": {
    "update_interval": 0.033,
    "max_points": 500,
    "show_trail": true,
    "trail_length": 100
  }
}
```

## 📈 性能指标

### 典型性能
- **数据处理延迟**: < 2ms
- **3D渲染帧率**: 30+ FPS
- **图表更新频率**: 20 Hz
- **内存使用**: < 200MB
- **CPU使用率**: < 20% (四核心)

### 优化建议
1. **高速数据流**: 增大batch_size到100-200
2. **低延迟要求**: 减小processing_interval到0.01
3. **内存限制**: 减小max_points到200-300
4. **CPU限制**: 降低更新频率

## 🔧 故障排除

### 常见问题

1. **COM6连接失败**
   ```
   解决方案:
   - 检查设备是否连接到COM6
   - 确认串口未被其他程序占用
   - 检查波特率设置是否正确
   - 尝试重新插拔USB设备
   ```

2. **VPython无法启动**
   ```
   解决方案:
   - 确保安装了VPython: pip install vpython
   - 检查OpenGL驱动是否正常
   - 尝试更新显卡驱动
   - 在虚拟环境中运行
   ```

3. **数据解析错误**
   ```
   解决方案:
   - 检查数据格式设置是否正确
   - 验证四元数数据的字节序
   - 使用测试数据验证解析功能
   - 检查数据包完整性
   ```

4. **图表显示异常**
   ```
   解决方案:
   - 确保安装了matplotlib和tkinter
   - 检查系统GUI环境
   - 尝试不同的matplotlib后端
   - 重启应用程序
   ```

### 调试模式
```bash
# 启用详细日志
python quaternion_visualizer.py --port COM6 --debug

# 查看日志文件
type quaternion_visualizer.log
```

## 📝 开发说明

### 项目结构
```
src/
├── quaternion_processor.py    # 四元数数据处理
├── vpython_visualizer.py      # VPython 3D可视化
├── quaternion_plotter.py      # Matplotlib图表
├── serial_manager.py          # 串口管理
└── config.py                  # 配置管理

quaternion_visualizer.py       # 主程序
test_quaternion_visualizer.py  # 测试脚本
```

### 扩展开发
1. **自定义数据格式**: 修改`quaternion_processor.py`中的解析函数
2. **新增可视化**: 继承基础可视化类添加新功能
3. **数据导出**: 添加CSV、JSON等格式导出功能
4. **网络传输**: 支持TCP/UDP数据接收

### API接口
```python
# 四元数处理
processor = QuaternionProcessor(config)
processor.set_data_format('float32')
result = processor.process_raw_data(raw_data)

# 3D可视化
visualizer = VPython3DVisualizer(config, processor)
await visualizer.start()

# 图表绘制
plotter = QuaternionPlotter(config, processor)
await plotter.start()
```

## 📄 许可证

MIT License - 详见 LICENSE 文件

## 🤝 支持

- **GitHub Issues**: 报告问题和建议
- **文档**: 查看详细API文档
- **示例**: 参考example目录中的示例代码

---

**注意**: 本系统专为四元数数据可视化设计，确保您的设备发送标准的四元数格式数据以获得最佳效果。
