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

# 创建路由器
router = AIAgentRouter(
    llm_client=A2AClient("http://localhost:5000/openai"),
    agent_network=network
)
