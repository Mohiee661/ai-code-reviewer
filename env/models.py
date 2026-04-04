from typing import List, Literal, Optional
from pydantic import BaseModel


class Issue(BaseModel):
    file: str
    line: int
    type: str  # "syntax" | "logic" | "performance" | "security" | "code_quality"
    severity: Literal["low", "medium", "high"]
    description: str


class FileDiff(BaseModel):
    filename: str
    diff: str


class Observation(BaseModel):
    files: List[FileDiff]
    instruction: str
    persona: str = ""          # reviewer persona hint
    phase: str = "issues"      # "issues" | "decision"


class Action(BaseModel):
    issues: List[Issue] = []
    final_decision: Optional[Literal["approve", "request_changes"]] = None


class Reward(BaseModel):
    score: float   # 0.0 → 1.0
    feedback: str
