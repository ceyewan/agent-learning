from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from llm import llm

# 定义中文提示模板，包含角色设定、目标和背景信息
prompt = ChatPromptTemplate.from_messages([
    ("system", """你是一个{role}。你的目标：{goal}
                你的背景故事：{backstory}"""),
    ("human", """请完成以下描述内容：{description}
                ---
                请确保最终输出符合要求：{expected_output}""")
])

# 构建 LCEL 流水线：输入 -> 提示模板 -> 大模型 -> 输出解析器 -> 字符串输出
chain = prompt | llm | StrOutputParser()

# 准备输入参数（使用中文描述角色与任务）
inputs = {
    "role": "高级技术文档撰写者",
    "goal": "根据研究结果撰写清晰、有吸引力且结构良好的技术内容",
    "backstory": "你是一位经验丰富的技术写作者，擅长将复杂概念简化，构建易于阅读的内容结构，并确保文档的准确性。",
    "description": "撰写一篇结构清晰、引人入胜且技术准确的文章，主题为：AI Agents（人工智能智能体）。",
    "expected_output": "一篇结构完整、内容详实、易于阅读的技术文章。"
}

# 开始流式调用并逐块打印输出
print("--- 开始流式输出 ---")

for chunk in chain.stream(inputs):
    print(chunk, end="", flush=True)  # 不换行输出，实时刷新控制台

print("\n--- 流式输出结束 ---")
