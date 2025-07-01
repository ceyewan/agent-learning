import asyncio
from fastmcp import Client
from fastmcp.client.sampling import SamplingMessage, SamplingParams
from mcp.shared.context import RequestContext
import litellm
import os
from datetime import datetime
import json


# Qwen 配置
QWEN_API_KEY = os.getenv("QWEN_API_KEY", "")
QWEN_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
QWEN_MODEL = "openai/qwen-plus-latest"

# 全局计数器，用于跟踪采样请求
sampling_counter = 0


async def enhanced_sampling_handler(
    messages: list[SamplingMessage],
    params: SamplingParams,
    ctx: RequestContext
) -> str:
    """
    增强的采样处理器，展示 Context 的独立性和详细日志
    """
    global sampling_counter
    sampling_counter += 1

    # 生成唯一的采样会话ID
    session_id = f"sampling_{sampling_counter:03d}"
    current_time = datetime.now().strftime('%H:%M:%S.%f')[:-3]

    print(f"\n{'='*60}")
    print(f"🎯 采样请求开始 #{sampling_counter}")
    print(f"{'='*60}")
    print(f"⏰ 时间: {current_time}")
    print(f"🆔 会话ID: {session_id}")
    print(f"📋 请求ID: {getattr(ctx, 'request_id', 'unknown')}")
    print(f"🔧 客户端上下文: {type(ctx).__name__}")

    # 分析请求参数
    print(f"\n📊 请求参数分析:")
    print(f"   🌡️  温度: {params.temperature}")
    print(f"   📏 最大令牌: {params.maxTokens}")
    print(f"   🤖 模型偏好: {params.modelPreferences}")
    print(f"   💬 消息数量: {len(messages)}")

    # 分析系统提示
    if params.systemPrompt:
        system_preview = params.systemPrompt[:100] + "..." if len(
            params.systemPrompt) > 100 else params.systemPrompt
        print(f"   📝 系统提示: {system_preview}")
    else:
        print(f"   📝 系统提示: 无")

    # 分析消息内容
    print(f"\n💬 消息内容分析:")
    for i, msg in enumerate(messages):
        content = getattr(msg.content, 'text', str(msg.content))
        content_preview = content[:80] + \
            "..." if len(content) > 80 else content
        print(f"   {i+1}. [{msg.role}] {content_preview}")

    # 检查API密钥
    if not QWEN_API_KEY:
        error_msg = "❌ QWEN_API_KEY 环境变量未设置"
        print(f"\n{error_msg}")
        print(f"{'='*60}")
        return error_msg

    try:
        # 构建聊天消息
        print(f"\n🔧 构建LLM请求...")
        chat_messages = []

        # 添加系统提示
        if params.systemPrompt:
            chat_messages.append({
                "role": "system",
                "content": params.systemPrompt
            })
            print(f"   ✅ 添加系统消息")

        # 添加对话消息
        for msg in messages:
            content = getattr(msg.content, 'text', str(msg.content))
            chat_messages.append({
                "role": msg.role,
                "content": content
            })
            print(f"   ✅ 添加 {msg.role} 消息")

        # 确定使用的模型
        model_to_use = QWEN_MODEL
        if (params.modelPreferences and
            params.modelPreferences.hints and
                params.modelPreferences.hints[0].name):
            model_to_use = params.modelPreferences.hints[0].name

        print(f"   🤖 使用模型: {model_to_use}")

        # 调用LLM
        print(f"\n🚀 调用LLM...")
        llm_start_time = datetime.now()

        response = await litellm.acompletion(
            model=model_to_use,
            messages=chat_messages,
            temperature=params.temperature or 0.7,
            max_tokens=params.maxTokens or 500,
            base_url=QWEN_BASE_URL,
            api_key=QWEN_API_KEY
        )

        llm_duration = (datetime.now() - llm_start_time).total_seconds()
        print(f"   ⏱️  LLM响应时间: {llm_duration:.2f}秒")

        # 提取响应内容
        result_content = None
        if isinstance(response, dict):
            try:
                result_content = response['choices'][0]['message']['content']
                print(f"   ✅ 成功提取响应内容 (dict格式)")
            except Exception as e:
                print(f"   ⚠️  dict格式提取失败: {e}")
                try:
                    result_content = response['choices'][0]['text']
                    print(f"   ✅ 使用备用提取方法 (text字段)")
                except Exception:
                    result_content = str(response)
                    print(f"   ⚠️  使用字符串转换")
        else:
            result_content = str(response)
            print(f"   ✅ 直接字符串转换")

        # 分析响应结果
        if result_content:
            result_length = len(result_content)
            result_preview = result_content[:100] + \
                "..." if result_length > 100 else result_content
            print(f"\n📤 响应结果分析:")
            print(f"   📏 响应长度: {result_length} 字符")
            print(f"   👀 内容预览: {result_preview}")

            # 检查响应质量
            if result_length < 10:
                print(f"   ⚠️  响应较短，可能存在问题")
            elif result_length > 1000:
                print(f"   ℹ️  响应较长，内容丰富")
            else:
                print(f"   ✅ 响应长度适中")

        print(f"\n✅ 采样请求完成 #{sampling_counter}")
        print(
            f"⏱️  总耗时: {(datetime.now() - datetime.strptime(current_time, '%H:%M:%S.%f')).total_seconds():.2f}秒")
        print(f"{'='*60}\n")

        return result_content or "响应为空"

    except Exception as e:
        error_msg = f"LLM调用失败: {str(e)}"
        print(f"\n❌ 错误详情:")
        print(f"   🚨 错误类型: {type(e).__name__}")
        print(f"   📝 错误信息: {str(e)}")
        print(f"   🆔 会话ID: {session_id}")
        print(f"\n❌ 采样请求失败 #{sampling_counter}")
        print(f"{'='*60}\n")

        return error_msg


async def demo_independent_sampling():
    """演示采样的独立性"""
    print("🎭 开始演示采样独立性...")
    print("📝 这将调用服务器的 analyze_sentiment_with_summary 工具")
    print("🔍 观察两次独立的采样调用\n")

    async with Client("http://localhost:8080/sse/", sampling_handler=enhanced_sampling_handler) as client:

        test_text = """
我对这项新技术感到非常兴奋！它真的很革命性，将会彻底改变我们的工作方式。
这种创新让我看到了未来的无限可能性，我迫不及待想要开始使用它。
虽然学习新技术总是有挑战的，但我相信这个投资是值得的。
"""

        print(f"🎯 测试文本: {test_text.strip()[:100]}...")
        print(f"📏 文本长度: {len(test_text)} 字符\n")

        try:
            result = await client.call_tool(
                "analyze_sentiment_with_summary",
                {"text": test_text.strip()}
            )

            print("🎉 工具调用完成！")
            print("📋 最终结果:")
            print("-" * 50)
            print(result)
            print("-" * 50)

        except Exception as e:
            print(f"❌ 工具调用失败: {str(e)}")


async def demo_context_continuity():
    """演示上下文连续性"""
    print("\n" + "="*60)
    print("🔗 开始演示上下文连续性...")
    print("📝 这将调用服务器的 analyze_with_context_continuity 工具")
    print("🔍 观察第二次采样如何包含第一次的结果\n")

    async with Client("http://localhost:8080/sse/", sampling_handler=enhanced_sampling_handler) as client:

        test_text = "今天的天气真是糟糕透了，下雨又刮风，心情也变得很沮丧。"

        print(f"🎯 测试文本: {test_text}")
        print(f"📏 文本长度: {len(test_text)} 字符\n")

        try:
            result = await client.call_tool(
                "analyze_with_context_continuity",
                {"text": test_text}
            )

            print("🎉 上下文连续性演示完成！")
            print("📋 最终结果:")
            print("-" * 50)
            print(result)
            print("-" * 50)

        except Exception as e:
            print(f"❌ 工具调用失败: {str(e)}")


async def demo_simple_test():
    """简单测试"""
    print("\n" + "="*60)
    print("🧪 开始简单功能测试...")
    print("📝 这将调用服务器的 simple_echo_test 工具\n")

    async with Client("http://localhost:8080/sse/", sampling_handler=enhanced_sampling_handler) as client:

        test_message = "你好，这是一个测试消息！"

        try:
            result = await client.call_tool(
                "simple_echo_test",
                {"message": test_message}
            )

            print("🎉 简单测试完成！")
            print("📋 结果:")
            print("-" * 30)
            print(result)
            print("-" * 30)

        except Exception as e:
            print(f"❌ 简单测试失败: {str(e)}")


async def main():
    """主函数，运行所有演示"""
    print("🚀 Enhanced MCP Client 演示程序")
    print("=" * 60)
    print("📋 演示内容:")
    print("   1. 采样独立性演示")
    print("   2. 上下文连续性演示")
    print("   3. 简单功能测试")
    print("=" * 60)

    if not QWEN_API_KEY:
        print("❌ 错误: 请设置 QWEN_API_KEY 环境变量")
        print("💡 提示: export QWEN_API_KEY='your_api_key_here'")
        return

    print(f"✅ API配置检查通过")
    print(f"🤖 使用模型: {QWEN_MODEL}")
    print(f"🔗 API地址: {QWEN_BASE_URL}")
    print(f"🔑 API密钥: {'*' * (len(QWEN_API_KEY) - 4) + QWEN_API_KEY[-4:]}")

    try:
        # 运行所有演示
        await demo_simple_test()
        await asyncio.sleep(2)  # 间隔2秒

        await demo_independent_sampling()
        await asyncio.sleep(2)  # 间隔2秒

        await demo_context_continuity()

        print("\n🎉 所有演示完成！")
        print("📊 采样统计:")
        print(f"   📈 总采样次数: {sampling_counter}")
        print(f"   ⚡ 平均每个工具的采样次数: {sampling_counter/3:.1f}")

    except KeyboardInterrupt:
        print("\n⏹️  用户中断程序")
    except Exception as e:
        print(f"\n❌ 程序执行出错: {str(e)}")

    print("\n👋 程序结束")


if __name__ == "__main__":
    asyncio.run(main())
