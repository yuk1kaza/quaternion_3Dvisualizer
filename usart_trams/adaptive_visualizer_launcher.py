#!/usr/bin/env python3
"""
自适应四元数可视化器启动器
支持所有可视化方法，全部配备自适应速率匹配技术
少司命 编辑于 2025年6月25日
"""

import sys
import time
from pathlib import Path

def main():
    """主启动器"""
    print(f"""
🎯 自适应四元数3D可视化器启动器
===============================

🚀 全新自适应速率匹配技术
✅ 自动检测串口数据传输速率
✅ 动态调整渲染频率完美匹配
✅ 智能插值因子自动优化
✅ 所有方法都支持丝滑运动

选择可视化方法:
""")
    
    # 可视化方法配置
    methods = {
        "1": {
            "name": "Open3D 3D可视化器 (推荐)",
            "description": "专业级3D引擎，完美视角控制，极速响应",
            "script": "quaternion_3d_visualizer.py",
            "features": ["🎯 自适应速率匹配", "⚡ 超响应", "🖱️ 完美视角控制", "🔄 SLERP插值"]
        },
        "2": {
            "name": "VPython 3D可视化器",
            "description": "轻量级3D可视化，简单易用，跨平台",
            "script": "enhanced_vpython_visualizer.py", 
            "features": ["🎯 自适应速率匹配", "🌐 Web界面", "📱 跨平台", "🎨 美观界面"]
        }
    }
    
    # 串口配置
    port_configs = {
        "1": {"port": "COM6", "baudrate": 115200, "data_format": "ascii", "name": "COM6 ASCII (自适应)"},
        "2": {"port": "COM12", "baudrate": 128000, "data_format": "ascii", "name": "COM12 ASCII (自适应)"},
        "3": {"port": "COM6", "baudrate": 921600, "data_format": "ascii", "name": "COM6 高速 (自适应)"},
        "4": {"port": "COM3", "baudrate": 115200, "data_format": "ascii", "name": "COM3 标准 (自适应)"},
        "5": {"port": "COM4", "baudrate": 230400, "data_format": "ascii", "name": "COM4 中速 (自适应)"},
        "6": {"port": "COM5", "baudrate": 57600, "data_format": "ascii", "name": "COM5 低速 (自适应)"},
        "7": {"port": "COM7", "baudrate": 38400, "data_format": "ascii", "name": "COM7 兼容 (自适应)"},
        "8": {"port": "COM8", "baudrate": 19200, "data_format": "ascii", "name": "COM8 稳定 (自适应)"},
    }
    
    # 显示可视化方法
    for key, method in methods.items():
        print(f"  {key}. {method['name']}")
        print(f"     {method['description']}")
        for feature in method['features']:
            print(f"     {feature}")
        print()
    
    try:
        # 选择可视化方法
        method_choice = input("请选择可视化方法 (1-2, 默认1): ").strip() or "1"
        
        if method_choice not in methods:
            print("❌ 无效的方法选择")
            return
        
        selected_method = methods[method_choice]
        print(f"\n✅ 选择: {selected_method['name']}")
        
        # 显示串口配置
        print(f"\n选择串口配置 (全部支持自适应速率匹配):")
        for key, config in port_configs.items():
            print(f"  {key}. {config['name']}")
        
        print(f"\n🎯 自适应技术特性:")
        print(f"  ✅ 实时检测串口数据速率")
        print(f"  ✅ 动态调整渲染频率匹配数据频率")
        print(f"  ✅ 智能插值因子自动优化")
        print(f"  ✅ 完美丝滑运动效果")
        print(f"  ✅ 支持任意数据频率 (1Hz - 1000Hz+)")
        
        # 选择串口配置
        port_choice = input(f"\n请选择串口配置 (1-{len(port_configs)}, 默认2): ").strip() or "2"
        
        if port_choice not in port_configs:
            print("❌ 无效的串口选择")
            return
        
        selected_port = port_configs[port_choice]
        print(f"✅ 选择: {selected_port['name']}")
        
        # 启动选择的可视化器
        print(f"\n🚀 启动 {selected_method['name']}...")
        print(f"   串口: {selected_port['port']}")
        print(f"   波特率: {selected_port['baudrate']}")
        print(f"   数据格式: {selected_port['data_format']}")
        print(f"   自适应速率匹配: 启用")
        
        time.sleep(1)
        
        # 根据选择启动对应的可视化器
        if method_choice == "1":
            # 启动Open3D可视化器
            print(f"\n🎯 启动自适应Open3D可视化器...")
            import subprocess
            import os
            
            # 设置环境变量传递配置
            env = os.environ.copy()
            env['ADAPTIVE_PORT'] = selected_port['port']
            env['ADAPTIVE_BAUDRATE'] = str(selected_port['baudrate'])
            env['ADAPTIVE_FORMAT'] = selected_port['data_format']
            
            # 启动Open3D可视化器
            subprocess.run([
                sys.executable, 
                "quaternion_3d_visualizer.py"
            ], env=env)
            
        elif method_choice == "2":
            # 启动VPython可视化器
            print(f"\n🎯 启动自适应VPython可视化器...")
            import subprocess
            import os
            
            # 设置环境变量传递配置
            env = os.environ.copy()
            env['ADAPTIVE_PORT'] = selected_port['port']
            env['ADAPTIVE_BAUDRATE'] = str(selected_port['baudrate'])
            env['ADAPTIVE_FORMAT'] = selected_port['data_format']
            
            # 启动VPython可视化器
            subprocess.run([
                sys.executable, 
                "enhanced_vpython_visualizer.py"
            ], env=env)
    
    except KeyboardInterrupt:
        print("\n\n👋 用户取消")
    except Exception as e:
        print(f"\n❌ 启动异常: {e}")
        import traceback
        traceback.print_exc()


def show_adaptive_technology_info():
    """显示自适应技术详细信息"""
    print(f"""
🎯 自适应速率匹配技术详解
========================

🔍 工作原理:
1. 实时监测串口数据接收时间戳
2. 计算平均数据间隔，得出实际传输速率
3. 设置目标渲染速率 = 数据速率 × 2.5倍
4. 根据数据频率动态调整插值参数

⚡ 自适应插值策略:
- 高频数据 (≥200Hz): 插值因子 0.08 (快速响应)
- 中频数据 (≥100Hz): 插值因子 0.12 (平衡模式)  
- 低频数据 (≥50Hz):  插值因子 0.18 (平滑优先)
- 超低频 (<50Hz):    插值因子 0.25 (最大平滑)

🎨 丝滑度优化:
- SLERP四元数球面线性插值
- 智能帧率控制避免过度渲染
- 连续插值确保无卡顿
- 自适应参数每2秒更新一次

🌟 技术优势:
✅ 完美匹配任意数据频率
✅ 自动优化渲染性能
✅ 极致丝滑运动效果
✅ 零配置自动适应
✅ 支持1Hz到1000Hz+的数据速率

按回车键返回主菜单...
""")
    input()


if __name__ == "__main__":
    while True:
        try:
            print("\n" + "="*50)
            choice = input("选择操作: [1] 启动可视化器 [2] 技术详解 [3] 退出: ").strip()
            
            if choice == "1" or choice == "":
                main()
            elif choice == "2":
                show_adaptive_technology_info()
            elif choice == "3":
                print("👋 再见!")
                break
            else:
                print("❌ 无效选择")
                
        except KeyboardInterrupt:
            print("\n👋 再见!")
            break
        except Exception as e:
            print(f"❌ 异常: {e}")
