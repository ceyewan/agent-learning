from python_a2a import A2AServer, agent, skill, TaskState, TaskStatus
from python_a2a import run_server
import math
import re


@agent(
    name="Tangent Agent",
    description="一个可以计算正切函数值的 Agent",
    version="1.0.0",
)
class TangentAgent(A2AServer):

    @skill(
        name="Get Tangent",
        description="计算给定角度的正切值",
        tags=["tangent", "tan"]
    )
    def get_tangent(self, angle: float) -> float:
        """
        计算给定角度的正切值。

        :param angle: 角度值，单位为度，例如 45 表示直角一半。
        :return: 正切值。
        """
        radians = math.radians(angle)
        return math.tan(radians)

    def handle_task(self, task):
        input_message = task.message["content"]["text"]
        match = re.search(r"([-+]?[0-9]*\.?[0-9]+)", input_message)
        number = float(match.group(1)) if match else None

        if number is not None:
            tangent_output = self.get_tangent(number)
        else:
            tangent_output = None  # 或者抛出异常，或返回错误信息

        task.artifacts = [{
            "parts": [{"type": "text", "text": f"正切值为: {tangent_output}"}]
        }]
        task.status = TaskStatus(state=TaskState.COMPLETED)
        return task


if __name__ == "__main__":
    agent = TangentAgent()
    run_server(agent, port=4739)
