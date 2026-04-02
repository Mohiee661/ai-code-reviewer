import random
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from typing import Any, Optional
from uuid import uuid4
from openenv.core.env_server.types import Action, Observation, State
from openenv.core.env_server.environment import Environment

from env.models import FileDiff, Issue
from env.tasks import TASKS
from env.grader import grade as grade_action
from env.models import Action as ReviewAction


class CodeReviewEnvironment(Environment):
    """OpenEnv environment for AI pull request code review."""

    def __init__(self):
        self._current_task = None
        self._done = False
        self._state_obj = State(episode_id=str(uuid4()), step_count=0)

    def reset(self, seed=None, episode_id=None, **kwargs) -> Observation:
        self._current_task = random.choice(TASKS)
        self._done = False
        self._state_obj = State(
            episode_id=episode_id or str(uuid4()),
            step_count=0,
        )
        return Observation(
            done=False,
            reward=0.0,
            metadata={
                "files": [{"filename": f.filename, "diff": f.diff} for f in self._current_task.files],
                "instruction": "Review this pull request.",
                "task_id": self._current_task.id,
            },
        )

    def step(self, action: Action, timeout_s=None, **kwargs) -> Observation:
        self._state_obj.step_count += 1

        if self._current_task is None:
            return Observation(done=True, reward=0.0, metadata={"error": "Call reset() first."})
        if self._done:
            return Observation(done=True, reward=0.0, metadata={"error": "Episode done. Call reset()."})

        # Parse action from metadata
        try:
            meta = action.metadata if hasattr(action, "metadata") and action.metadata else {}
            issues_data = meta.get("issues", [])
            decision = meta.get("final_decision", "approve")
            issues = [Issue(**i) for i in issues_data]
            review_action = ReviewAction(issues=issues, final_decision=decision)
        except Exception as e:
            self._done = True
            return Observation(done=True, reward=0.0, metadata={"error": str(e)})

        reward_obj = grade_action(review_action, self._current_task.expected, self._current_task.decision)
        self._done = True

        return Observation(
            done=True,
            reward=reward_obj.score,
            metadata={
                "task_id": self._current_task.id,
                "score": reward_obj.score,
                "feedback": reward_obj.feedback,
                "files": [{"filename": f.filename, "diff": f.diff} for f in self._current_task.files],
            },
        )

    async def step_async(self, action: Action, timeout_s=None, **kwargs) -> Observation:
        return self.step(action, timeout_s=timeout_s, **kwargs)

    @property
    def state(self) -> State:
        return self._state_obj