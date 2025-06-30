from fastmcp import FastMCP

# 初始化 FastMCP 应用，并命名为 "Simple Weather Server"
mcp = FastMCP("Simple Weather Server")

# 定义一个工具函数，用于获取天气信息
@mcp.tool
def get_weather(city :str) -> dict:
    """
    获取指定城市的天气信息。
    参数: city (str): 城市名称
    返回: dict: 包含天气信息的字典
    """
    # 模拟天气数据
    weather_data = {
        "city": city,
        "temperature": "25°C",
        "condition": "晴天"
    }
    return weather_data

if __name__ == "__main__":
    # 启动 FastMCP 服务器。
    # 传输方式 (transport) 决定了客户端与服务器的通信机制。
    
    # 方式一：Stdio (标准输入/输出)
    # mcp.run() 
    
    # 方式二：SSE (Server-Sent Events)，监听于 8080 端口
    mcp.run(transport="sse", port=8080)
