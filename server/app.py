"""FastAPI server — AI Code Reviewer (OpenEnv)."""
import sys, os, logging
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(
    level=logging.INFO,
    format="[%(levelname)s] %(message)s",
)
log = logging.getLogger(__name__)

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, field_validator
from typing import Any, List, Optional

from env.environment import CodeReviewEnv
from env.models import Action, Issue

app = FastAPI(title="AI Code Reviewer", description="OpenEnv PR review environment", version="2.0.0")
env = CodeReviewEnv()

VALID_SEVERITIES  = {"low", "medium", "high"}
VALID_DECISIONS   = {"approve", "request_changes"}
VALID_TYPES       = {"syntax", "logic", "performance", "security", "code_quality"}


# ── response helpers ──────────────────────────────────────────────────────────

def ok(data):
    return {"success": True, "data": data, "error": None}

def err(message: str, status: int = 400):
    from fastapi import HTTPException
    raise HTTPException(status_code=status, detail={"success": False, "data": None, "error": message})


# ── request models ────────────────────────────────────────────────────────────

class ResetRequest(BaseModel):
    task_id: Optional[str] = None


class ActionRequest(BaseModel):
    issues: List[Any] = []
    final_decision: Optional[str] = None

    @field_validator("final_decision")
    @classmethod
    def validate_decision(cls, v):
        if v is not None and v not in VALID_DECISIONS:
            raise ValueError(f"final_decision must be one of {sorted(VALID_DECISIONS)}")
        return v


# ── validation ────────────────────────────────────────────────────────────────

def parse_issues(raw: List[Any]) -> List[Issue]:
    if not isinstance(raw, list):
        err("'issues' must be a list")
    issues = []
    for i, item in enumerate(raw):
        if not isinstance(item, dict):
            err(f"issues[{i}] must be an object")
        for field in ("file", "line", "type", "severity", "description"):
            if field not in item:
                err(f"issues[{i}] missing required field '{field}'")
        if item["severity"] not in VALID_SEVERITIES:
            err(f"issues[{i}].severity must be one of {sorted(VALID_SEVERITIES)}")
        if item["type"] not in VALID_TYPES:
            err(f"issues[{i}].type must be one of {sorted(VALID_TYPES)}")
        if not isinstance(item["line"], int):
            err(f"issues[{i}].line must be an integer")
        issues.append(Issue(**item))
    return issues


# ── endpoints ─────────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
def root():
    return """
    <html><head><title>AI Code Reviewer</title></head>
    <body style="font-family:sans-serif;max-width:640px;margin:40px auto;padding:20px">
    <h1>🤖 AI Code Reviewer <small style="font-size:0.5em;color:#888">v2.0</small></h1>
    <p>OpenEnv environment — multi-step, persona-aware, severity-weighted.</p>
    <table border="1" cellpadding="6" cellspacing="0" style="border-collapse:collapse;width:100%">
      <tr><th>Method</th><th>Path</th><th>Description</th></tr>
      <tr><td>POST</td><td>/reset</td><td>Start episode. Optional: <code>{"task_id":"easy"}</code></td></tr>
      <tr><td>POST</td><td>/step</td><td>Phase 1: issues · Phase 2: final_decision</td></tr>
      <tr><td>GET</td><td>/state</td><td>Current task &amp; phase</td></tr>
      <tr><td>GET</td><td>/metrics</td><td>Last episode precision/recall</td></tr>
      <tr><td>GET</td><td>/health</td><td>Liveness check</td></tr>
      <tr><td>GET</td><td>/docs</td><td>Swagger UI</td></tr>
    </table>
    <br><a href="/docs"><button style="padding:10px 20px;font-size:16px;cursor:pointer">Open API Docs →</button></a>
    </body></html>
    """


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/reset")
def reset(body: ResetRequest = ResetRequest()):
    try:
        obs = env.reset(task_id=body.task_id)
        log.info("Reset called for task %s", env.current_task.id)
        return ok(obs.model_dump())
    except ValueError as e:
        log.error("Reset error: %s", e)
        err(str(e))
    except Exception as e:
        log.error("Reset unexpected error: %s", e)
        err("Internal server error", 500)


@app.post("/step")
def step(action_req: ActionRequest):
    try:
        issues = parse_issues(action_req.issues)
        action = Action(issues=issues, final_decision=action_req.final_decision)
    except Exception as e:
        log.error("Invalid action input: %s", e)
        err(str(e), 422)

    try:
        obs, reward, done, info = env.step(action)
        return ok({
            "observation": obs.model_dump(),
            "reward":      reward.model_dump(),
            "done":        done,
            "info":        info,
        })
    except RuntimeError as e:
        log.error("Step error: %s", e)
        err(str(e))
    except Exception as e:
        log.error("Step unexpected error: %s", e)
        err("Internal server error", 500)


@app.get("/state")
def state():
    try:
        return ok(env.state())
    except Exception as e:
        log.error("State error: %s", e)
        err("Internal server error", 500)


@app.get("/metrics")
def metrics():
    return ok(env.metrics())


def main():
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=7860)


if __name__ == "__main__":
    main()
