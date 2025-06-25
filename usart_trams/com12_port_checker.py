#!/usr/bin/env python3
"""
串口检查工具
检查串口状态并解决访问问题，支持COM6/COM12等
"""

import serial
import serial.tools.list_ports
import time
import sys
import subprocess
import os

class COM12PortChecker:
    """COM12端口检查器"""
    
    def __init__(self):
        self.target_port = "COM12"
    
    def list_all_ports(self):
        """列出所有可用端口"""
        print("🔍 扫描所有串口...")
        
        ports = serial.tools.list_ports.comports()
        
        if not ports:
            print("❌ 未发现任何串口")
            return []
        
        print(f"✅ 发现 {len(ports)} 个串口:")
        
        available_ports = []
        for port in ports:
            print(f"   {port.device}: {port.description}")
            if port.hwid:
                print(f"      硬件ID: {port.hwid}")
            if port.manufacturer:
                print(f"      制造商: {port.manufacturer}")
            
            available_ports.append(port.device)
        
        return available_ports
    
    def check_port_access(self, port_name, baudrate=128000):
        """检查端口访问权限"""
        print(f"\n🔐 检查 {port_name} 访问权限...")
        
        try:
            # 尝试打开端口
            ser = serial.Serial(
                port=port_name,
                baudrate=baudrate,
                timeout=1.0
            )
            
            print(f"✅ {port_name} 访问成功")
            print(f"   波特率: {ser.baudrate}")
            print(f"   超时: {ser.timeout}")
            print(f"   是否打开: {ser.is_open}")
            
            # 尝试读写测试
            ser.reset_input_buffer()
            ser.reset_output_buffer()
            
            # 检查缓冲区
            waiting = ser.in_waiting
            print(f"   输入缓冲区: {waiting} 字节")
            
            ser.close()
            return True
            
        except PermissionError as e:
            print(f"❌ {port_name} 权限错误: {e}")
            print(f"   错误代码: {e.errno}")
            print(f"   可能原因:")
            print(f"   1. 端口被其他程序占用")
            print(f"   2. 需要管理员权限")
            print(f"   3. 设备驱动问题")
            return False
            
        except serial.SerialException as e:
            print(f"❌ {port_name} 串口错误: {e}")
            return False
            
        except Exception as e:
            print(f"❌ {port_name} 未知错误: {e}")
            return False
    
    def find_processes_using_port(self, port_name):
        """查找占用端口的进程"""
        print(f"\n🔍 查找占用 {port_name} 的进程...")
        
        try:
            # 使用wmic查找占用串口的进程
            cmd = f'wmic process where "CommandLine like \'%{port_name}%\'" get ProcessId,Name,CommandLine /format:csv'
            
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0 and result.stdout:
                lines = result.stdout.strip().split('\n')
                processes_found = False
                
                for line in lines[1:]:  # 跳过标题行
                    if line.strip() and port_name.lower() in line.lower():
                        processes_found = True
                        parts = line.split(',')
                        if len(parts) >= 3:
                            print(f"   进程: {parts[1]} (PID: {parts[2]})")
                            print(f"   命令行: {parts[0]}")
                
                if not processes_found:
                    print(f"   未发现明确占用 {port_name} 的进程")
            else:
                print(f"   无法查询进程信息")
                
        except Exception as e:
            print(f"   查询进程失败: {e}")
    
    def try_different_baudrates(self, port_name):
        """尝试不同波特率"""
        print(f"\n⚡ 测试 {port_name} 不同波特率...")
        
        baudrates = [9600, 19200, 38400, 57600, 115200, 128000, 230400, 460800, 921600]
        
        working_baudrates = []
        
        for baudrate in baudrates:
            try:
                ser = serial.Serial(
                    port=port_name,
                    baudrate=baudrate,
                    timeout=0.5
                )
                
                print(f"   ✅ {baudrate}: 成功")
                working_baudrates.append(baudrate)
                
                # 快速检查是否有数据
                time.sleep(0.1)
                if ser.in_waiting > 0:
                    data = ser.read(ser.in_waiting)
                    print(f"      检测到数据: {len(data)} 字节")
                
                ser.close()
                
            except Exception as e:
                print(f"   ❌ {baudrate}: {type(e).__name__}")
        
        return working_baudrates
    
    def suggest_solutions(self):
        """建议解决方案"""
        print(f"\n💡 解决 COM12 访问问题的建议:")
        print(f"="*50)
        
        print(f"1. 🔒 检查端口占用:")
        print(f"   - 关闭可能使用COM12的程序")
        print(f"   - 检查设备管理器中的串口状态")
        print(f"   - 重启相关设备")
        
        print(f"\n2. 👑 管理员权限:")
        print(f"   - 以管理员身份运行PowerShell")
        print(f"   - 右键点击PowerShell -> 以管理员身份运行")
        
        print(f"\n3. 🔧 设备管理器检查:")
        print(f"   - Win+X -> 设备管理器")
        print(f"   - 展开 '端口(COM和LPT)'")
        print(f"   - 查看COM12状态")
        print(f"   - 如有黄色感叹号，右键更新驱动")
        
        print(f"\n4. 🔄 重置端口:")
        print(f"   - 设备管理器中禁用COM12")
        print(f"   - 等待5秒后重新启用")
        
        print(f"\n5. 🔌 硬件检查:")
        print(f"   - 重新插拔USB连接")
        print(f"   - 检查设备电源")
        print(f"   - 尝试不同的USB端口")
    
    def run_full_check(self):
        """运行完整检查"""
        print(f"""
🔧 COM12端口诊断工具
===================

目标: 解决COM12端口访问问题

检查项目:
1. 扫描所有串口
2. 检查COM12访问权限
3. 查找占用进程
4. 测试不同波特率
5. 提供解决建议

开始检查...
""")
        
        # 步骤1: 扫描所有端口
        print("\n" + "="*50)
        print("步骤1: 扫描所有串口")
        print("="*50)
        
        available_ports = self.list_all_ports()
        
        if self.target_port not in available_ports:
            print(f"\n❌ {self.target_port} 不在可用端口列表中")
            print(f"   可能原因:")
            print(f"   1. 设备未连接")
            print(f"   2. 驱动未安装")
            print(f"   3. 硬件故障")
            self.suggest_solutions()
            return
        
        # 步骤2: 检查访问权限
        print("\n" + "="*50)
        print("步骤2: 检查访问权限")
        print("="*50)
        
        access_ok = self.check_port_access(self.target_port, 128000)
        
        if not access_ok:
            # 步骤3: 查找占用进程
            print("\n" + "="*50)
            print("步骤3: 查找占用进程")
            print("="*50)
            
            self.find_processes_using_port(self.target_port)
            
            # 步骤4: 尝试不同波特率
            print("\n" + "="*50)
            print("步骤4: 测试不同波特率")
            print("="*50)
            
            working_baudrates = self.try_different_baudrates(self.target_port)
            
            if working_baudrates:
                print(f"\n✅ 以下波特率可以访问:")
                for br in working_baudrates:
                    print(f"   {br}")
            
            # 步骤5: 解决建议
            print("\n" + "="*50)
            print("步骤5: 解决建议")
            print("="*50)
            
            self.suggest_solutions()
        
        else:
            print(f"\n✅ {self.target_port} 访问正常!")
            print(f"   可以正常使用128000波特率")
            print(f"   建议重新运行可视化程序")


def main():
    """主函数"""
    try:
        checker = COM12PortChecker()
        checker.run_full_check()
        
    except Exception as e:
        print(f"❌ 检查工具异常: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
