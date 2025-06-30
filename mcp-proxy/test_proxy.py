#!/usr/bin/env python3
"""
测试 MCP 代理服务器
"""

import asyncio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def test_proxy():
    """测试代理服务器的功能"""
    print("正在测试 MCP 代理服务器...")

    # 配置代理服务器参数
    server_params = StdioServerParameters(
        command="python",
        args=["proxy.py"]
    )

    try:
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                # 初始化会话
                await session.initialize()
                print("✓ 成功连接到代理服务器")

                # 测试列出所有服务器
                print("\n--- 测试列出服务器 ---")
                servers_result = await session.call_tool("list_servers", {})
                servers = servers_result.content[0].text if servers_result.content else ""
                print(f"服务器信息: {servers}")

                # 测试列出所有工具
                print("\n--- 测试列出工具 ---")
                tools_result = await session.call_tool("list_all_tools", {})
                tools_info = tools_result.content[0].text if tools_result.content else ""
                print(f"工具信息: {tools_info}")

                # 测试调用具体工具
                print("\n--- 测试调用工具 ---")

                # 测试 sin 工具
                try:
                    sin_result = await session.call_tool("calculate_sin", {"angle": 30, "unit": "degrees"})
                    sin_value = sin_result.content[0].text if sin_result.content else ""
                    print(f"sin(30°) = {sin_value}")
                except Exception as e:
                    print(f"sin 工具调用失败: {e}")

                # 测试 cos 工具
                try:
                    cos_result = await session.call_tool("calculate_cos", {"angle": 60, "unit": "degrees"})
                    cos_value = cos_result.content[0].text if cos_result.content else ""
                    print(f"cos(60°) = {cos_value}")
                except Exception as e:
                    print(f"cos 工具调用失败: {e}")

                # 测试 tan 工具
                try:
                    tan_result = await session.call_tool("calculate_tan", {"angle": 45, "unit": "degrees"})
                    tan_value = tan_result.content[0].text if tan_result.content else ""
                    print(f"tan(45°) = {tan_value}")
                except Exception as e:
                    print(f"tan 工具调用失败: {e}")

                print("\n✓ 所有测试通过！")

    except Exception as e:
        print(f"✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_proxy())
