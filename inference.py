"""
inference.py — OpenEnv baseline for the PR Code Review environment.

Environment variables:
  API_BASE_URL  : OpenAI-compatible base URL  (default: https://api.openai.com/v1)
  MODEL_NAME    : model identifier             (default: gpt-4o)
  HF_TOKEN      : API key / HF token

Runs all tasks deterministically (temperature=0) using the two-phase protocol:
  Phase 1 → submit issues only
  Phase 2 → submit final_decision only
"""
import json, os
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

Respond with ONLY valid JSON — no markdown, no explanation:
{{
  "issues": [
    {{
      "file": "<filename>",
      "line": <integer>,
      "type": "<syntax|logic|performance|security|code_quality>",
      "severity": "<low|medium|high>",
      "description": "<concise description>"
    }}
  ]
}}"""

DECISION_PROMPT = """\
You are an expert code reviewer. Based on the issues you identified, decide whether to approve or request changes.

Respond with ONLY valid JSON — no markdown, no explanation:
{{
  "final_decision": "<approve|request_changes>"
}}"""


def call_llm(client, system: str, user: str) -> str:
    try:
        resp = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
            temperature=TEMPERATURE,
            max_tokens=MAX_TOKENS,
        )
        return resp.choices[0].message.content or ""
    except Exception as e:
        print(f"  [warn] API error: {e}")
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
    # Phase 1 — issues
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

    obs2, reward1, done1, info1 = env.step(Action(issues=issues))
    assert not done1, "Expected phase 1 to not be terminal"

    # Phase 2 — decision
    if client:
        raw2 = call_llm(client, DECISION_PROMPT, build_diff_prompt(obs2))
        data2 = parse_json(raw2)
        decision = data2.get("final_decision", "approve")
        if decision not in ("approve", "request_changes"):
            decision = "approve"
    else:
        decision = "approve"

    _, reward2, done2, info2 = env.step(Action(final_decision=decision))
    assert done2, "Expected phase 2 to be terminal"
    return reward2, info2


def main():
    client = None
    if HF_TOKEN:
        client = OpenAI(api_key=HF_TOKEN, base_url=API_BASE_URL)
        print(f"[info] model={MODEL_NAME}  base={API_BASE_URL}")
    else:
        print("[warn] No token found — running dummy baseline (score=0)")

    env = CodeReviewEnv()
    total = 0.0

    print("\n" + "=" * 60)
    for task in TASKS:
        reward, info = run_task(client, env, task)
        total += reward.score
        print(f"  task={info['task_id']:<8}  score={reward.score:.2f}  {reward.feedback}")

    avg = total / len(TASKS)
    print("=" * 60)
    print(f"  average score: {avg:.2f}  ({len(TASKS)} tasks)")
    print("=" * 60 + "\n")
    return avg


if __name__ == "__main__":
    main()
