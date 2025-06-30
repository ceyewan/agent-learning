from fastmcp import FastMCP, Context

mcp = FastMCP(name="Document Assistant")


@mcp.tool()
async def summarize_document(document_text: str, ctx: Context) -> str:
    """Generate a summary of the given document text."""
    # Request the client's LLM to summarize the document
    response = await ctx.sample(
        messages=f"Summarize the following document:\n{document_text}",
        system_prompt="You are an expert summarizer. Extract the key ideas and summarize them.",
        temperature=0.7,
        max_tokens=300,
        model_preferences="gpt-4o"
    )
    summary = response.text.strip()
    return f"Summary:\n{summary}."


if __name__ == "__main__":
    mcp.run()   # stdio
