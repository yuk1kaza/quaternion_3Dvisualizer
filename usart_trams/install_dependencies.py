#!/usr/bin/env python3
"""
依赖安装脚本
为新的3D可视化方案安装必要的依赖库
"""

import subprocess
import sys
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def install_package(package_name, description=""):
    """安装Python包"""
    try:
        logger.info(f"正在安装 {package_name}...")
        if description:
            logger.info(f"  用途: {description}")
        
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", package_name],
            capture_output=True,
            text=True,
            check=True
        )
        
        logger.info(f"✅ {package_name} 安装成功")
        return True
        
    except subprocess.CalledProcessError as e:
        logger.error(f"❌ {package_name} 安装失败: {e}")
        logger.error(f"错误输出: {e.stderr}")
        return False


def check_package(package_name):
    """检查包是否已安装"""
    try:
        __import__(package_name)
        return True
    except ImportError:
        return False


def main():
    """主函数"""
    print("""
🔧 3D可视化依赖安装器
====================

将为您安装三种不同的3D可视化方案所需的依赖:

方案1: Open3D + PyQt5 (高性能专业级)
方案2: Pygame + OpenGL (轻量级高性能)  
方案3: Plotly + Dash (Web交互式)

开始安装...
""")
    
    # 定义依赖包
    dependencies = [
        # 方案1: Open3D + PyQt5
        ("open3d", "高性能3D渲染引擎"),
        ("PyQt5", "专业级GUI框架"),
        
        # 方案2: Pygame + OpenGL
        ("pygame", "游戏开发库，用于窗口管理"),
        ("PyOpenGL", "OpenGL Python绑定"),
        ("PyOpenGL_accelerate", "OpenGL加速库"),
        
        # 方案3: Plotly + Dash
        ("plotly", "高质量交互式图形库"),
        ("dash", "Web应用框架"),
        ("dash-bootstrap-components", "Bootstrap组件库"),
        
        # 通用依赖
        ("numpy", "数值计算库"),
        ("scipy", "科学计算库")
    ]
    
    # 检查并安装依赖
    installed_count = 0
    failed_count = 0
    
    for package, description in dependencies:
        # 检查是否已安装
        package_check = package.replace("-", "_").replace("PyQt5", "PyQt5.QtCore")
        
        if package == "PyOpenGL_accelerate":
            package_check = "OpenGL_accelerate"
        elif package == "dash-bootstrap-components":
            package_check = "dash_bootstrap_components"
        
        if check_package(package_check.split('.')[0]):
            logger.info(f"✅ {package} 已安装")
            installed_count += 1
        else:
            if install_package(package, description):
                installed_count += 1
            else:
                failed_count += 1
    
    print(f"\n" + "="*50)
    print("📊 安装结果统计")
    print("="*50)
    print(f"总计包数: {len(dependencies)}")
    print(f"安装成功: {installed_count}")
    print(f"安装失败: {failed_count}")
    
    if failed_count == 0:
        print(f"""
✅ 所有依赖安装完成！

现在您可以选择运行以下任一可视化方案:

🏆 方案1 - Open3D + PyQt5 (推荐):
   python advanced_3d_visualizer.py
   
   特点:
   - 最高性能3D渲染
   - 专业级用户界面
   - 最佳交互体验
   - 适合专业应用

⚡ 方案2 - Pygame + OpenGL:
   python opengl_3d_visualizer.py
   
   特点:
   - 轻量级实现
   - 极速响应
   - 游戏级性能
   - 适合高频率更新

🌐 方案3 - Plotly + Dash:
   python web_3d_visualizer.py
   
   特点:
   - 基于Web界面
   - 跨平台兼容
   - 移动设备支持
   - 适合远程访问

建议优先尝试方案1，它提供最佳的整体体验！
""")
    else:
        print(f"""
⚠️  部分依赖安装失败

您可以手动安装失败的包:
pip install <包名>

或者尝试使用conda:
conda install <包名>

安装完成后即可运行相应的可视化方案。
""")
    
    print("\n按任意键退出...")
    input()


if __name__ == "__main__":
    main()
