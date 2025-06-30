#!/usr/bin/env python3
"""
MCP Server Proxy using standard MCP protocol
聚合多个MCP服务器的工具，提供统一的代理访问
"""

import asyncio
import json
import subprocess
from typing import Dict, List, Any, Optional
from fastmcp import FastMCP
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 初始化代理MCP服务器
mcp = FastMCP("mcp-proxy")


class MCPProxy:
    def __init__(self):
        self.servers: Dict[str, Dict] = {}
        # tool_name -> server_name mapping
        self.tools_registry: Dict[str, str] = {}
        # 缓存客户端会话
        self.sessions: Dict[str, ClientSession] = {}

    async def register_server(self, name: str, server_command: List[str]):
        """
        注册一个MCP服务器

        Args:
            name: 服务器名称
            server_command: 启动服务器的命令列表，如 ['python', 'sin_server.py']
        """
        server_info = {
            "name": name,
            "command": server_command,
            "tools": []
        }

        try:
            # 使用标准 MCP 客户端连接
            server_params = StdioServerParameters(
                command=server_command[0],
                args=server_command[1:] if len(server_command) > 1 else []
            )

            async with stdio_client(server_params) as (read, write):
                async with ClientSession(read, write) as session:
                    # 初始化会话
                    await session.initialize()

                    # 获取服务器的工具列表
                    tools_response = await session.list_tools()
                    server_info["tools"] = tools_response.tools

                    # 注册工具到代理
                    for tool in server_info["tools"]:
                        tool_name = tool.name
                        if tool_name:
                            # 如果工具名冲突，添加服务器前缀
                            if tool_name in self.tools_registry:
                                prefixed_name = f"{name}_{tool_name}"
                                self.tools_registry[prefixed_name] = name
                                logger.warning(
                                    f"工具名冲突: {tool_name}，使用前缀名: {prefixed_name}")
                            else:
                                self.tools_registry[tool_name] = name

                    self.servers[name] = server_info
                    logger.info(
                        f"成功注册服务器: {name}，工具数量: {len(server_info['tools'])}")

        except Exception as e:
            logger.error(f"注册服务器 {name} 时出错: {e}")

    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """调用指定工具"""
        if tool_name not in self.tools_registry:
            raise ValueError(f"未找到工具: {tool_name}")

        server_name = self.tools_registry[tool_name]
        server_info = self.servers[server_name]

        try:
            # 创建新的连接来调用工具
            server_params = StdioServerParameters(
                command=server_info["command"][0],
                args=server_info["command"][1:] if len(
                    server_info["command"]) > 1 else []
            )

            async with stdio_client(server_params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()

                    # 调用工具
                    result = await session.call_tool(tool_name, arguments)
                    return result.content

        except Exception as e:
            logger.error(f"调用工具 {tool_name} 时出错: {e}")
            raise

    def get_all_tools(self) -> List[Dict]:
        """获取所有聚合的工具列表"""
        all_tools = []
        for server_name, server_info in self.servers.items():
            for tool in server_info["tools"]:
                tool_dict = {
                    "name": tool.name,
                    "description": tool.description,
                    "server": server_name
                }
                # 添加参数信息
                if hasattr(tool, 'inputSchema'):
                    tool_dict["inputSchema"] = tool.inputSchema
                all_tools.append(tool_dict)
        return all_tools


# 创建代理实例
proxy = MCPProxy()


@mcp.tool()
async def list_servers() -> Dict[str, Any]:
    """
    列出所有已注册的MCP服务器及其工具信息

    Returns:
        包含所有服务器信息的字典
    """
    servers_info = {}
    for name, info in proxy.servers.items():
        servers_info[name] = {
            "command": info["command"],
            "tools_count": len(info["tools"]),
            "tools": [tool.name for tool in info["tools"]]
        }
    return {
        "total_servers": len(proxy.servers),
        "total_tools": len(proxy.tools_registry),
        "servers": servers_info
    }


@mcp.tool()
async def list_all_tools() -> Dict[str, Any]:
    """
    列出所有可用的工具

    Returns:
        所有工具的详细信息
    """
    return {
        "tools": proxy.get_all_tools(),
        "total_count": len(proxy.tools_registry)
    }


# 动态生成代理工具
async def create_proxy_tools():
    """为每个注册的工具创建代理函数"""
    for tool_name, server_name in proxy.tools_registry.items():
        # 为每个工具创建代理函数
        async def proxy_tool_func(*args, tool_name=tool_name, **kwargs):
            return await proxy.call_tool(tool_name, kwargs)

        # 获取原始工具信息
        server_info = proxy.servers[server_name]
        original_tool = None
        for tool in server_info["tools"]:
            if tool.name == tool_name:
                original_tool = tool
                break

        if original_tool:
            # 注册代理工具到 FastMCP
            mcp.tool(
                name=tool_name,
                description=f"[来自{server_name}] {original_tool.description}"
            )(proxy_tool_func)


async def setup_proxy():
    """设置代理服务器，注册所有后端服务器"""
    # 配置要连接的服务器列表 - 使用标准 MCP 协议
    servers_config = [
        {"name": "sin-server", "command": ["python", "sin_server.py"]},
        {"name": "cos-server", "command": ["python", "cos_server.py"]},
        {"name": "tan-server", "command": ["python", "tan_server.py"]},
    ]

    logger.info("开始注册MCP服务器...")

    # 注册所有服务器
    for config in servers_config:
        await proxy.register_server(
            config["name"],
            config["command"]
        )

    # 创建代理工具
    await create_proxy_tools()

    logger.info(
        f"代理设置完成。已注册 {len(proxy.servers)} 个服务器，{len(proxy.tools_registry)} 个工具")


if __name__ == "__main__":
    async def main():
        try:
            # 设置代理
            await setup_proxy()

            # 启动代理服务器
            logger.info("启动MCP代理服务器...")
            mcp.run()  # 移除 transport 参数，使用默认的 stdio

        except KeyboardInterrupt:
            logger.info("收到中断信号，正在关闭...")

    # 运行主程序
    asyncio.run(main())
