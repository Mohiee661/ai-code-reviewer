import logging
from env.models import Observation, Action, Reward
from env.tasks import TASKS
from env.grader import grade

log = logging.getLogger(__name__)


class CodeReviewEnv:
    def __init__(self):
        self.current_task  = None
        self.phase         = "issues"
        self.pending_issues = []
        self._task_index   = 0
        self._last_metrics = {}   # precision/recall from last completed episode

    def reset(self, task_id: str = None) -> Observation:
        if task_id:
            task = next((t for t in TASKS if t.id == task_id), None)
            if task is None:
                raise ValueError(f"Unknown task_id: {task_id!r}")
            self.current_task = task
        else:
            self.current_task = TASKS[self._task_index % len(TASKS)]
            self._task_index += 1

        self.phase          = "issues"
        self.pending_issues = []
        log.info("Reset → task=%s", self.current_task.id)
        return self._observation()

    def step(self, action: Action) -> tuple:
        if self.current_task is None:
            raise RuntimeError("Call reset() before step().")

        if self.phase == "issues":
            self.pending_issues = action.issues
            self.phase = "decision"
            log.info("Step phase: issues → decision  task=%s", self.current_task.id)
            reward = Reward(score=0.0, feedback="Issues received. Submit your final_decision.")
            return self._observation(), reward, False, {"task_id": self.current_task.id, "phase": "decision"}

        full_action = Action(issues=self.pending_issues, final_decision=action.final_decision)
        reward = grade(full_action, self.current_task.expected, self.current_task.decision)
        self._last_metrics = _extract_metrics(reward.feedback)
        self.phase = "done"
        log.info("Step phase: decision → done  task=%s  score=%.2f", self.current_task.id, reward.score)
        return self._observation(), reward, True, {"task_id": self.current_task.id, "phase": "done"}

    def state(self) -> dict:
        if self.current_task is None:
            return {"current_task": None}
        return {
            "task_id":          self.current_task.id,
            "persona":          self.current_task.persona,
            "phase":            self.phase,
            "pending_issues":   [i.model_dump() for i in self.pending_issues],
            "expected_issues":  [i.model_dump() for i in self.current_task.expected],
            "correct_decision": self.current_task.decision,
        }

    def metrics(self) -> dict:
        return self._last_metrics

    def _observation(self) -> Observation:
        meta = self.current_task.pr_metadata
        pr_context = (
            f'PR: "{meta.title}" — {meta.description}'
            if meta else ""
        )
        if self.phase == "issues":
            instruction = (
                f"{self.current_task.persona} "
                f"{pr_context} "
                "Review the diff below. Identify ALL issues: correctness bugs, "
                "security vulnerabilities, performance regressions, and code quality problems. "
                "Report exact file, line, type, severity, and a clear actionable description."
            )
        else:
            instruction = (
                f"{self.current_task.persona} "
                "You have submitted your issues. "
                "Based on the severity and number of issues found, provide your final_decision: "
                "approve (no blocking issues) or request_changes (bugs, security, or significant problems)."
            )
        return Observation(
            files=self.current_task.files,
            instruction=instruction,
            persona=self.current_task.persona,
            phase=self.phase,
            pr_metadata=self.current_task.pr_metadata,
        )


def _extract_metrics(feedback: str) -> dict:
    """Parse precision/recall from grader feedback string."""
    precision = recall = 0.0
    # Feedback contains: "Precision: 0.75  Recall: 0.50."
    for segment in feedback.split("Precision:")[1:]:
        try:
            precision = float(segment.strip().split()[0])
        except (ValueError, IndexError):
            pass
    for segment in feedback.split("Recall:")[1:]:
        try:
            recall = float(segment.strip().split()[0].rstrip("."))
        except (ValueError, IndexError):
            pass
    hallucination_rate = round(1.0 - precision, 4)
    return {
        "precision":          round(precision, 4),
        "recall":             round(recall, 4),
        "hallucination_rate": hallucination_rate,
    }
