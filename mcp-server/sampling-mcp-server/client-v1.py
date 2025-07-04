import asyncio
from fastmcp import Client
from fastmcp.client.sampling import SamplingMessage, SamplingParams
from mcp.shared.context import RequestContext
import litellm
import os


# Qwen 配置
QWEN_API_KEY = os.getenv("QWEN_API_KEY", "")
QWEN_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
QWEN_MODEL = "openai/qwen-plus-latest"  # 可根据需要更换


async def sampling_handler(
    messages: list[SamplingMessage],
    params: SamplingParams,
    ctx: RequestContext
) -> str:
    """处理服务器的采样请求"""
    try:
        if not QWEN_API_KEY:
            return "Error: QWEN_API_KEY 环境变量未设置"
        # 构建消息格式
        chat_messages = []

        # 添加系统提示（如果有）
        if params.systemPrompt:
            chat_messages.append({
                "role": "system",
                "content": params.systemPrompt
            })

        # 添加对话消息
        for msg in messages:
            # 安全获取 text 属性，兼容 ImageContent/AudioContent 等
            content = getattr(msg.content, 'text', str(msg.content))
            chat_messages.append({
                "role": msg.role,
                "content": content
            })

        # 处理模型偏好
        model_to_use = QWEN_MODEL  # 默认用 Qwen
        if params.modelPreferences and params.modelPreferences.hints and params.modelPreferences.hints[0].name:
            model_to_use = params.modelPreferences.hints[0].name or QWEN_MODEL

        # 确保 model_to_use 是字符串且不为 None
        if not isinstance(model_to_use, str) or not model_to_use:
            model_to_use = QWEN_MODEL

        # 调用LLM，传递 Qwen 的 base_url 和 api_key
        response = await litellm.acompletion(
            model=model_to_use,
            messages=chat_messages,
            temperature=params.temperature or 0.7,
            max_tokens=params.maxTokens or 500,
            base_url=QWEN_BASE_URL,
            api_key=QWEN_API_KEY
        )

        # 只用 dict 方式安全提取内容
        if isinstance(response, dict):
            try:
                content = response['choices'][0]['message']['content']
                if content is not None:
                    return str(content)
            except Exception:
                pass
            try:
                text = response['choices'][0]['text']
                if text is not None:
                    return str(text)
            except Exception:
                pass
            return str(response)
        # 兜底：直接转字符串
        return str(response)
    except Exception as e:
        return f"Error generating response: {str(e)}"


async def main():
    # 连接到MCP服务器
    async with Client("http://localhost:8080/sse/", sampling_handler=sampling_handler) as client:
        # 调用工具
        result = await client.call_tool(
            "analyze_sentiment_with_summary",
            {"text": "I absolutely love this new technology! It's revolutionary and will change everything for the better."}
        )
        print("Analysis Result:")
        print(result)

if __name__ == "__main__":
    asyncio.run(main())
