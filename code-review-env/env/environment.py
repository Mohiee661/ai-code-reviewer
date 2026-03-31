import random
from env.models import Observation, Action, Reward
from env.tasks import TASKS
from env.grader import grade


class CodeReviewEnv:
    def __init__(self):
        self.current_task = None
        self.done = False

    def reset(self) -> Observation:
        self.current_task = random.choice(TASKS)
        self.done = False
        return Observation(
            files=self.current_task.files,
            instruction="Review this pull request."
        )

    def step(self, action: Action) -> tuple:
        if self.current_task is None:
            raise RuntimeError("Call reset() before step().")
        if self.done:
            raise RuntimeError("Episode is done. Call reset() to start a new one.")

        reward = grade(action, self.current_task.expected, self.current_task.decision)
        self.done = True
        observation = Observation(
            files=self.current_task.files,
            instruction="Review this pull request."
        )
        info = {"task_id": self.current_task.id}
        return observation, reward, self.done, info

    def state(self) -> dict:
        if self.current_task is None:
            return {"current_task": None}
        return {
            "task_id": self.current_task.id,
            "expected_issues": [i.model_dump() for i in self.current_task.expected],
            "correct_decision": self.current_task.decision,
            "done": self.done,
        }
