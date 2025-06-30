import asyncio
import time
from mcp import ClientSession
from mcp.client.sse import sse_client

# 初始化 MCP 客户端，连接到远程的 SSE 服务器
async def main():
    # 通过 sse_client 连接服务器，获取读写流
    async with sse_client("http://127.0.0.1:8000/sse/") as (read_stream, write_stream):
        # 创建客户端会话
        async with ClientSession(read_stream, write_stream) as session:
            # 初始化会话，完成握手
            await session.initialize()

            # 获取并打印可用工具列表
            tools_result = await session.list_tools()
            print("可用工具:")
            for tool in tools_result.tools:
                print(f"  - {tool.name}: {tool.description}\n{tool.inputSchema}")
                print("=" * 40)

            # 示例：调用工具获取城市坐标
            result = await session.call_tool("get_coordinates", arguments={"city": "beijing"})
            content0 = result.content[0]
            print(f"获取坐标结果: {getattr(content0, 'text', content0)}")

# 程序入口
if __name__ == "__main__":
    asyncio.run(main())