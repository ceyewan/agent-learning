import asyncio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# 初始化 MCP 客户端，连接到本地的 Stdio 服务器
async def main():
    # 配置服务器参数，指定启动命令和参数
    server_params = StdioServerParameters(
        command="uv",  # 启动服务器的命令
        args=["run", "weather_server.py"],  # 命令参数
    )

    # 通过 stdio_client 连接服务器，获取读写流
    async with stdio_client(server_params) as (read_stream, write_stream):
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