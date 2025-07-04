import os

from langchain_core.messages import HumanMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate, PromptTemplate, MessagesPlaceholder
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv

load_dotenv()

# 设置 OPENAI_API_KEY 环境变量
os.environ["OPENAI_API_KEY"] = os.getenv("QWEN_API_KEY", "")

llm = ChatOpenAI(
    model = "qwen-plus-latest",
    temperature = 0.7,
    max_tokens = 1024,
    base_url = "https://dashscope.aliyuncs.com/compatible-mode/v1"
)

examples = [
    {
        "question": "电话和电灯的发明者是否毕业于同一所大学？",
        "answer":
            """
            这里需要跟进问题吗：是的。
            跟进：电话的发明者是谁？
            中间答案：电话的发明者是Alexander Graham Bell。
            跟进：Alexander Graham Bell毕业于哪所大学？
            中间答案：Alexander Graham Bell没有正式大学学位，他在爱丁堡大学短暂学习过。
            跟进：电灯的发明者是谁？
            中间答案：电灯的发明者是Thomas Edison。
            跟进：Thomas Edison毕业于哪所大学？
            中间答案：Thomas Edison没有大学学位，他是自学成才的发明家。
            所以最终答案是：不是
            """
    }
]


prompt_template = ChatPromptTemplate.from_messages([
    ("system", "You are a helpful assistant"),
    #可以传入一组消息
    MessagesPlaceholder("msgs")
])

result = prompt_template.invoke({"msgs": [HumanMessage(content="您好!"),
                                          HumanMessage(content="通义千问!")]})

output_parser = StrOutputParser()

chain = llm | output_parser

resp = chain.invoke(result)

print(resp)