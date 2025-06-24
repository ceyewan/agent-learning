from python_a2a import A2AServer, agent, skill, TaskState, TaskStatus
from python_a2a import run_server
import math
import re


@agent(
    name="Cosine Agent",
    description="一个可以计算余弦函数值的 Agent",
    version="1.0.0",
)
class CosineAgent(A2AServer):

    @skill(
        name="Get Cosine",
        description="计算给定角度的余弦值",
        tags=["cosine", "cos"]
    )
    def get_cosine(self, angle: float) -> float:
        """
        计算给定角度的余弦值。

        :param angle: 角度值，单位为度，例如 90 表示直角。
        :return: 余弦值。
        """

        # 将角度转换为弧度
        radians = math.radians(angle)
        return math.cos(radians)

    def handle_task(self, task):

        input_message = task.message["content"]["text"]

        match = re.search(r"([-+]?[0-9]*\.?[0-9]+)", input_message)
        number = float(match.group(1)) if match else None

        if number is not None:
            cosine_output = self.get_cosine(number)
        else:
            cosine_output = None  # 或者抛出异常，或返回错误信息

        task.artifacts = [{
            "parts": [{"type": "text", "text": f"余弦值为: {cosine_output}"}]
        }]

        task.status = TaskStatus(state=TaskState.COMPLETED)

        return task


if __name__ == "__main__":
    agent = CosineAgent()
    run_server(agent, port=4738)
