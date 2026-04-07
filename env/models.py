from typing import List, Literal, Optional, Dict
from pydantic import BaseModel


class Issue(BaseModel):
    file: str
    line: int
    type: str
    severity: Literal["low", "medium", "high"]
    description: str


class FileDiff(BaseModel):
    filename: str
    diff: str
    language: str = "python"
    lines_added: int = 0
    lines_removed: int = 0


class PRMetadata(BaseModel):
    title: str
    description: str
    author_intent: str


class Observation(BaseModel):
    files: List[FileDiff]
    instruction: str
    persona: str = ""
    phase: str = "issues"
    pr_metadata: Optional[PRMetadata] = None


class Action(BaseModel):
    issues: List[Issue] = []
    final_decision: Optional[Literal["approve", "request_changes"]] = None


class RewardBreakdown(BaseModel):
    issue_coverage: float
    severity_awareness: float
    precision: float
    explanation_quality: float
    decision_correctness: float


class Reward(BaseModel):
    score: float
    feedback: str
    breakdown: Optional[RewardBreakdown] = None
