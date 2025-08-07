# 🎯 项目结构说明

## 📁 整理后的项目文件

### 🚀 主要可视化器
| 文件名 | 功能描述 | 推荐使用场景 |
|--------|----------|-------------|
| `quaternion_3d_final_reset.py` | **最终版带重置功能3D可视化器** | ⭐ 需要重置功能的应用 |
| `quaternion_3d_visualizer.py` | **完整功能自适应3D可视化器** | ⭐ 专业级应用，全功能 |
| `simple_quaternion_3d.py` | **精简版3D可视化器** | 简单测试，快速启动 |

### 📊 绘图工具
| 文件名 | 功能描述 | 推荐使用场景 |
|--------|----------|-------------|
| `quaternion_time_plotter.py` | **增强版时间轴绘图工具** | ⭐ 实时绘图，支持历史数据 |
| `simple_quaternion_plotter.py` | **简化版绘图工具** | 数据收集和离线分析 |

### 🎮 启动器和工具
| 文件名 | 功能描述 | 推荐使用场景 |
|--------|----------|-------------|
| `adaptive_visualizer_launcher.py` | **统一启动器** | ⭐ 一键启动，选择不同方法 |
| `com12_port_checker.py` | **串口诊断工具** | 串口问题排查 |

### 📚 核心库和文档
| 文件/目录 | 功能描述 |
|-----------|----------|
| `src/` | **核心库目录** |
| `├── config.py` | 配置管理 |
| `├── serial_manager.py` | 串口管理 |
| `├── quaternion_processor.py` | 四元数处理 |
| `└── complementary_filter.py` | 互补滤波器 |
| `README.md` | **项目文档** |
| `requirements.txt` | **依赖包列表** |

## 🎯 推荐使用方式

### 新用户入门
```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 使用统一启动器
python adaptive_visualizer_launcher.py
```

### 专业用户
```bash
# 带重置功能的3D可视化
python quaternion_3d_final_reset.py

# 完整功能的3D可视化
python quaternion_3d_visualizer.py

# 时间轴绘图
python quaternion_time_plotter.py
```

### 开发者
```bash
# 精简版测试
python simple_quaternion_3d.py

# 串口诊断
python com12_port_checker.py
```

## 🗂️ 文件功能对比

### 3D可视化器对比
| 功能 | 最终版 | 完整版 | 精简版 |
|------|--------|--------|--------|
| 重置功能 | ✅ | ❌ | ❌ |
| 自适应速率 | ❌ | ✅ | ❌ |
| 运动轨迹 | ❌ | ✅ | ❌ |
| 零漂抑制 | ❌ | ✅ | ❌ |
| 启动速度 | 快 | 中等 | 最快 |
| 资源占用 | 低 | 中等 | 最低 |

### 绘图工具对比
| 功能 | 增强版 | 简化版 |
|------|--------|--------|
| 实时绘图 | ✅ | ❌ |
| 历史数据保持 | ✅ | ❌ |
| 显示模式切换 | ✅ | ❌ |
| 数据导出 | ❌ | ✅ |
| 自动生成绘图脚本 | ❌ | ✅ |

## 🧹 已删除的文件

以下文件已被删除以简化项目结构：
- `README_Quaternion.md` - 重复文档
- `enhanced_vpython_visualizer.py` - VPython版本（功能重复）
- `main.py` - 旧版主程序
- `config.json` - 旧版配置文件
- `setup.py` - 安装脚本（不需要）
- `install.bat/sh` - 安装脚本（不需要）
- `test_*.py` - 测试文件（功能已集成）
- `*.log` - 日志文件
- `examples/` - 示例目录（功能已集成）
- `tests/` - 测试目录（功能已集成）
- `tools/` - 工具目录（功能已集成）

## 💡 使用建议

1. **首次使用**: 运行 `adaptive_visualizer_launcher.py`
2. **需要重置功能**: 使用 `quaternion_3d_final_reset.py`
3. **专业应用**: 使用 `quaternion_3d_visualizer.py`
4. **数据分析**: 使用 `quaternion_time_plotter.py`
5. **问题排查**: 使用 `com12_port_checker.py`

项目现在结构清晰，文件精简，每个文件都有明确的用途！
