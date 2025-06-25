@echo off
REM 四元数3D可视化系统启动脚本

echo ========================================
echo 四元数3D可视化系统 - USART Trams
echo COM6串口四元数数据3D可视化
echo ========================================
echo.

REM 检查Python
python --version >nul 2>&1
if errorlevel 1 (
    echo 错误: 未找到Python
    echo 请先安装Python 3.8或更高版本
    pause
    exit /b 1
)

REM 检查依赖包
echo 检查依赖包...
python -c "import vpython" 2>nul && echo ✓ VPython 已安装 || echo ✗ VPython 未安装
python -c "import matplotlib" 2>nul && echo ✓ Matplotlib 已安装 || echo ✗ Matplotlib 未安装
python -c "import serial" 2>nul && echo ✓ PySerial 已安装 || echo ✗ PySerial 未安装
python -c "import numpy" 2>nul && echo ✓ NumPy 已安装 || echo ✗ NumPy 未安装

echo.
echo 如果有依赖包未安装，请运行: pip install vpython matplotlib pyserial numpy
echo.

REM 检查串口
echo 检查串口...
python -c "import serial.tools.list_ports; ports = list(serial.tools.list_ports.comports()); print('可用串口:') if ports else print('未检测到串口'); [print(f'  {p.device} - {p.description}') for p in ports]; print('✓ 找到COM6') if any(p.device == 'COM6' for p in ports) else print('⚠ 未找到COM6，请检查设备连接')"

echo.
echo 启动选项:
echo 1. 运行完整测试
echo 2. 启动四元数可视化系统 (COM6)
echo 3. 启动四元数可视化系统 (自定义串口)
echo 4. 查看使用说明
echo 5. 退出
echo.

set /p choice="请选择 (1-5): "

if "%choice%"=="1" (
    echo.
    echo 运行完整测试...
    python test_quaternion_visualizer.py
    pause
) else if "%choice%"=="2" (
    echo.
    echo 启动四元数可视化系统 (COM6)...
    echo 按 Ctrl+C 停止程序
    python quaternion_visualizer.py --port COM6
    pause
) else if "%choice%"=="3" (
    set /p port="请输入串口号 (如 COM3): "
    set /p baudrate="请输入波特率 (默认 115200): "
    if "%baudrate%"=="" set baudrate=115200
    echo.
    echo 启动四元数可视化系统 (%port%, %baudrate%)...
    echo 按 Ctrl+C 停止程序
    python quaternion_visualizer.py --port %port% --baudrate %baudrate%
    pause
) else if "%choice%"=="4" (
    echo.
    python quaternion_visualizer.py --help-usage
    pause
) else if "%choice%"=="5" (
    exit /b 0
) else (
    echo 无效选择
    pause
)

goto :eof
