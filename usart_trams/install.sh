#!/bin/bash

# USART Trams Linux/macOS 安装脚本

echo "========================================"
echo "USART Trams 高性能串口数据处理系统"
echo "安装脚本 v1.0"
echo "========================================"
echo

# 检查Python版本
if ! command -v python3 &> /dev/null; then
    echo "错误: 未找到Python3，请先安装Python 3.8或更高版本"
    exit 1
fi

echo "检查Python版本..."
PYTHON_VERSION=$(python3 --version 2>&1 | cut -d' ' -f2)
echo "当前Python版本: $PYTHON_VERSION"

# 检查pip
if ! command -v pip3 &> /dev/null; then
    echo "错误: 未找到pip3，请确保pip已正确安装"
    exit 1
fi

echo
echo "开始安装依赖包..."
echo "========================================"

# 升级pip
echo "升级pip..."
python3 -m pip install --upgrade pip

# 创建虚拟环境（可选）
read -p "是否创建虚拟环境? (y/n): " create_venv
if [[ $create_venv == "y" || $create_venv == "Y" ]]; then
    echo "创建虚拟环境..."
    python3 -m venv .venv
    
    echo "激活虚拟环境..."
    source .venv/bin/activate
    
    echo "虚拟环境已创建并激活"
    echo "要手动激活虚拟环境，请运行: source .venv/bin/activate"
fi

# 安装依赖
echo
echo "安装项目依赖..."
pip3 install -r requirements.txt

if [ $? -ne 0 ]; then
    echo
    echo "警告: 某些依赖包安装失败"
    echo "这可能是由于网络问题或系统环境问题"
    echo "请检查错误信息并手动安装失败的包"
    echo
fi

# 检查关键依赖
echo
echo "检查关键依赖包..."
python3 -c "import serial; print('✓ pyserial 已安装')" 2>/dev/null || echo "✗ pyserial 安装失败"
python3 -c "import numpy; print('✓ numpy 已安装')" 2>/dev/null || echo "✗ numpy 安装失败"
python3 -c "import vispy; print('✓ vispy 已安装')" 2>/dev/null || echo "✗ vispy 安装失败"
python3 -c "import asyncio; print('✓ asyncio 可用')" 2>/dev/null || echo "✗ asyncio 不可用"

echo
echo "========================================"
echo "安装完成！"
echo "========================================"
echo

# 创建启动脚本
echo "创建启动脚本..."
cat > run.sh << 'EOF'
#!/bin/bash
echo "启动 USART Trams..."

# 如果存在虚拟环境，自动激活
if [ -d ".venv" ]; then
    source .venv/bin/activate
fi

python3 main.py "$@"
EOF

chmod +x run.sh

# 创建基准测试脚本
echo "创建基准测试脚本..."
cat > benchmark.sh << 'EOF'
#!/bin/bash
echo "运行性能基准测试..."

# 如果存在虚拟环境，自动激活
if [ -d ".venv" ]; then
    source .venv/bin/activate
fi

python3 tools/benchmark.py "$@"
EOF

chmod +x benchmark.sh

echo
echo "使用说明:"
echo "========================================"
echo "1. 运行程序: ./run.sh 或 python3 main.py"
echo "2. 性能测试: ./benchmark.sh 或 python3 tools/benchmark.py"
echo "3. 配置文件: 编辑 config.json 来调整设置"
echo "4. 查看日志: 程序运行后会生成 usart_trams.log 日志文件"
echo
echo "快捷键:"
echo "- R: 重置视图"
echo "- C: 清空数据"
echo "- S: 保存截图"
echo "- Q/ESC: 退出程序"
echo

# 检查串口
echo "检测可用串口..."
python3 -c "
import serial.tools.list_ports
ports = list(serial.tools.list_ports.comports())
if ports:
    print('可用串口:')
    for p in ports:
        print(f'  {p.device} - {p.description}')
else:
    print('未检测到串口')
    print('常见Linux串口设备: /dev/ttyUSB0, /dev/ttyACM0')
    print('常见macOS串口设备: /dev/cu.usbserial-*')
"

echo
echo "安装完成！"

# 如果创建了虚拟环境，提醒用户
if [[ $create_venv == "y" || $create_venv == "Y" ]]; then
    echo
    echo "注意: 已创建虚拟环境"
    echo "下次运行前请先激活虚拟环境: source .venv/bin/activate"
    echo "或直接使用提供的脚本: ./run.sh"
fi
