import os
import os
from typing import TypedDict, Annotated, Literal
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, BaseMessage
from langchain.prompts import PromptTemplate
from langgraph.graph import StateGraph, END
from langchain_core.tools import tool
from langgraph.graph.message import add_messages

from llm import llm


# 优化状态结构
class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]  # 使用 add_messages
    file_path: str
    file_content: str
    summary: str
    next_action: Literal["read_file", "summarize", "end"]


# 工具定义：读取文件内容
@tool
def read_file(file_path: str) -> str:
    """读取指定路径的文件内容，适用于文本类文件如 .txt、.md 等。"""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        return content
    except Exception as e:
        return f"Error reading file: {str(e)}"


# 工具定义：内容摘要
@tool
def summarize_content(input_text: str) -> str:
    """对输入文本进行简明扼要的总结，控制在 20 字以内。"""
    prompt_template = PromptTemplate.from_template(
        """你是一个资深文档分析师，请阅读以下文本内容：

        {input}

        请提供一个不超过 20 字的简洁摘要，突出关键信息。"""
    )
    prompt = prompt_template.format(input=input_text)
    response = llm.invoke([HumanMessage(content=prompt)])
    return response.content.strip()


# 节点函数：文件读取节点
def file_reader_node(state: AgentState) -> AgentState:
    """读取文件内容"""
    file_path = state["file_path"]
    content = read_file.invoke({"file_path": file_path})

    state["file_content"] = content
    state["messages"].append(AIMessage(content=f"已读取文件 {file_path}，内容长度：{len(content)} 字符"))
    state["next_action"] = "summarize"

    return state


# 节点函数：内容摘要节点
def summarizer_node(state: AgentState) -> AgentState:
    """生成内容摘要"""
    content = state["file_content"]
    summary = summarize_content.invoke({"input_text": content})

    state["summary"] = summary
    state["messages"].append(AIMessage(content=f"生成摘要：{summary}"))
    state["next_action"] = "end"

    return state


# 条件函数：决定下一步操作
def should_continue(state: AgentState) -> str:
    """根据当前状态决定下一个节点"""
    next_action = state.get("next_action", "read_file")

    if next_action == "read_file":
        return "file_reader"
    elif next_action == "summarize":
        return "summarizer"
    else:
        return END


# 构建工作流图
def create_workflow():
    workflow = StateGraph(AgentState)

    # 添加节点
    workflow.add_node("file_reader", file_reader_node)
    workflow.add_node("summarizer", summarizer_node)

    # 设置入口点
    workflow.set_entry_point("file_reader")

    # 添加条件边
    workflow.add_conditional_edges(
        "file_reader",
        should_continue,
        {
            "summarizer": "summarizer",
            END: END
        }
    )

    workflow.add_conditional_edges(
        "summarizer",
        should_continue,
        {
            END: END
        }
    )

    return workflow.compile()


# 主执行函数
def run_file_summarizer(file_path: str):
    """执行文件摘要任务"""
    app = create_workflow()

    # 初始化状态
    initial_state = {
        "messages": [SystemMessage(content="开始文件摘要任务")],
        "file_path": file_path,
        "file_content": "",
        "summary": "",
        "next_action": "read_file"
    }

    # 执行工作流
    final_state = app.invoke(initial_state)

    return final_state


# 使用示例
if __name__ == "__main__":
    file_path = "output.md"

    print("=== LangGraph 文件摘要工作流 ===")
    result = run_file_summarizer(file_path)

    print("\n--- 执行过程 ---")
    for msg in result["messages"]:
        print(f"{msg.__class__.__name__}: {msg.content}")

    print(f"\n--- 最终摘要 ---")
    print(result["summary"])