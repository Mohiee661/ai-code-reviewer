from typing import List, Literal
from pydantic import BaseModel


class Issue(BaseModel):
    file: str
    line: int
    type: str  # e.g. "syntax", "security", "code_quality"
    severity: Literal["low", "medium", "high"]
    description: str


class FileDiff(BaseModel):
    filename: str
    diff: str


class Observation(BaseModel):
    files: List[FileDiff]
    instruction: str


class Action(BaseModel):
    issues: List[Issue]
    final_decision: Literal["approve", "request_changes"]


class Reward(BaseModel):
    score: float  # 0.0 → 1.0
    feedback: str
