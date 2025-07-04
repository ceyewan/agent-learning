import os

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

# 加载 .env 文件中的环境变量
load_dotenv()

# 设置 OpenAI 兼容接口的 API Key 和基础 URL（如 Qwen）
os.environ["OPENAI_API_KEY"] = os.getenv("QWEN_API_KEY")

# 初始化大模型客户端
llm = ChatOpenAI(
    model="qwen-plus-latest",
    temperature=0.7,
    base_url=os.getenv("QWEN_BASE_URL")
)