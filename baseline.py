import os

from openai import OpenAI

from env.environment import CodeReviewEnv
from env.models import Action, Issue
from inference import (
    DECISION_PROMPT,
    ISSUES_PROMPT,
    MODEL_NAME,
    build_context_prompt,
    call_llm,
    parse_json,
)


def parse_issues(raw: str) -> list[Issue]:
    """Parse model issue output, returning an empty list on failure."""
    issues = []
    for item in parse_json(raw).get("issues", []):
        try:
            issues.append(Issue(**item))
        except Exception as exc:
            print(f"[warn] Ignoring invalid issue: {exc}")
    return issues


def parse_decision(raw: str) -> str:
    decision = parse_json(raw).get("final_decision", "approve")
    if decision not in ("approve", "request_changes"):
        return "approve"
    return decision


def offline_issues_for(task_id: str) -> list[Issue]:
    """Offline smoke-test answer for the easiest deterministic task."""
    if task_id != "easy":
        return []
    return [
        Issue(
            file="utils/list_helpers.py",
            line=4,
            type="logic",
            severity="medium",
            description="Off-by-one slice returns one extra item before the requested last n elements. Use len(items) - n.",
        ),
        Issue(
            file="utils/list_helpers.py",
            line=9,
            type="logic",
            severity="medium",
            description="Loop extends to len(items) + 1, producing an extra empty chunk. Use range(0, len(items), size).",
        ),
    ]


def main():
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("[warn] No OPENAI_API_KEY found. Running deterministic offline smoke baseline.")
        client = None
    else:
        print(f"[info] Using OpenAI API model={MODEL_NAME}")
        client = OpenAI(api_key=api_key)

    env = CodeReviewEnv()
    observation = env.reset(task_id=os.environ.get("TASK_ID") or "easy")
    task_id = env.state()["task_id"]
    print(f"[info] Task: {task_id}\n")

    if client:
        prompt = ISSUES_PROMPT.format(
            title=observation.pr_metadata.title,
            description=observation.pr_metadata.description,
            intent=observation.pr_metadata.author_intent,
        )
        raw = call_llm(client, prompt, build_context_prompt(observation))
        print(f"[model issues]\n{raw}\n")
        issues = parse_issues(raw)
    else:
        issues = offline_issues_for(task_id)
        print(f"[info] Offline issues: {len(issues)}\n")

    _, reward1, done1, info1 = env.step(Action(issues=issues))
    print(f"[step 1] done    : {done1}")
    print(f"[step 1] phase   : {info1['phase']}")
    print(f"[step 1] feedback: {reward1.feedback}\n")

    if client:
        issues_summary = "\n".join(
            f"- {issue.file}:{issue.line} [{issue.severity}] {issue.description[:80]}"
            for issue in issues[:8]
        ) or "No issues found"
        raw = call_llm(
            client,
            DECISION_PROMPT.format(num_issues=len(issues), issues_summary=issues_summary),
            "",
        )
        print(f"[model decision]\n{raw}\n")
        decision = parse_decision(raw)
    else:
        decision = "request_changes" if issues else "approve"

    _, reward, done, info = env.step(Action(final_decision=decision))

    print(f"[result] task_id : {info['task_id']}")
    print(f"[result] decision: {decision}")
    print(f"[result] done    : {done}")
    print(f"[result] score   : {reward.score:.2f}")
    print(f"[result] feedback: {reward.feedback}")


if __name__ == "__main__":
    main()
