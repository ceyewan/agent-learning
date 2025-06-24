import os
from python_a2a import OpenAIA2AServer, run_server

# 创建一个由 OpenAI 驱动的智能体
agent = OpenAIA2AServer(
    api_key=os.environ["OPENAI_API_KEY"],
    model="gpt-4",
    system_prompt="你是一个有帮助的 AI 助手。"
)

# 运行服务器
if __name__ == "__main__":
    run_server(agent, host="0.0.0.0", port=5000)
