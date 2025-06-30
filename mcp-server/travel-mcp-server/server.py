from fastmcp import FastMCP

# 初始化 FastMCP 应用
mcp = FastMCP("Smart Travel Assistant")

# 模拟城市数据库
CITY_DATABASE = {
    "北京": {
        "coordinates": "39.9042°N, 116.4074°E",
        "population": "2154万",
        "attractions": ["故宫", "长城", "天坛", "颐和园"],
        "cuisine": ["北京烤鸭", "炸酱面", "豆汁"],
        "best_season": "春秋季",
        "description": "中国首都，历史文化名城"
    },
    "上海": {
        "coordinates": "31.2304°N, 121.4737°E",
        "population": "2489万",
        "attractions": ["外滩", "东方明珠", "豫园", "南京路"],
        "cuisine": ["小笼包", "生煎包", "白切鸡"],
        "best_season": "春秋季",
        "description": "国际化大都市，经济金融中心"
    },
    "杭州": {
        "coordinates": "30.2741°N, 120.1551°E",
        "population": "1220万",
        "attractions": ["西湖", "灵隐寺", "千岛湖", "宋城"],
        "cuisine": ["西湖醋鱼", "东坡肉", "龙井虾仁"],
        "best_season": "春季和秋季",
        "description": "人间天堂，风景如画的旅游城市"
    }
}


# =========================== RESOURCES ===========================
@mcp.resource("file://city/{city_name}")
def get_city_info(city_name: str) -> str:
    """
    获取城市的详细信息资源
    参数: city_name (str): 城市名称
    返回: str: 城市详细信息的JSON格式字符串
    """
    if city_name in CITY_DATABASE:
        city_data = CITY_DATABASE[city_name]
        return f"""# {city_name} 城市信息

                    ## 基本信息
                    - **坐标**: {city_data['coordinates']}
                    - **人口**: {city_data['population']}
                    - **最佳旅游季节**: {city_data['best_season']}
                    - **城市特色**: {city_data['description']}

                    ## 热门景点
                    {' | '.join(city_data['attractions'])}

                    ## 特色美食  
                    {' | '.join(city_data['cuisine'])}
                """
    else:
        return f"抱歉，暂无 {city_name} 的详细信息"


@mcp.resource("file://cities/list")
def list_all_cities() -> str:
    """
    获取所有支持的城市列表
    返回: str: 支持的城市列表
    """
    cities = list(CITY_DATABASE.keys())
    return f"## 支持的城市列表\n\n" + "\n".join([f"- {city}" for city in cities])


# =========================== TOOLS ===========================
@mcp.tool
def get_weather(city: str) -> dict:
    """
    获取指定城市的实时天气信息
    参数: city (str): 城市名称
    返回: dict: 包含天气信息的字典
    """
    import random

    # 模拟不同的天气情况
    weather_conditions = ["晴天", "多云", "小雨", "阴天", "雾霾"]
    temperatures = [f"{temp}°C" for temp in range(15, 35)]

    weather_data = {
        "city": city,
        "temperature": random.choice(temperatures),
        "condition": random.choice(weather_conditions),
        "humidity": f"{random.randint(40, 80)}%",
        "wind_speed": f"{random.randint(1, 15)}km/h",
        "air_quality": random.choice(["优", "良", "轻度污染", "中度污染"])
    }
    return weather_data


@mcp.tool
def calculate_travel_budget(city: str, days: int, accommodation_level: str = "中档") -> dict:
    """
    计算旅行预算估算
    参数: 
        city (str): 目标城市
        days (int): 旅行天数
        accommodation_level (str): 住宿档次 (经济/中档/豪华)
    返回: dict: 预算明细
    """
    # 模拟不同城市和档次的费用
    base_costs = {
        "北京": {"经济": 200, "中档": 400, "豪华": 800},
        "上海": {"经济": 250, "中档": 450, "豪华": 900},
        "杭州": {"经济": 180, "中档": 350, "豪华": 700}
    }

    daily_cost = base_costs.get(city, {"经济": 200, "中档": 400, "豪华": 800})[
        accommodation_level]
    food_cost = days * 120  # 每天餐饮费用
    transport_cost = days * 80  # 每天交通费用
    attraction_cost = days * 100  # 每天景点门票费用

    total_cost = (daily_cost * days) + food_cost + \
        transport_cost + attraction_cost

    return {
        "city": city,
        "days": days,
        "accommodation_level": accommodation_level,
        "breakdown": {
            "住宿费用": f"{daily_cost * days}元",
            "餐饮费用": f"{food_cost}元",
            "交通费用": f"{transport_cost}元",
            "景点门票": f"{attraction_cost}元"
        },
        "total_budget": f"{total_cost}元"
    }


# =========================== PROMPTS ===========================
@mcp.prompt
def travel_recommendation(city: str, weather_condition: str = "", budget_range: str = "中等") -> str:
    """
    基于城市信息、天气状况和预算生成个性化旅行建议
    参数:
        city (str): 目标城市
        weather_condition (str): 当前天气状况
        budget_range (str): 预算范围 (经济/中等/豪华)
    返回: str: 个性化旅行建议prompt
    """
    city_info = CITY_DATABASE.get(city, {})

    prompt = f"""# 为 {city} 制定个性化旅行计划

                    ## 任务背景
                    作为专业的旅行规划师，请基于以下信息为用户制定详细的旅行建议：

                    ## 城市基础信息
                    - **目标城市**: {city}
                    - **城市特色**: {city_info.get('description', '暂无描述')}
                    - **最佳旅游季节**: {city_info.get('best_season', '四季皆宜')}
                    - **热门景点**: {', '.join(city_info.get('attractions', ['待补充']))}
                    - **特色美食**: {', '.join(city_info.get('cuisine', ['待补充']))}

                    ## 当前条件
                    - **天气状况**: {weather_condition if weather_condition else '请获取最新天气信息'}
                    - **预算档次**: {budget_range}

                    ## 请提供以下建议：

                    ### 1. 行程规划建议
                    - 根据天气情况调整室内外活动安排
                    - 推荐最佳游览路线和时间安排

                    ### 2. 住宿推荐
                    - 基于预算档次推荐合适的住宿区域和类型

                    ### 3. 美食体验
                    - 必尝当地特色美食和推荐餐厅

                    ### 4. 注意事项
                    - 根据天气和季节给出实用的旅行贴士

                    ### 5. 预算优化建议
                    - 如何在预算范围内获得最佳旅行体验

                    请生成详细、实用且个性化的旅行建议。
                """
    return prompt


@mcp.prompt
def weather_outfit_advisor(city: str, weather_data: dict) -> str:
    """
    基于天气信息生成穿衣和出行建议
    参数:
        city (str): 城市名称
        weather_data (dict): 天气信息字典
    返回: str: 穿衣和出行建议prompt
    """
    prompt = f"""# {city} 天气穿衣助手

## 当前天气信息
- **城市**: {weather_data.get('city', city)}
- **温度**: {weather_data.get('temperature', '未知')}
- **天气状况**: {weather_data.get('condition', '未知')}
- **湿度**: {weather_data.get('humidity', '未知')}
- **风速**: {weather_data.get('wind_speed', '未知')}
- **空气质量**: {weather_data.get('air_quality', '未知')}

## 请基于以上天气信息提供：

### 1. 穿衣建议
- 推荐适合的服装搭配
- 是否需要携带雨具、防晒用品等

### 2. 出行建议  
- 最佳出行时间段
- 交通工具选择建议
- 是否适合户外活动

### 3. 健康提醒
- 基于空气质量的健康建议
- 特殊天气下的注意事项

### 4. 旅行活动调整
- 适合当前天气的活动推荐
- 需要避免的活动类型

请生成实用的个性化建议。
"""
    return prompt


if __name__ == "__main__":
    # 启动服务器
    print("🌟 智能旅行助手 MCP Server 启动中...")
    print("📍 支持的功能:")
    print("   🔧 Tools: 天气查询、预算计算")
    print("   📚 Resources: 城市信息、城市列表")
    print("   💡 Prompts: 旅行建议、穿衣助手")
    print("   🏙️ 支持城市: 北京、上海、杭州")

    # 使用 SSE 传输方式
    mcp.run(transport="sse", port=8080)
