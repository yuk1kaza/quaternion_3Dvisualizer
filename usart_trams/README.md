# USART Trams - 高性能串口数据处理系统

一个专为解决数据转换延迟问题而设计的高性能串口数据处理和可视化系统。

## 🚀 主要特性

### 性能优化
- **异步串口通信** - 使用asyncio避免阻塞，提高响应速度
- **多线程/多进程处理** - 分离数据接收、处理和显示，最大化并行性
- **智能缓冲管理** - 批处理数据减少频繁的小数据处理开销
- **数据缓存机制** - 缓存常用数据转换结果，避免重复计算
- **NumPy加速** - 使用NumPy进行高效的数值计算

### 数据处理
- **多格式支持** - 支持HEX、ASCII、二进制数据格式
- **实时数据过滤** - 可配置的数据过滤器去除噪声
- **自动格式检测** - 智能识别数据格式
- **数据验证** - 确保数据完整性和正确性

### 可视化
- **硬件加速渲染** - 使用VisPy和OpenGL实现低延迟显示
- **实时数据流** - 毫秒级数据更新
- **自适应缩放** - 自动调整显示范围
- **交互式操作** - 支持缩放、平移、重置等操作

### 监控和调试
- **性能统计** - 实时显示FPS、处理速率、延迟等指标
- **详细日志** - 完整的操作日志记录
- **内存监控** - 防止内存泄漏
- **错误恢复** - 自动错误处理和恢复机制

## 📦 安装

### 环境要求
- Python 3.8+
- Windows/Linux/macOS

### 安装依赖
```bash
pip install -r requirements.txt
```

### 快速开始
```bash
python main.py
```

## ⚙️ 配置

系统使用 `config.json` 文件进行配置，主要配置项包括：

### 串口配置
```json
{
  "serial": {
    "port": "COM3",           // 串口号
    "baudrate": 115200,       // 波特率
    "timeout": 0.1,           // 超时时间
    "bytesize": 8,            // 数据位
    "parity": "N",            // 校验位
    "stopbits": 1             // 停止位
  }
}
```

### 性能优化配置
```json
{
  "processing": {
    "buffer_size": 8192,      // 缓冲区大小
    "batch_size": 100,        // 批处理大小
    "processing_interval": 0.01, // 处理间隔(秒)
    "data_format": "hex"      // 数据格式
  },
  "performance": {
    "use_multiprocessing": true,  // 启用多进程
    "worker_processes": 2,        // 工作进程数
    "enable_caching": true,       // 启用缓存
    "cache_size": 1000           // 缓存大小
  }
}
```

## 🎯 性能优化说明

### 延迟优化策略

1. **异步I/O架构**
   - 串口读取、数据处理、可视化更新完全异步
   - 避免任何阻塞操作影响整体性能

2. **批处理机制**
   - 将小数据包合并为批次处理
   - 减少函数调用开销和上下文切换

3. **多级缓存**
   - 数据转换结果缓存
   - 减少重复计算开销

4. **硬件加速**
   - 使用OpenGL进行图形渲染
   - NumPy进行数值计算加速

5. **内存优化**
   - 循环缓冲区避免内存增长
   - 及时释放不需要的数据

### 典型性能指标

- **数据处理延迟**: < 1ms
- **可视化更新频率**: 60+ FPS
- **串口吞吐量**: 1MB/s+
- **内存使用**: < 100MB

## 🔧 使用说明

### 基本操作

1. **启动程序**
   ```bash
   python main.py
   ```

2. **配置串口**
   - 修改 `config.json` 中的串口参数
   - 或使用程序自动检测功能

3. **数据格式设置**
   - 支持 `hex`、`ascii`、`binary` 格式
   - 在配置文件中设置 `data_format`

### 快捷键操作

- `R` - 重置视图
- `C` - 清空数据
- `S` - 保存截图
- `Q/ESC` - 退出程序

### 命令行参数

```bash
python main.py --config custom_config.json  # 使用自定义配置
python main.py --port COM4                  # 指定串口
python main.py --baudrate 9600             # 指定波特率
python main.py --debug                     # 启用调试模式
```

## 📊 性能监控

程序提供实时性能监控：

- **FPS显示** - 可视化帧率
- **数据速率** - 串口接收速率
- **处理延迟** - 数据处理时间
- **内存使用** - 实时内存占用
- **缓存命中率** - 缓存效率统计

## 🛠️ 开发和调试

### 性能分析
```bash
# 使用line_profiler分析性能瓶颈
kernprof -l -v main.py

# 使用memory_profiler监控内存
python -m memory_profiler main.py
```

### 测试
```bash
# 运行单元测试
pytest tests/

# 运行性能测试
pytest tests/test_performance.py -v
```

## 🔍 故障排除

### 常见问题

1. **串口连接失败**
   - 检查串口号是否正确
   - 确认串口未被其他程序占用
   - 验证波特率等参数设置

2. **数据显示异常**
   - 检查数据格式设置
   - 验证数据过滤器配置
   - 查看日志文件排查问题

3. **性能问题**
   - 调整批处理大小
   - 启用多进程处理
   - 优化缓冲区配置

### 日志分析
程序会生成详细的日志文件 `usart_trams.log`，包含：
- 性能统计信息
- 错误和警告信息
- 数据处理详情

## 📈 性能调优建议

### 硬件建议
- **CPU**: 4核心以上，支持多线程
- **内存**: 8GB以上
- **显卡**: 支持OpenGL 3.0+

### 软件优化
1. **调整批处理大小**
   - 高速数据流：增大batch_size
   - 低延迟要求：减小batch_size

2. **缓冲区优化**
   - 根据数据速率调整buffer_size
   - 平衡内存使用和性能

3. **多进程配置**
   - CPU密集型：启用多进程
   - I/O密集型：使用多线程

## 📄 许可证

MIT License - 详见 LICENSE 文件

## 🤝 贡献

欢迎提交Issue和Pull Request来改进项目！

## 📞 支持

如有问题或建议，请通过以下方式联系：
- 提交GitHub Issue
- 发送邮件至项目维护者

---

**注意**: 本系统专为高性能数据处理设计，在使用前请根据实际需求调整配置参数以获得最佳性能。
