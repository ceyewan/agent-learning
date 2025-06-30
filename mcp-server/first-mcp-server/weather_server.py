from fastmcp import FastMCP

# 初始化 FastMCP 应用，并命名为 "Simple Weather Server"
mcp = FastMCP("Simple Weather Server")

@mcp.tool
def get_coordinates(city: str) -> dict:
    """
    根据城市名称获取其地理坐标（经纬度）。
    
    :param city: 城市名称，例如 "北京"。
    :return: 包含城市名称、纬度和经度的字典。
    """
    # 注意：此处为演示目的，返回硬编码的坐标。
    # 实际应用中应调用地理编码 API。
    return {"city": city, "latitude": 39.9042, "longitude": 116.4074}

@mcp.tool
def get_weather(latitude: float, longitude: float) -> dict:
    """
    根据经纬度坐标获取天气信息。
    
    :param latitude: 纬度。
    :param longitude: 经度。
    :return: 包含天气详情的字典。
    """
    # 注意：此处为演示目的，返回硬编码的天气数据。
    # 实际应用中应调用天气服务 API。
    return {
        "latitude": latitude,
        "longitude": longitude,
        "temperature": 20.0,
        "condition": "Sunny"
    }

if __name__ == "__main__":
    # 启动 FastMCP 服务器。
    # 传输方式 (transport) 决定了客户端与服务器的通信机制。
    
    # 方式一：Stdio (标准输入/输出)
    # mcp.run() 
    
    # 方式二：SSE (Server-Sent Events)，监听于 8080 端口
    mcp.run(transport="sse", port=8080)
