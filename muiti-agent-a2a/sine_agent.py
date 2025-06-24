from python_a2a import A2AServer, agent, skill, TaskState, TaskStatus
from python_a2a import run_server
import math
import re


@agent(
    name="Sine Agent",
    description="一个可以计算正弦函数值的 Agent",
    version="1.0.0",
)
class SineAgent(A2AServer):

    @skill(
        name="Get Sine",
        description="计算给定角度的正弦值",
        tags=["sine", "sin"]
    )
    def get_sine(self, angle: float) -> float:
        """
        计算给定角度的正弦值。

        :param angle: 角度值，单位为度，例如 90 表示直角。
        :return: 正弦值。
        """

        # 将角度转换为弧度
        radians = math.radians(angle)
        return math.sin(radians)

    def handle_task(self, task):

        input_message = task.message["content"]["text"]

        match = re.search(r"([-+]?[0-9]*\.?[0-9]+)", input_message)
        number = float(match.group(1)) if match else None

        if number is not None:
            sine_output = self.get_sine(number)
        else:
            sine_output = None  # 或者抛出异常，或返回错误信息

        task.artifacts = [{
            "parts": [{"type": "text", "text": f"正弦值为: {sine_output}"}]
        }]

        task.status = TaskStatus(state=TaskState.COMPLETED)

        return task


if __name__ == "__main__":
    agent = SineAgent()
    run_server(agent, port=4737)
