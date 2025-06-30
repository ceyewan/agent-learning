from fastmcp import Client
from fastmcp.client.sampling import SamplingMessage, SamplingParams
from mcp.shared.context import RequestContext
from litellm import acompletion
import asyncio
import os

from dotenv import load_dotenv
load_dotenv()


# A minimal client-side implementation (not the complete logic): to particularly demonstrate the sampling handler.
async def sampling_handler(
    messages: list[SamplingMessage],
    params: SamplingParams,
    ctx: RequestContext
) -> str:
    """Handle sampling requests using LiteLLM and OpenAI GPT-4o."""
    chat_messages = []
    if params.systemPrompt:
        chat_messages.append(
            {"role": "system", "content": params.systemPrompt})
    for m in messages:
        if m.content.type == "text":
            chat_messages.append({"role": m.role, "content": m.content.text})
    if params.modelPreferences:
        # if it's a list, take first supported; if string, use directly.
        # This is demonstrational, however, in reality a more robust handling logic and fallback is needed.
        preferred_model = params.modelPreferences.hints[0].name
    print(preferred_model)
    print(params.temperature)
    print(params.maxTokens)
    try:
        response = await acompletion(
            model=preferred_model,
            messages=chat_messages,
            temperature=params.temperature,
            max_tokens=params.maxTokens,
            # .env file approach can also be used
            api_key=os.getenv("OPENAI_API_KEY"),
        )
        generated_text = response["choices"][0]["message"]["content"]
    except Exception as e:
        generated_text = f"[Error: LLM failed: {e}]"

    return generated_text

client = Client("server.py", sampling_handler=sampling_handler)  # stdio


async def main():

    print(client.transport)
    async with client:
        f = open("sample.txt", "r")
        result = await client.call_tool("summarize_document", {"document_text": f.read()})
        print(result)

    # Connection is closed automatically here
    # False: since connection gets closed gracefully.
    print(f"Connected?: {client.is_connected()}")
    # The client operates asynchronously within the async with block.
    # This context manager automatically handles the connection, initializations, and clean up upon exit.

if __name__ == "__main__":
    asyncio.run(main())
