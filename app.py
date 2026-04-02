import gradio as gr
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from env.environment import CodeReviewEnv
from env.models import Action, Issue
import json

env = CodeReviewEnv()


def run_review(issues_json: str, decision: str):
    try:
        issues_data = json.loads(issues_json) if issues_json.strip() else []
        issues = [Issue(**i) for i in issues_data]
    except Exception as e:
        return "", "", f"Invalid JSON: {e}"

    action = Action(issues=issues, final_decision=decision)
    obs, reward, done, info = env.step(action)
    return f"{reward.score:.2f}", info["task_id"], reward.feedback


def reset_env():
    obs = env.reset()
    diff_text = "\n\n".join(f"### {f.filename}\n{f.diff}" for f in obs.files)
    return diff_text, env.state()["task_id"]


with gr.Blocks(title="AI Code Reviewer") as demo:
    gr.Markdown("# AI Code Reviewer\nReview a pull request diff and get a score.")

    with gr.Row():
        reset_btn = gr.Button("Load New PR", variant="primary")

    task_id = gr.Textbox(label="Task ID", interactive=False)
    diff_box = gr.Textbox(label="PR Diff", lines=20, interactive=False)

    gr.Markdown("### Your Review")
    issues_box = gr.Textbox(
        label='Issues (JSON array)',
        lines=6,
        placeholder='[{"file": "auth/login.py", "line": 11, "type": "security", "severity": "high", "description": "SQL injection"}]'
    )
    decision_radio = gr.Radio(
        choices=["approve", "request_changes"],
        value="request_changes",
        label="Final Decision"
    )
    submit_btn = gr.Button("Submit Review")

    score_box = gr.Textbox(label="Score (0.0 - 1.0)", interactive=False)
    feedback_box = gr.Textbox(label="Feedback", lines=4, interactive=False)

    reset_btn.click(fn=reset_env, outputs=[diff_box, task_id])
    submit_btn.click(fn=run_review, inputs=[issues_box, decision_radio], outputs=[score_box, task_id, feedback_box])

    demo.load(fn=reset_env, outputs=[diff_box, task_id])

demo.launch()
