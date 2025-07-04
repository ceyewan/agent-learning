import os
import logging
from typing import TypedDict, List, Annotated, Literal, Optional
from datetime import datetime

from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langgraph.graph import StateGraph, END, add_messages
from langchain_community.utilities import SerpAPIWrapper
from llm import llm

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class ResearchState(TypedDict):
    """研究状态定义 - 包含完整的工作流状态信息"""
    # 核心数据
    messages: Annotated[List[BaseMessage], add_messages]  # 消息历史记录
    topic: str  # 用户输入的研究主题

    # 各阶段输出
    search_queries: List[str]  # 生成的搜索查询列表
    raw_search_results: List[str]  # 原始搜索结果
    research_report: str  # 结构化研究报告
    summary: str  # 精炼总结
    verified_summary: str  # 事实核查后的最终摘要

    # 流程控制
    current_step: Literal["research", "summarize", "fact_check", "completed", "error"]
    error_message: Optional[str]  # 错误信息

    # 元数据
    timestamp: str  # 执行时间戳
    total_sources: int  # 信息源数量


class EnhancedLangGraphResearchCrew:
    """增强版研究工作流 - 提供详细的步骤输出和错误处理"""

    def __init__(self):
        self.llm = llm
        self.search = self._initialize_search()

    def _initialize_search(self) -> SerpAPIWrapper:
        """初始化搜索工具"""
        api_key = os.getenv("SERPAPI_API_KEY")
        if not api_key:
            raise ValueError("SERPAPI_API_KEY 环境变量未设置")

        os.environ["SERPAPI_API_KEY"] = api_key
        return SerpAPIWrapper()

    def research_node(self, state: ResearchState) -> ResearchState:
        """
        研究节点 - 第一步：信息收集和研究

        输入: ResearchState.topic (研究主题)
        输出: ResearchState.research_report (结构化研究报告)
        处理流程：
        1. 根据主题生成多个搜索查询
        2. 执行搜索并收集结果
        3. 使用LLM整合信息生成报告
        """
        print("\n" + "=" * 60)
        print("🔍 第一步：研究信息收集阶段")
        print("=" * 60)
        print(f"📋 输入主题: {state['topic']}")

        try:
            # 1. 生成搜索查询策略
            queries = self._generate_search_queries(state['topic'])
            print(f"🎯 生成搜索查询 ({len(queries)}个):")
            for i, query in enumerate(queries, 1):
                print(f"   {i}. {query}")

            # 2. 执行搜索
            print(f"\n🌐 执行搜索...")
            search_results = []
            successful_searches = 0

            for i, query in enumerate(queries, 1):
                try:
                    print(f"   正在搜索 {i}/{len(queries)}: {query[:50]}...")
                    result = self.search.run(query)
                    search_results.append(result)
                    successful_searches += 1
                    print(f"   ✅ 搜索 {i} 完成 ({len(result)}字符)")
                except Exception as e:
                    error_msg = f"搜索失败: {str(e)}"
                    print(f"   ❌ 搜索 {i} 失败: {error_msg}")
                    search_results.append(f"搜索失败: {error_msg}")

            print(f"📊 搜索结果: {successful_searches}/{len(queries)} 成功")

            # 3. 生成研究报告
            print(f"\n🤖 正在生成研究报告...")
            research_report = self._generate_research_report(state['topic'], search_results)
            print(f"📝 研究报告生成完成 ({len(research_report)}字符)")

            # 更新状态
            new_state = state.copy()
            new_state.update({
                "search_queries": queries,
                "raw_search_results": search_results,
                "research_report": research_report,
                "current_step": "summarize",
                "total_sources": successful_searches,
                "messages": state["messages"] + [
                    HumanMessage(content=f"研究主题: {state['topic']}"),
                    AIMessage(content=f"研究报告已生成，包含{successful_searches}个信息源")
                ]
            })

            print(f"✅ 研究阶段完成，进入总结阶段")
            return new_state

        except Exception as e:
            error_msg = f"研究节点执行失败: {str(e)}"
            logger.error(error_msg)
            return self._handle_error(state, error_msg)

    def summarize_node(self, state: ResearchState) -> ResearchState:
        """
        总结节点 - 第二步：信息精炼和总结

        输入: ResearchState.research_report (研究报告)
        输出: ResearchState.summary (精炼总结)
        处理流程：
        1. 分析研究报告的关键信息
        2. 提取最重要的洞察和数据
        3. 生成结构化的简洁总结
        """
        print("\n" + "=" * 60)
        print("📝 第二步：信息总结阶段")
        print("=" * 60)
        print(f"📋 输入: 研究报告 ({len(state['research_report'])}字符)")

        try:
            # 分析报告并生成总结
            print("🤖 正在分析研究报告...")
            summary = self._generate_summary(state['topic'], state['research_report'])

            print(f"📊 总结统计:")
            print(f"   - 原始报告长度: {len(state['research_report'])} 字符")
            print(f"   - 总结长度: {len(summary)} 字符")
            print(f"   - 压缩比: {len(summary) / len(state['research_report']):.2%}")

            # 更新状态
            new_state = state.copy()
            new_state.update({
                "summary": summary,
                "current_step": "fact_check",
                "messages": state["messages"] + [
                    HumanMessage(content="请总结研究报告"),
                    AIMessage(content=f"总结已完成，压缩比{len(summary) / len(state['research_report']):.2%}")
                ]
            })

            print("✅ 总结阶段完成，进入事实核查阶段")
            return new_state

        except Exception as e:
            error_msg = f"总结节点执行失败: {str(e)}"
            logger.error(error_msg)
            return self._handle_error(state, error_msg)

    def fact_check_node(self, state: ResearchState) -> ResearchState:
        """
        事实核查节点 - 第三步：验证和最终确认

        输入: ResearchState.summary (总结)
        输出: ResearchState.verified_summary (验证后的最终摘要)
        处理流程：
        1. 对总结中的关键声明进行验证搜索
        2. 交叉检验信息的准确性
        3. 生成经过验证的最终摘要
        """
        print("\n" + "=" * 60)
        print("✅ 第三步：事实核查阶段")
        print("=" * 60)
        print(f"📋 输入: 总结内容 ({len(state['summary'])}字符)")

        try:
            # 1. 执行验证搜索
            print("🔍 正在进行事实验证搜索...")
            verification_query = f"验证事实 {state['topic']} 准确性 统计数据"

            try:
                verification_results = self.search.run(verification_query)
                print(f"✅ 验证搜索完成 ({len(verification_results)}字符)")
            except Exception as e:
                verification_results = f"验证搜索失败: {str(e)}"
                print(f"❌ 验证搜索失败: {str(e)}")

            # 2. 生成验证后的摘要
            print("🤖 正在生成验证后的最终摘要...")
            verified_summary = self._generate_verified_summary(
                state['topic'],
                state['summary'],
                verification_results
            )

            print(f"📊 核查结果:")
            print(f"   - 验证信息长度: {len(verification_results)} 字符")
            print(f"   - 最终摘要长度: {len(verified_summary)} 字符")

            # 更新状态
            new_state = state.copy()
            new_state.update({
                "verified_summary": verified_summary,
                "current_step": "completed",
                "messages": state["messages"] + [
                    HumanMessage(content="请进行事实核查"),
                    AIMessage(content="事实核查完成，生成最终验证摘要")
                ]
            })

            print("✅ 事实核查阶段完成，工作流结束")
            return new_state

        except Exception as e:
            error_msg = f"事实核查节点执行失败: {str(e)}"
            logger.error(error_msg)
            return self._handle_error(state, error_msg)

    def _generate_search_queries(self, topic: str) -> List[str]:
        """生成多样化的搜索查询"""
        return [
            f"{topic} 最新发展 2024",
            f"{topic} 统计数据 趋势分析",
            f"{topic} 专家观点 研究报告",
            f"{topic} 影响 案例分析"
        ]

    def _generate_research_report(self, topic: str, search_results: List[str]) -> str:
        """生成结构化研究报告"""
        research_prompt = f"""
        基于以下关于 "{topic}" 的搜索结果，创建一份全面、结构化的研究报告：

        搜索结果：
        {chr(10).join([f"来源 {i + 1}：{result[:500]}..." for i, result in enumerate(search_results)])}

        请按以下结构组织报告：
        ## 执行摘要
        ## 关键发现
        ## 最新发展和趋势
        ## 统计数据和事实
        ## 专家观点
        ## 结论和影响

        要求：准确、客观、有条理，引用具体数据和来源。
        """

        response = self.llm.invoke([HumanMessage(content=research_prompt)])
        return response.content

    def _generate_summary(self, topic: str, research_report: str) -> str:
        """生成精炼总结"""
        summary_prompt = f"""
        将以下关于 "{topic}" 的详细研究报告总结为简洁、信息丰富的摘要：

        研究报告：
        {research_report}

        总结要求：
        1. 突出最重要的3-5个关键发现
        2. 包含具体的数据和统计信息
        3. 保持客观和准确性
        4. 长度控制在300-500字
        5. 使用清晰的段落结构
        """

        response = self.llm.invoke([HumanMessage(content=summary_prompt)])
        return response.content

    def _generate_verified_summary(self, topic: str, summary: str, verification_results: str) -> str:
        """生成验证后的最终摘要"""
        fact_check_prompt = f"""
        使用验证信息对以下关于 "{topic}" 的摘要进行事实核查和最终完善：

        待核查摘要：
        {summary}

        验证信息来源：
        {verification_results}

        请执行以下任务：
        1. 验证摘要中关键声明的准确性
        2. 纠正任何可能的不准确信息
        3. 补充重要的遗漏信息
        4. 提供置信度评估
        5. 生成最终的权威摘要

        输出格式：
        ## 验证后摘要
        [最终摘要内容]

        ## 置信度评估
        [对信息准确性的评估]
        """

        response = self.llm.invoke([HumanMessage(content=fact_check_prompt)])
        return response.content

    def _handle_error(self, state: ResearchState, error_message: str) -> ResearchState:
        """统一错误处理"""
        new_state = state.copy()
        new_state.update({
            "current_step": "error",
            "error_message": error_message,
            "messages": state["messages"] + [
                AIMessage(content=f"❌ 错误: {error_message}")
            ]
        })
        return new_state

    def create_workflow(self):
        """创建工作流程图"""
        workflow = StateGraph(ResearchState)

        # 添加节点
        workflow.add_node("research", self.research_node)
        workflow.add_node("summarize", self.summarize_node)
        workflow.add_node("fact_check", self.fact_check_node)

        # 定义流程边
        workflow.set_entry_point("research")
        workflow.add_edge("research", "summarize")
        workflow.add_edge("summarize", "fact_check")
        workflow.add_edge("fact_check", END)

        return workflow.compile()

    def run_research(self, topic: str) -> dict:
        """
        运行完整的研究流程

        Args:
            topic (str): 研究主题

        Returns:
            dict: 包含完整结果和执行信息的字典
        """
        print("\n" + "🚀" * 20)
        print("🎯 启动LangGraph研究工作流")
        print("🚀" * 40)
        print(f"📋 研究主题: {topic}")
        print(f"⏰ 开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        try:
            # 初始化工作流
            app = self.create_workflow()

            # 初始状态
            initial_state = ResearchState(
                messages=[],
                topic=topic,
                search_queries=[],
                raw_search_results=[],
                research_report="",
                summary="",
                verified_summary="",
                current_step="research",
                error_message=None,
                timestamp=datetime.now().isoformat(),
                total_sources=0
            )

            # 执行工作流
            print(f"\n🔄 开始执行工作流...")
            result = app.invoke(initial_state)

            # 生成执行报告
            execution_report = self._generate_execution_report(result)

            return {
                "success": result["current_step"] == "completed",
                "final_summary": result["verified_summary"],
                "execution_report": execution_report,
                "full_state": result
            }

        except Exception as e:
            error_msg = f"工作流执行失败: {str(e)}"
            logger.error(error_msg)
            print(f"\n❌ {error_msg}")
            return {
                "success": False,
                "error": error_msg,
                "final_summary": "",
                "execution_report": None,
                "full_state": None
            }

    def _generate_execution_report(self, final_state: ResearchState) -> str:
        """生成详细的执行报告"""
        report = f"""
        📊 工作流执行报告
        {'=' * 50}

        📋 基本信息:
           • 研究主题: {final_state['topic']}
           • 执行时间: {final_state['timestamp']}
           • 最终状态: {final_state['current_step']}
           • 信息源数量: {final_state['total_sources']}

        🔍 第一步 - 研究阶段:
           • 搜索查询数: {len(final_state['search_queries'])}
           • 搜索结果数: {len(final_state['raw_search_results'])}
           • 研究报告长度: {len(final_state['research_report'])} 字符

        📝 第二步 - 总结阶段:
           • 总结长度: {len(final_state['summary'])} 字符
           • 压缩比: {len(final_state['summary']) / max(len(final_state['research_report']), 1):.2%}

        ✅ 第三步 - 事实核查阶段:
           • 最终摘要长度: {len(final_state['verified_summary'])} 字符
           • 消息历史条数: {len(final_state['messages'])}

        {'=' * 50}
                """.strip()

        return report

def main():
    """主函数 - 演示完整的研究流程"""
    try:
        # 初始化研究工具
        print("🔧 正在初始化研究工具...")
        crew = EnhancedLangGraphResearchCrew()

        # 设置研究主题
        topic = "人工智能对就业市场的影响"

        # 执行研究
        result = crew.run_research(topic)

        # 输出最终结果
        print("\n" + "🎉" * 20)
        print("📋 研究工作流完成!")
        print("🎉" * 40)

        if result["success"]:
            print("\n✅ 执行成功!")
            print(f"\n📊 执行报告:")
            print(result["execution_report"])

            print(f"\n📝 最终验证摘要:")
            print("-" * 50)
            print(result["final_summary"])
            print("-" * 50)

        else:
            print(f"\n❌ 执行失败: {result['error']}")

    except Exception as e:
        print(f"\n💥 程序执行异常: {str(e)}")
        logger.error(f"主函数执行失败: {str(e)}")

if __name__ == "__main__":
    main()