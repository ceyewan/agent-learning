from dotenv import load_dotenv
import os
import requests
import json
from python_a2a import AgentNetwork, A2AClient, AIAgentRouter

# 初始化代理网络
network = AgentNetwork(name="Math Assistant Network")

# 添加代理到网络
network.add("Sine", "http://localhost:4737")
network.add("Cosine", "http://localhost:4738")
network.add("Tangent", "http://localhost:4739")

# 加载环境变量
load_dotenv()  # 默认会读取当前目录下的 .env 文件
QWEN_API_KEY = os.environ.get("QWEN_API_KEY")

if not QWEN_API_KEY:
    raise ValueError("请在 .env 文件中设置 QWEN_API_KEY")

print(f"API Key 已加载: {QWEN_API_KEY[:10]}...")

# 配置 LLM 客户端
llm_client = A2AClient(
    endpoint_url="https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions",
    headers={"Authorization": f"Bearer {QWEN_API_KEY}"},
    timeout=60
)

# 创建路由器
router = AIAgentRouter(
    llm_client=llm_client,
    agent_network=network
)


def test_agent_connectivity():
    """测试所有代理的连接性"""
    agent_urls = {
        "Sine": "http://localhost:4737",
        "Cosine": "http://localhost:4738",
        "Tangent": "http://localhost:4739"
    }

    print("测试代理连接性...")
    available_agents = []

    for name, url in agent_urls.items():
        try:
            response = requests.get(f"{url}/health", timeout=5)
            if response.status_code == 200:
                print(f"✓ {name} 代理可用 ({url})")
                available_agents.append(name)
            else:
                print(f"✗ {name} 代理不可用 ({url}) - 状态码: {response.status_code}")
        except Exception as e:
            print(f"✗ {name} 代理不可用 ({url}) - 错误: {e}")

    return available_agents


def call_agent_directly(agent_url, query):
    """直接调用代理服务"""
    try:
        # 尝试不同的API端点
        endpoints = ["/process", "/task", "/ask"]

        for endpoint in endpoints:
            try:
                response = requests.post(
                    f"{agent_url}{endpoint}",
                    json={"query": query, "message": query, "text": query},
                    timeout=30
                )
                if response.status_code == 200:
                    return response.json()
            except:
                continue

        # 如果所有端点都失败，尝试GET请求
        response = requests.get(f"{agent_url}?query={query}", timeout=30)
        if response.status_code == 200:
            return response.text

        return f"代理调用失败: 所有端点都不可用"
    except Exception as e:
        return f"连接代理失败: {e}"


def main():
    # 测试查询
    test_queries = [
        "60 度的正切值是多少？",
        "计算 30 度的正弦值",
        "45 度的余弦值是多少？"
    ]

    # 测试连接性
    available_agents = test_agent_connectivity()

    if not available_agents:
        print("\n❌ 没有可用的代理！请先启动代理服务器:")
        print("python start_agents.py")
        return

    print(f"\n✓ 找到 {len(available_agents)} 个可用代理")

    # 代理URL映射
    agent_urls = {
        "Sine": "http://localhost:4737",
        "Cosine": "http://localhost:4738",
        "Tangent": "http://localhost:4739"
    }

    for query in test_queries:
        print(f"\n" + "="*50)
        print(f"🔍 查询: {query}")

        try:
            # 使用路由器确定应该使用哪个代理
            agent_name, confidence = router.route_query(query)
            print(f"🤖 路由结果: {agent_name} (置信度: {confidence:.2f})")

            if agent_name in agent_urls and agent_name in [name.split()[0] for name in available_agents]:
                agent_url = agent_urls[agent_name]
                print(f"📡 调用代理: {agent_url}")

                # 直接调用代理
                response = call_agent_directly(agent_url, query)
                print(f"📋 响应: {response}")
            else:
                print(f"❌ 代理 {agent_name} 不可用或未知")

        except Exception as e:
            print(f"❌ 发生错误: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    main()
