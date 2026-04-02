import json
import os
from openai import OpenAI
from env.environment import CodeReviewEnv
from env.models import Action, Issue

SYSTEM_PROMPT = """\
You are an expert code reviewer. You will be given a pull request diff.
Your job is to identify issues and decide whether to approve or request changes.

Respond with ONLY valid JSON in this exact format:
{
  "issues": [
    {
      "file": "<filename>",
      "line": <line_number>,
      "type": "<syntax|logic|performance|security|code_quality>",
      "severity": "<low|medium|high>",
      "description": "<concise description>"
    }
  ],
  "final_decision": "<approve|request_changes>"
}

Do not include any explanation or text outside the JSON."""


def build_user_prompt(observation) -> str:
    parts = ["Review the following pull request:\n"]
    for f in observation.files:
        parts.append(f"### {f.filename}\n```diff\n{f.diff}\n```\n")
    return "\n".join(parts)


def parse_action(raw: str) -> Action:
    """Parse model output into an Action, returning empty action on failure."""
    try:
        data = json.loads(raw)
        issues = [Issue(**i) for i in data.get("issues", [])]
        decision = data.get("final_decision", "approve")
        if decision not in ("approve", "request_changes"):
            decision = "approve"
        return Action(issues=issues, final_decision=decision)
    except Exception as e:
        print(f"[warn] Failed to parse model response: {e}")
        return Action(issues=[], final_decision="approve")


def main():
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("[warn] No OPENAI_API_KEY found. Running dummy baseline.")
        use_api = False
    else:
        print("[info] Using OpenAI API")
        client = OpenAI(api_key=api_key)
        use_api = True

    env = CodeReviewEnv()
    observation = env.reset()
    print(f"[info] Task: {env.state()['task_id']}\n")

    if use_api:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": build_user_prompt(observation)},
            ],
            temperature=0,
        )
        raw = response.choices[0].message.content
        print(f"[model output]\n{raw}\n")
        action = parse_action(raw)
    else:
        print("[info] Dummy action: no issues, decision=approve\n")
        action = Action(issues=[], final_decision="approve")

    _, reward, done, info = env.step(action)

    print(f"[result] task_id : {info['task_id']}")
    print(f"[result] score   : {reward.score:.2f}")
    print(f"[result] feedback: {reward.feedback}")


if __name__ == "__main__":
    main()
