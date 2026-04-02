"""
inference.py — OpenEnv baseline script for the PR Code Review environment.

Reads credentials from environment variables:
  API_BASE_URL  : OpenAI-compatible API base URL
  MODEL_NAME    : model identifier (e.g. gpt-4o)
  HF_TOKEN      : API key / Hugging Face token

Runs all 3 tasks (easy, medium, hard) deterministically and prints scores.
"""
import json
import os
import sys
from openai import OpenAI
from env.environment import CodeReviewEnv
from env.models import Action, Issue
from env.tasks import TASKS

# ── credentials ──────────────────────────────────────────────────────────────
API_BASE_URL = os.environ.get("API_BASE_URL", "https://api.openai.com/v1")
MODEL_NAME   = os.environ.get("MODEL_NAME", "gpt-4o")
HF_TOKEN     = os.environ.get("HF_TOKEN") or os.environ.get("OPENAI_API_KEY")

TEMPERATURE = 0
MAX_TOKENS  = 1024

SYSTEM_PROMPT = """\
You are an expert code reviewer. You will be given a pull request diff.
Identify every issue and decide whether to approve or request changes.

Respond with ONLY valid JSON — no markdown, no explanation:
{
  "issues": [
    {
      "file": "<filename>",
      "line": <integer>,
      "type": "<syntax|logic|performance|security|code_quality>",
      "severity": "<low|medium|high>",
      "description": "<concise description>"
    }
  ],
  "final_decision": "<approve|request_changes>"
}"""


def build_prompt(observation) -> str:
    parts = ["Review the following pull request:\n"]
    for f in observation.files:
        parts.append(f"### {f.filename}\n```diff\n{f.diff}\n```\n")
    return "\n".join(parts)


def parse_action(raw: str) -> Action:
    try:
        # strip markdown code fences if model wraps output
        text = raw.strip()
        if text.startswith("```"):
            text = "\n".join(text.split("\n")[1:])
            text = text.rstrip("`").strip()
        data = json.loads(text)
        issues = [Issue(**i) for i in data.get("issues", [])]
        decision = data.get("final_decision", "approve")
        if decision not in ("approve", "request_changes"):
            decision = "approve"
        return Action(issues=issues, final_decision=decision)
    except Exception as e:
        print(f"  [warn] parse failed: {e} — using empty action")
        return Action(issues=[], final_decision="approve")


def run_task(client, env, task):
    """Force a specific task and run one episode."""
    env.current_task = task
    env.done = False
    from env.models import Observation
    observation = Observation(files=task.files, instruction="Review this pull request.")

    if client:
        try:
            resp = client.chat.completions.create(
                model=MODEL_NAME,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user",   "content": build_prompt(observation)},
                ],
                temperature=TEMPERATURE,
                max_tokens=MAX_TOKENS,
            )
            raw = resp.choices[0].message.content or ""
        except Exception as exc:
            print(f"  [warn] API call failed: {exc} — using empty action")
            raw = ""
        action = parse_action(raw)
    else:
        action = Action(issues=[], final_decision="approve")

    _, reward, done, info = env.step(action)
    return reward, info


def main():
    use_api = bool(HF_TOKEN)
    client = None
    if use_api:
        client = OpenAI(api_key=HF_TOKEN, base_url=API_BASE_URL)
        print(f"[info] model={MODEL_NAME}  base={API_BASE_URL}")
    else:
        print("[warn] No HF_TOKEN / OPENAI_API_KEY found — running dummy baseline (score=0)")

    env = CodeReviewEnv()
    total = 0.0

    print("\n" + "="*55)
    for task in TASKS:
        reward, info = run_task(client, env, task)
        total += reward.score
        print(f"  task={info['task_id']:<8}  score={reward.score:.2f}  {reward.feedback}")

    avg = total / len(TASKS)
    print("="*55)
    print(f"  average score: {avg:.2f}  ({len(TASKS)} tasks)")
    print("="*55 + "\n")
    return avg


if __name__ == "__main__":
    main()
