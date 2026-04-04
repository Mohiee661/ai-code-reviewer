"""FastAPI server for the Code Review Environment."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import Any, List, Optional

from env.environment import CodeReviewEnv
from env.models import Action, Issue

app = FastAPI(title="AI Code Reviewer", description="OpenEnv PR review environment", version="2.0.0")
env = CodeReviewEnv()


class ActionRequest(BaseModel):
    issues: List[Any] = []
    final_decision: Optional[str] = None


@app.get("/", response_class=HTMLResponse)
def root():
    return """
    <html><head><title>AI Code Reviewer</title></head>
    <body style="font-family:sans-serif;max-width:640px;margin:40px auto;padding:20px">
    <h1>🤖 AI Code Reviewer <small style="font-size:0.5em;color:#888">v2.0</small></h1>
    <p>OpenEnv environment for pull request review — multi-step, persona-aware, severity-weighted.</p>
    <h3>Endpoints</h3>
    <ul>
      <li><code>POST /reset</code> — start episode (optional body: <code>{"task_id": "easy"}</code>)</li>
      <li><code>POST /step</code> — phase 1: submit issues / phase 2: submit final_decision</li>
      <li><code>GET  /state</code> — inspect current task &amp; phase</li>
      <li><a href="/docs">GET /docs</a> — Swagger UI</li>
    </ul>
    <p><a href="/docs"><button style="padding:10px 20px;font-size:16px;cursor:pointer">Open API Docs →</button></a></p>
    </body></html>
    """


@app.get("/health")
def health():
    return {"status": "ok"}


class ResetRequest(BaseModel):
    task_id: Optional[str] = None


@app.post("/reset")
def reset(body: ResetRequest = ResetRequest()):
    obs = env.reset(task_id=body.task_id)
    return obs.model_dump()


@app.post("/step")
def step(action_req: ActionRequest):
    try:
        issues = [Issue(**i) if isinstance(i, dict) else i for i in action_req.issues]
        action = Action(issues=issues, final_decision=action_req.final_decision)
    except Exception as e:
        raise HTTPException(status_code=422, detail=str(e))

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


def main():
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=7860)


if __name__ == "__main__":
    main()
