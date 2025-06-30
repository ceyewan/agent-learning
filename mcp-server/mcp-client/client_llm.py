import asyncio
import os
import json
import litellm
import warnings
from dataclasses import dataclass
from typing import Any, Dict, List

from dotenv import load_dotenv
from mcp import ClientSession
from mcp.client.sse import sse_client

warnings.filterwarnings("ignore")
load_dotenv()

@dataclass
class Config:
    """配置类"""
    model: str = "openai/qwen-plus-latest"
    server_sse_url: str = "http://127.0.0.1:8080/sse/"
    base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    api_key: str = os.getenv("QWEN_API_KEY", "")

class MCPToolsManager:
    """MCP 工具管理器"""
    
    def __init__(self, session: ClientSession):
        self.session = session
    
    async def get_tools_list(self) -> List[Dict[str, Any]]:
        """获取 MCP 工具，并转换为 Litellm/OpenAI function 格式"""
        try:
            tools_result = await self.session.list_tools()
            self._print_available_tools(tools_result.tools)
            
            formatted_tools = []
            for tool in tools_result.tools:
                formatted_tools.append({
                    "type": "function",
                    "function": {
                        "name": tool.name,
                        "description": tool.description,
                        "parameters": tool.inputSchema
                    }
                })
            return formatted_tools
        except Exception as e:
            print(f"获取工具列表失败: {e}")
            return []
    
    def _print_available_tools(self, tools) -> None:
        """打印可用工具列表"""
        print("已连接服务器，工具列表:")
        for tool in tools:
            print(f"  • {tool.name}: {tool.description}")
    
    async def execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> str:
        """执行 MCP 工具"""
        try:
            result = await self.session.call_tool(tool_name, arguments=arguments)
            # 安全地提取工具输出内容
            if result.content and len(result.content) > 0:
                content = result.content[0]
                return getattr(content, "text", str(content))
            return "工具执行成功，但无返回内容"
        except Exception as e:
            return f"工具执行失败: {str(e)}"

class ToolCallHandler:
    """工具调用处理器"""
    
    def __init__(self, tools_manager: MCPToolsManager):
        self.tools_manager = tools_manager
    
    def extract_tool_call_info(self, tool_call) -> tuple[str, Dict[str, Any], str]:
        """安全地提取工具调用信息"""
        # 提取工具名称
        tool_name = ""
        if hasattr(tool_call, "function") and tool_call.function:
            tool_name = tool_call.function.name
            raw_args = tool_call.function.arguments
        else:
            tool_name = getattr(tool_call, "name", "")
            raw_args = getattr(tool_call, "arguments", "{}")
        
        # 解析参数
        try:
            if isinstance(raw_args, str):
                parsed_args = json.loads(raw_args)
            else:
                parsed_args = raw_args if isinstance(raw_args, dict) else {}
        except json.JSONDecodeError:
            print(f"警告: 无法解析工具参数 {raw_args}，使用空字典")
            parsed_args = {}
        
        # 提取工具调用ID
        tool_call_id = getattr(tool_call, "id", f"call_{tool_name}")
        
        return tool_name, parsed_args, tool_call_id
    
    def get_user_permission(self, tool_name: str, args: Dict[str, Any]) -> bool:
        """获取用户执行工具的权限"""
        print(f"\n助手请求工具: {tool_name}({args})")
        while True:
            permission = input("允许执行该工具吗？(y/n): ").strip().lower()
            if permission in ['y', 'yes']:
                return True
            elif permission in ['n', 'no']:
                return False
            else:
                print("请输入 y 或 n")
    
    async def process_tool_calls(self, tool_calls: List, messages: List[Dict[str, Any]]) -> None:
        """处理所有工具调用"""
        for tool_call in tool_calls:
            tool_name, parsed_args, tool_call_id = self.extract_tool_call_info(tool_call)
            
            if not tool_name:
                print("警告: 无法提取工具名称，跳过此工具调用")
                continue
            
            # 获取用户权限
            if self.get_user_permission(tool_name, parsed_args):
                # 执行工具
                tool_output = await self.tools_manager.execute_tool(tool_name, parsed_args)
                print(f"→ {tool_name} 返回: {tool_output}")
                
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call_id,
                    "content": tool_output,
                })
            else:
                # 用户拒绝执行
                denied_msg = f"[用户拒绝执行工具 '{tool_name}']"
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call_id,
                    "content": denied_msg,
                })
                print(f"→ 跳过 {tool_name}")

class QueryProcessor:
    """查询处理器"""
    
    def __init__(self, config: Config, tools_manager: MCPToolsManager):
        self.config = config
        self.tools_manager = tools_manager
        self.tool_handler = ToolCallHandler(tools_manager)
    
    async def process_query(self, query: str) -> str:
        """处理用户查询，自动调用工具并返回最终回复"""
        tools = await self.tools_manager.get_tools_list()
        
        if not tools:
            return "抱歉，无法获取可用工具，请检查 MCP 服务器连接"
        
        # 第一次调用：让 LLM 判断是否需要调用工具
        try:
            first_response = await self._call_llm(
                messages=[{"role": "user", "content": query}],
                tools=tools,
                tool_choice="auto"
            )
        except Exception as e:
            return f"调用 LLM 失败: {str(e)}"
        
        assistant_message = first_response.choices[0].message
        messages = [
            {"role": "user", "content": query},
            assistant_message.model_dump() if hasattr(assistant_message, 'model_dump') else assistant_message
        ]
        
        # 检查是否需要调用工具
        tool_calls = getattr(assistant_message, 'tool_calls', None)
        if tool_calls:
            # 确保 tool_calls 是列表
            if not isinstance(tool_calls, list):
                tool_calls = [tool_calls]
            
            # 处理工具调用
            await self.tool_handler.process_tool_calls(tool_calls, messages)
            
            # 第二次调用：生成最终回复
            try:
                second_response = await self._call_llm(
                    messages=messages,
                    tools=tools,
                    tool_choice="none"
                )
                return second_response.choices[0].message.content.strip()
            except Exception as e:
                return f"生成最终回复失败: {str(e)}"
        else:
            # 不需要工具，直接返回助手回复
            content = getattr(assistant_message, 'content', '')
            return content.strip() if content else "抱歉，我无法理解您的问题"
    
    async def _call_llm(self, messages: List[Dict[str, Any]], tools: List[Dict[str, Any]], 
                       tool_choice: str) -> Any:
        """调用 LLM API"""
        return await litellm.acompletion(
            base_url=self.config.base_url,
            api_key=self.config.api_key,
            model=self.config.model,
            messages=messages,
            tools=tools,
            tool_choice=tool_choice,
        )

async def main():
    """主程序入口"""
    config = Config()
    
    if not config.api_key:
        print("错误: 未找到 QWEN_API_KEY 环境变量")
        return
    
    # 建立 SSE 连接
    async with sse_client(url=config.server_sse_url) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as mcp_session:
            # 初始化 MCP 连接
            await mcp_session.initialize()
            
            # 创建管理器和处理器
            tools_manager = MCPToolsManager(mcp_session)
            query_processor = QueryProcessor(config, tools_manager)
            
            # 示例查询
            query = "北京的天气怎么样？"
            print(f"\n用户提问: {query}")
            
            response = await query_processor.process_query(query)
            print(f"\n最终回复: {response}")
                

if __name__ == "__main__":
    asyncio.run(main())
