#!/usr/bin/env python3
"""
启动所有数学代理服务器的脚本
"""
import subprocess
import sys
import time
import os


def start_agent(script_name, port):
    """启动单个代理"""
    print(f"启动 {script_name} 在端口 {port}...")
    try:
        process = subprocess.Popen([
            sys.executable, script_name
        ], cwd=os.path.dirname(__file__))
        return process
    except Exception as e:
        print(f"启动 {script_name} 失败: {e}")
        return None


def main():
    print("启动数学代理网络...")

    agents = [
        ("sine_agent.py", 4737),
        ("cosine_agent.py", 4738),
        ("tangent_agent.py", 4739)
    ]

    processes = []

    for script, port in agents:
        process = start_agent(script, port)
        if process:
            processes.append((script, process))
            time.sleep(1)  # 等待1秒再启动下一个

    print(f"\n成功启动了 {len(processes)} 个代理服务器")
    print("服务器状态:")
    for script, process in processes:
        print(f"  {script}: PID {process.pid}")

    print("\n所有代理服务器已启动！")
    print("现在你可以运行 client.py 来测试系统")
    print("按 Ctrl+C 来停止所有服务器")

    try:
        # 等待所有进程
        for script, process in processes:
            process.wait()
    except KeyboardInterrupt:
        print("\n正在停止所有代理服务器...")
        for script, process in processes:
            process.terminate()
            print(f"已停止 {script}")


if __name__ == "__main__":
    main()
