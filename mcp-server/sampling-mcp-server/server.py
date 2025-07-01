from fastmcp import FastMCP, Context

mcp = FastMCP("SamplingDemo")


@mcp.tool()
async def analyze_sentiment_with_summary(text: str, ctx: Context) -> str:
    """分析文本情感并提供详细摘要"""
    try:
        # 第一次采样：分析情感
        sentiment_response = await ctx.sample(
            messages=f"Analyze the sentiment of this text: {text}",
            system_prompt="You are a sentiment analysis expert. Classify as positive, negative, or neutral with confidence score.",
            temperature=0.3,
            max_tokens=1000,
            model_preferences=["openai/qwen-turbo-latest"]
        )

        # 第二次采样：生成详细摘要
        summary_response = await ctx.sample(
            messages=f"Provide a detailed summary of this text: {text}",
            system_prompt="You are a professional summarizer. Create comprehensive yet concise summaries.",
            temperature=0.7,
            max_tokens=1000
        )

        return f"Sentiment Analysis: {getattr(sentiment_response, 'text', str(sentiment_response))}\n\nSummary: {getattr(summary_response, 'text', str(summary_response))}"

    except Exception as e:
        await ctx.error(f"Sampling failed: {str(e)}")
        return f"Analysis failed, but here's basic info: Text length is {len(text)} characters."

if __name__ == "__main__":
    mcp.run("sse", port=8080)
