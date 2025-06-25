@echo off
REM USART Trams Windows 安装脚本

echo ========================================
echo USART Trams 高性能串口数据处理系统
echo 安装脚本 v1.0
echo ========================================
echo.

REM 检查Python版本
python --version >nul 2>&1
if errorlevel 1 (
    echo 错误: 未找到Python，请先安装Python 3.8或更高版本
    echo 下载地址: https://www.python.org/downloads/
    pause
    exit /b 1
)

echo 检查Python版本...
for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo 当前Python版本: %PYTHON_VERSION%

REM 检查pip
pip --version >nul 2>&1
if errorlevel 1 (
    echo 错误: 未找到pip，请确保pip已正确安装
    pause
    exit /b 1
)

echo.
echo 开始安装依赖包...
echo ========================================

REM 升级pip
echo 升级pip...
python -m pip install --upgrade pip

REM 安装依赖
echo.
echo 安装项目依赖...
pip install -r requirements.txt

if errorlevel 1 (
    echo.
    echo 警告: 某些依赖包安装失败
    echo 这可能是由于网络问题或系统环境问题
    echo 请检查错误信息并手动安装失败的包
    echo.
)

REM 检查关键依赖
echo.
echo 检查关键依赖包...
python -c "import serial; print('✓ pyserial 已安装')" 2>nul || echo "✗ pyserial 安装失败"
python -c "import numpy; print('✓ numpy 已安装')" 2>nul || echo "✗ numpy 安装失败"
python -c "import vispy; print('✓ vispy 已安装')" 2>nul || echo "✗ vispy 安装失败"
python -c "import asyncio; print('✓ asyncio 可用')" 2>nul || echo "✗ asyncio 不可用"

echo.
echo ========================================
echo 安装完成！
echo ========================================
echo.

REM 创建启动脚本
echo 创建启动脚本...
echo @echo off > run.bat
echo echo 启动 USART Trams... >> run.bat
echo python main.py %%* >> run.bat
echo pause >> run.bat

echo 创建基准测试脚本...
echo @echo off > benchmark.bat
echo echo 运行性能基准测试... >> benchmark.bat
echo python tools/benchmark.py %%* >> benchmark.bat
echo pause >> benchmark.bat

echo.
echo 使用说明:
echo ========================================
echo 1. 运行程序: 双击 run.bat 或执行 "python main.py"
echo 2. 性能测试: 双击 benchmark.bat 或执行 "python tools/benchmark.py"
echo 3. 配置文件: 编辑 config.json 来调整设置
echo 4. 查看日志: 程序运行后会生成 usart_trams.log 日志文件
echo.
echo 快捷键:
echo - R: 重置视图
echo - C: 清空数据  
echo - S: 保存截图
echo - Q/ESC: 退出程序
echo.

REM 检查串口
echo 检测可用串口...
python -c "import serial.tools.list_ports; ports = list(serial.tools.list_ports.comports()); print('可用串口:') if ports else print('未检测到串口'); [print(f'  {p.device} - {p.description}') for p in ports]"

echo.
echo 安装完成！按任意键退出...
pause >nul
