#!/usr/bin/env python3
"""
USART Trams 安装脚本
"""

from setuptools import setup, find_packages
import os

# 读取README文件
def read_readme():
    with open("README.md", "r", encoding="utf-8") as f:
        return f.read()

# 读取requirements文件
def read_requirements():
    with open("requirements.txt", "r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip() and not line.startswith("#")]

setup(
    name="usart-trams",
    version="1.0.0",
    description="高性能串口数据处理和可视化系统",
    long_description=read_readme(),
    long_description_content_type="text/markdown",
    author="USART Trams Team",
    author_email="support@usart-trams.com",
    url="https://github.com/usart-trams/usart-trams",
    packages=find_packages(),
    include_package_data=True,
    install_requires=read_requirements(),
    python_requires=">=3.8",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Scientific/Engineering",
        "Topic :: System :: Hardware :: Hardware Drivers",
        "Topic :: Communications",
    ],
    keywords="serial uart data processing visualization real-time",
    entry_points={
        "console_scripts": [
            "usart-trams=main:main",
            "usart-benchmark=tools.benchmark:main",
        ],
    },
    project_urls={
        "Bug Reports": "https://github.com/usart-trams/usart-trams/issues",
        "Source": "https://github.com/usart-trams/usart-trams",
        "Documentation": "https://usart-trams.readthedocs.io/",
    },
)
