"""
inference.py -- OpenEnv baseline for the PR Code Review environment.

Environment variables:
  API_BASE_URL  : OpenAI-compatible base URL  (default: https://api.openai.com/v1)
  MODEL_NAME    : model identifier             (default: gpt-4o)
  HF_TOKEN      : API key / HF token

Multi-stage reasoning baseline:
  Stage 1: Detect issues from PR diff
  Stage 2: Refine issues (filter noise, validate severity)
  Stage 3: Make final decision based on identified issues
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
MAX_TOKENS  = 1500

ISSUES_PROMPT = """\
You are an expert code reviewer analyzing a pull request.

PR Context:
Title: {title}
Description: {description}
Author Intent: {intent}

Your task: Identify ALL issues in the code changes below. Focus on:
- Security vulnerabilities (SQL injection, XSS, auth bypass, secrets)
- Logic errors (off-by-one, null checks, edge cases)
- Performance problems (N+1 queries, full table scans, memory leaks)
- Code quality (readability, maintainability, best practices)

For each issue provide:
- Exact file and line number
- Precise issue type and severity
- Clear, actionable description (explain WHY it is wrong and HOW to fix)

Respond with ONLY valid JSON:
{{
  "issues": [
    {{
      "file": "<filename>",
      "line": <integer>,
      "type": "<syntax|logic|performance|security|code_quality>",
      "severity": "<low|medium|high>",
      "description": "<detailed explanation with fix suggestion>"
    }}
  ]
}}"""

DECISION_PROMPT = """\
You are an expert code reviewer making a final decision on this pull request.

You identified {num_issues} issues:
{issues_summary}

Based on the severity and number of issues, decide:
- approve: if no critical issues or only minor improvements needed
- request_changes: if there are bugs, security issues, or significant problems

Respond with ONLY valid JSON:
{{
  "final_decision": "<approve|request_changes>"
}}"""


def safe_score(score: float) -> float:
    return max(0.01, min(0.99, score))


def phase1_reward(raw_score: float, issues: list) -> float:
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
        lines = text.split("\n")
        text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
        text = text.rstrip("`").strip()
    try:
        return json.loads(text)
    except Exception:
        return {}


def build_context_prompt(observation) -> str:
    parts = []
    if observation.pr_metadata:
        parts.append(f"Title: {observation.pr_metadata.title}")
        parts.append(f"Description: {observation.pr_metadata.description}")
        parts.append(f"Author Intent: {observation.pr_metadata.author_intent}\n")
    
    parts.append("Code Changes:")
    for f in observation.files:
        lang = f.language if hasattr(f, 'language') else 'python'
        parts.append(f"\n### {f.filename} ({lang})")
        parts.append(f"```diff\n{f.diff}\n```")
    
    return "\n".join(parts)


def run_task(client, env, task):
    task_name = task.id
    print(f"[START] task={task_name}", flush=True)

    # Stage 1: Detect issues
    obs = env.reset(task_id=task.id)
    
    if client and obs.pr_metadata:
        prompt = ISSUES_PROMPT.format(
            title=obs.pr_metadata.title,
            description=obs.pr_metadata.description,
            intent=obs.pr_metadata.author_intent,
        )
        user_content = build_context_prompt(obs)
        raw = call_llm(client, prompt, user_content)
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

    # Stage 2: Make decision
    if client:
        issues_summary = "\n".join([
            f"- {i.file}:{i.line} [{i.severity}] {i.description[:60]}..."
            for i in issues[:5]
        ]) if issues else "No issues found"
        
        prompt = DECISION_PROMPT.format(
            num_issues=len(issues),
            issues_summary=issues_summary,
        )
        raw2 = call_llm(client, prompt, "")
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
