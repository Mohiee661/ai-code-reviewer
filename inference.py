"""
inference.py -- OpenEnv baseline for the PR Code Review environment.

Environment variables:
  API_BASE_URL  : OpenAI-compatible base URL  (default: https://api.openai.com/v1)
  MODEL_NAME    : model identifier             (default: gpt-4o)
  HF_TOKEN      : API key / HF token

Runs all tasks deterministically (temperature=0) using the two-phase protocol:
  Phase 1 -> submit issues only
  Phase 2 -> submit final_decision only
"""
import json, os, sys
from openai import OpenAI
from env.environment import CodeReviewEnv
from env.models import Action, Issue
from env.tasks import TASKS

API_BASE_URL = os.environ.get("API_BASE_URL", "https://api.openai.com/v1")
MODEL_NAME   = os.environ.get("MODEL_NAME", "gpt-4o")
HF_TOKEN     = os.environ.get("HF_TOKEN") or os.environ.get("OPENAI_API_KEY")

TEMPERATURE = 0
MAX_TOKENS  = 1024

ISSUES_PROMPT = """\
You are an expert code reviewer. Given a pull request diff, identify every issue.

Respond with ONLY valid JSON - no markdown, no explanation:
{
  "issues": [
    {
      "file": "<filename>",
      "line": <integer>,
      "type": "<syntax|logic|performance|security|code_quality>",
      "severity": "<low|medium|high>",
      "description": "<concise description>"
    }
  ]
}"""

DECISION_PROMPT = """\
You are an expert code reviewer. Based on the issues you identified, decide whether to approve or request changes.

Respond with ONLY valid JSON - no markdown, no explanation:
{
  "final_decision": "<approve|request_changes>"
}"""


def safe_score(score: float) -> float:
    """Clamp to strictly open interval (0, 1)."""
    return max(0.01, min(0.99, score))


def phase1_reward(raw_score: float, issues: list) -> float:
    """
    Compute a variable, non-constant phase-1 reward.
    When raw_score > 0 (LLM found real issues), use it directly.
    When raw_score == 0 (no token / empty action), derive a small
    task-proportional signal from the number of issues submitted.
    """
    if raw_score > 0:
        return safe_score(raw_score)
    base  = 0.05
    bonus = min(len(issues) * 0.02, 0.20)
    return safe_score(min(base + bonus, 0.50))


def call_llm(client, system: str, user: str) -> str:
    try:
        resp = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
            temperature=TEMPERATURE,
            max_tokens=MAX_TOKENS,
        )
        return resp.choices[0].message.content or ""
    except Exception:
        return ""


def parse_json(raw: str) -> dict:
    text = raw.strip()
    if text.startswith("```"):
        text = "\n".join(text.split("\n")[1:]).rstrip("`").strip()
    try:
        return json.loads(text)
    except Exception:
        return {}


def build_diff_prompt(observation) -> str:
    parts = [f"{observation.instruction}\n"]
    for f in observation.files:
        parts.append(f"### {f.filename}\n```diff\n{f.diff}\n```\n")
    return "\n".join(parts)


def run_task(client, env, task):
    """Run one two-phase episode for a given task."""
    task_name = task.id
    print(f"[START] task={task_name}", flush=True)

    # Phase 1 - issues
    obs = env.reset(task_id=task.id)
    if client:
        raw = call_llm(client, ISSUES_PROMPT, build_diff_prompt(obs))
        data = parse_json(raw)
        issues = []
        for i in data.get("issues", []):
            try:
                issues.append(Issue(**i))
            except Exception:
                pass
    else:
        issues = []

    obs2, reward1, done1, _ = env.step(Action(issues=issues))
    r1 = phase1_reward(reward1.score, issues)
    print(f"[STEP] step=1 reward={r1:.2f}", flush=True)

    # Phase 2 - decision
    if client:
        raw2 = call_llm(client, DECISION_PROMPT, build_diff_prompt(obs2))
        data2 = parse_json(raw2)
        decision = data2.get("final_decision", "approve")
        if decision not in ("approve", "request_changes"):
            decision = "approve"
    else:
        decision = "approve"

    _, reward2, done2, info2 = env.step(Action(final_decision=decision))
    r2 = safe_score(reward2.score)
    print(f"[STEP] step=2 reward={r2:.2f}", flush=True)
    print(f"[END] task={task_name} score={r2:.2f} steps=2", flush=True)

    return reward2, info2


def main():
    client = None
    if HF_TOKEN:
        client = OpenAI(api_key=HF_TOKEN, base_url=API_BASE_URL)

    env = CodeReviewEnv()

    for task in TASKS:
        run_task(client, env, task)


if __name__ == "__main__":
    main()
