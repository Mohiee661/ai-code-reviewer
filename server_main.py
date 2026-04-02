from fastapi import FastAPI
from fastapi.responses import RedirectResponse, HTMLResponse
from pydantic import BaseModel
from typing import Any
from env.environment import CodeReviewEnv
from env.models import Action

app = FastAPI(
    title="AI Code Reviewer",
    description="OpenEnv environment for PR code review. Use POST /reset to start, POST /step to submit a review.",
    version="1.0.0",
)
env = CodeReviewEnv()


class ActionRequest(BaseModel):
    issues: list[Any] = []
    final_decision: str = "approve"


@app.get("/", response_class=HTMLResponse)
def root():
    return """
    <html><head><title>AI Code Reviewer</title></head>
    <body style="font-family:sans-serif;max-width:600px;margin:40px auto;padding:20px">
    <h1>🤖 AI Code Reviewer</h1>
    <p>OpenEnv environment for pull request review evaluation.</p>
    <h3>Endpoints</h3>
    <ul>
      <li><code>POST /reset</code> — start a new episode</li>
      <li><code>POST /step</code> — submit a review action</li>
      <li><code>GET /state</code> — inspect current task</li>
      <li><a href="/docs">GET /docs</a> — interactive API docs</li>
    </ul>
    <p><a href="/docs"><button style="padding:10px 20px;font-size:16px;cursor:pointer">Open API Docs →</button></a></p>
    </body></html>
    """


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/reset")
def reset():
    obs = env.reset()
    return obs.model_dump()


@app.post("/step")
def step(action_req: ActionRequest):
    action = Action(**action_req.model_dump())
    obs, reward, done, info = env.step(action)
    return {
        "observation": obs.model_dump(),
        "reward": reward.model_dump(),
        "done": done,
        "info": info,
    }


@app.get("/state")
def state():
    return env.state()
