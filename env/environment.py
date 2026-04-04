from env.models import Observation, Action, Reward
from env.tasks import TASKS
from env.grader import grade


class CodeReviewEnv:
    def __init__(self):
        self.current_task = None
        self.phase = "issues"   # "issues" | "decision"
        self.pending_issues = []
        self._task_index = 0    # deterministic cycling through tasks

    def reset(self, task_id: str = None) -> Observation:
        """Start a new episode. Cycles tasks deterministically unless task_id given."""
        if task_id:
            task = next((t for t in TASKS if t.id == task_id), None)
            if task is None:
                raise ValueError(f"Unknown task_id: {task_id!r}")
            self.current_task = task
        else:
            self.current_task = TASKS[self._task_index % len(TASKS)]
            self._task_index += 1

        self.phase = "issues"
        self.pending_issues = []
        return self._observation()

    def step(self, action: Action) -> tuple:
        if self.current_task is None:
            raise RuntimeError("Call reset() before step().")

        if self.phase == "issues":
            # Phase 1: store submitted issues, ask for decision
            self.pending_issues = action.issues
            self.phase = "decision"
            obs = self._observation()
            return obs, Reward(score=0.0, feedback="Issues received. Submit your final_decision."), False, {"task_id": self.current_task.id, "phase": "decision"}

        # Phase 2: evaluate everything together
        full_action = Action(issues=self.pending_issues, final_decision=action.final_decision)
        reward = grade(full_action, self.current_task.expected, self.current_task.decision)
        self.phase = "done"
        return self._observation(), reward, True, {"task_id": self.current_task.id, "phase": "done"}

    def state(self) -> dict:
        if self.current_task is None:
            return {"current_task": None}
        return {
            "task_id": self.current_task.id,
            "persona": self.current_task.persona,
            "phase": self.phase,
            "pending_issues": [i.model_dump() for i in self.pending_issues],
            "expected_issues": [i.model_dump() for i in self.current_task.expected],
            "correct_decision": self.current_task.decision,
        }

    # ── internal ──────────────────────────────────────────────────────────────

    def _observation(self) -> Observation:
        instruction = (
            f"{self.current_task.persona} Review this pull request and identify all issues."
            if self.phase == "issues"
            else f"{self.current_task.persona} You have submitted your issues. Now provide your final_decision: approve or request_changes."
        )
        return Observation(
            files=self.current_task.files,
            instruction=instruction,
            persona=self.current_task.persona,
            phase=self.phase,
        )
