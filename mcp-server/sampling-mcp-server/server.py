from fastmcp import FastMCP, Context
import asyncio
from datetime import datetime
import json

mcp = FastMCP("Enhanced Sampling Demo")


@mcp.tool()
async def analyze_sentiment_with_summary(text: str, ctx: Context) -> str:
    """
    分析文本情感并提供详细摘要

    这个工具会进行两次独立的采样调用：
    1. 情感分析采样
    2. 文本摘要采样

    每次采样都是完全独立的，不会共享上下文。
    """

    start_time = datetime.now()
    await ctx.info(f"🚀 开始分析文本 | 长度: {len(text)} 字符 | 时间: {start_time.strftime('%H:%M:%S')}")

    if len(text.strip()) == 0:
        await ctx.error("❌ 输入文本为空")
        return "错误：输入文本不能为空"

    try:
        # ==================== 第一次独立采样：情感分析 ====================
        await ctx.info("📊 开始第一次采样：情感分析")
        await ctx.debug(f"采样参数 - 温度: 0.3, 最大令牌: 500, 模型偏好: qwen-turbo")

        sentiment_start = datetime.now()
        sentiment_response = await ctx.sample(
            messages=f"请分析以下文本的情感倾向：\n\n{text}",
            system_prompt="""
                你是一个专业的情感分析专家。请按照以下格式分析文本情感：

                1. 情感分类：正面/负面/中性
                2. 置信度：0-100%
                3. 关键情感词汇：列出3-5个关键词
                4. 情感强度：低/中/高
                5. 简要解释：一句话说明判断依据

                请保持分析客观准确。""",
            temperature=0.3,
            max_tokens=500,
            model_preferences=["openai/qwen-turbo-latest"]
        )

        sentiment_duration = (datetime.now() - sentiment_start).total_seconds()
        await ctx.info(f"✅ 第一次采样完成 | 耗时: {sentiment_duration:.2f}秒")

        # 等待一秒，让日志输出更清晰
        await asyncio.sleep(1)

        # ==================== 第二次独立采样：文本摘要 ====================
        await ctx.info("📝 开始第二次采样：文本摘要")
        await ctx.debug(f"采样参数 - 温度: 0.7, 最大令牌: 800, 无模型偏好")

        summary_start = datetime.now()
        summary_response = await ctx.sample(
            messages=f"请为以下文本生成详细摘要：\n\n{text}",
            system_prompt="""你是一个专业的文本摘要专家。请生成结构化的摘要：

                1. 核心主题：用一句话概括主要内容
                2. 关键信息：列出3-5个要点
                3. 文本特点：分析写作风格和语言特色
                4. 目标受众：推测可能的读者群体
                5. 总结：用2-3句话进行整体总结

                请保持摘要全面而简洁。""",
            temperature=0.7,
            max_tokens=800
        )

        summary_duration = (datetime.now() - summary_start).total_seconds()
        await ctx.info(f"✅ 第二次采样完成 | 耗时: {summary_duration:.2f}秒")

        # ==================== 整合结果 ====================
        total_duration = (datetime.now() - start_time).total_seconds()
        await ctx.info(f"🎉 分析完成 | 总耗时: {total_duration:.2f}秒")

        # 格式化最终结果
        result = f"""
# 📊 文本分析报告

## 📈 情感分析结果
{getattr(sentiment_response, 'text', str(sentiment_response))}

## 📋 文本摘要结果  
{getattr(summary_response, 'text', str(summary_response))}

---
**分析统计**
- 原文长度: {len(text)} 字符
- 情感分析耗时: {sentiment_duration:.2f}秒
- 摘要生成耗时: {summary_duration:.2f}秒
- 总处理时间: {total_duration:.2f}秒
- 分析时间: {start_time.strftime('%Y-%m-%d %H:%M:%S')}
"""

        return result.strip()

    except Exception as e:
        error_msg = f"采样过程发生错误: {str(e)}"
        await ctx.error(f"❌ {error_msg}")

        # 提供降级服务
        fallback_result = f"""
# ⚠️ 分析失败，提供基础信息

**文本基础统计：**
- 字符数: {len(text)}
- 单词数: {len(text.split())}
- 段落数: {len(text.split('\\n\\n'))}
- 包含感叹号: {'是' if '!' in text else '否'}
- 包含问号: {'是' if '?' in text else '否'}

**错误信息:** {error_msg}
**建议:** 请检查网络连接或稍后重试
"""
        return fallback_result.strip()


@mcp.tool()
async def analyze_with_context_continuity(text: str, ctx: Context) -> str:
    """
    带上下文连续性的分析工具

    演示如何在第二次采样中包含第一次采样的结果，
    实现上下文的连续性。
    """

    await ctx.info("🔗 开始带上下文连续性的分析")

    try:
        # 第一次采样：情感分析
        await ctx.info("1️⃣ 执行情感分析")
        sentiment_response = await ctx.sample(
            messages=f"分析情感：{text}",
            system_prompt="你是情感分析专家，简洁回答情感类型和置信度。",
            temperature=0.3,
            max_tokens=200
        )

        sentiment_result = getattr(
            sentiment_response, 'text', str(sentiment_response))
        await ctx.debug(f"情感分析结果: {sentiment_result[:50]}...")

        # 第二次采样：基于情感分析结果生成摘要
        await ctx.info("2️⃣ 基于情感分析生成摘要")
        contextual_summary_response = await ctx.sample(
            messages=[
                f"原始文本: {text}",
                f"情感分析结果: {sentiment_result}",
                "请基于上述情感分析结果，生成一个考虑了情感色彩的详细摘要。"
            ],
            system_prompt="你是摘要专家，能够结合情感分析结果生成更准确的摘要。",
            temperature=0.6,
            max_tokens=600
        )

        summary_result = getattr(
            contextual_summary_response, 'text', str(contextual_summary_response))

        result = f"""
# 🔗 上下文连续性分析报告

## 🎯 情感分析（第一步）
{sentiment_result}

## 📝 基于情感的摘要（第二步，包含第一步结果）
{summary_result}

---
**说明：** 第二次采样明确包含了第一次采样的结果，实现了上下文连续性。
"""

        await ctx.info("✅ 上下文连续性分析完成")
        return result.strip()

    except Exception as e:
        await ctx.error(f"上下文连续性分析失败: {str(e)}")
        return f"分析失败: {str(e)}"


@mcp.tool()
async def simple_echo_test(message: str, ctx: Context) -> str:
    """简单的回显测试工具，用于验证基础功能"""

    await ctx.info(f"🔄 执行回显测试: {message[:30]}...")

    try:
        response = await ctx.sample(
            messages=f"请简单回复这条消息：{message}",
            system_prompt="你是一个友好的助手，请简洁地回复用户的消息。",
            temperature=0.5,
            max_tokens=100
        )

        result = getattr(response, 'text', str(response))
        await ctx.info("✅ 回显测试完成")

        return f"原始消息: {message}\n回复: {result}"

    except Exception as e:
        await ctx.error(f"回显测试失败: {str(e)}")
        return f"回显失败: {str(e)}"


if __name__ == "__main__":
    print("🚀 启动 Enhanced MCP 服务器...")
    print("📡 监听端口: 8080")
    print("🔗 连接方式: SSE")
    print("=" * 50)
    mcp.run("sse", port=8080)
