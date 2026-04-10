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
    <!doctype html>
    <html lang="en">
    <head>
      <meta charset="utf-8" />
      <meta name="viewport" content="width=device-width, initial-scale=1" />
      <title>AI Code Reviewer</title>
      <style>
        :root { --ink:#121212; --muted:#5b616e; --line:#d6d9df; --panel:#f7f8fa; --accent:#0b6bcb; --good:#13795b; --warn:#9a3412; }
        * { box-sizing: border-box; }
        body { margin:0; color:var(--ink); font-family:Arial, Helvetica, sans-serif; background:#fff; }
        main { max-width:1120px; margin:0 auto; padding:28px 18px 48px; }
        header { border-bottom:1px solid var(--line); padding-bottom:18px; margin-bottom:20px; }
        h1 { font-size:32px; line-height:1.1; margin:0 0 8px; }
        h2 { font-size:18px; margin:0 0 10px; }
        p { line-height:1.55; margin:0 0 12px; }
        .sub { color:var(--muted); max-width:780px; }
        .grid { display:grid; grid-template-columns:minmax(0,1fr) 380px; gap:18px; align-items:start; }
        .band { background:var(--panel); border:1px solid var(--line); border-radius:8px; padding:16px; margin-bottom:16px; }
        .controls { display:flex; gap:10px; flex-wrap:wrap; align-items:center; }
        select, button, textarea { font:inherit; border-radius:8px; }
        select, textarea { border:1px solid var(--line); background:#fff; }
        select { padding:9px 10px; min-width:160px; }
        button { border:1px solid #0b5cad; background:var(--accent); color:#fff; padding:9px 12px; cursor:pointer; min-height:40px; }
        button.secondary { color:var(--accent); background:#fff; }
        textarea { width:100%; min-height:220px; padding:12px; resize:vertical; font-family:Consolas, "Courier New", monospace; font-size:13px; line-height:1.45; }
        pre { white-space:pre-wrap; overflow-wrap:anywhere; margin:0; padding:12px; background:#101820; color:#edf2f7; border-radius:8px; font-family:Consolas, "Courier New", monospace; font-size:13px; line-height:1.45; }
        .meta { display:grid; grid-template-columns:repeat(3, minmax(0, 1fr)); gap:10px; }
        .pill { border:1px solid var(--line); border-radius:8px; padding:10px; background:#fff; min-height:68px; }
        .pill b { display:block; margin-bottom:6px; }
        .score { font-size:34px; font-weight:700; color:var(--good); }
        .small { font-size:13px; color:var(--muted); }
        .links a { color:var(--accent); margin-right:12px; }
        .status { color:var(--warn); min-height:20px; }
        @media (max-width:860px) { .grid, .meta { grid-template-columns:1fr; } h1 { font-size:26px; } }
      </style>
    </head>
    <body>
      <main>
        <header>
          <h1>AI Code Reviewer OpenEnv</h1>
          <p class="sub">Evaluate agents on realistic pull request review: issue recall, severity awareness, precision, explanation quality, and approve/request-changes judgment.</p>
          <p class="links"><a href="/docs">API docs</a><a href="/health">Health</a><a href="/metrics">Last metrics</a></p>
        </header>

        <section class="band">
          <div class="controls">
            <label for="task"><b>Task</b></label>
            <select id="task">
              <option value="easy">easy</option>
              <option value="medium">medium</option>
              <option value="hard">hard</option>
              <option value="expert">expert</option>
            </select>
            <button onclick="resetTask()">Load PR</button>
            <button class="secondary" onclick="loadSample()">Use strong sample answer</button>
          </div>
          <p id="status" class="status"></p>
        </section>

        <section class="meta" id="metadata"></section>

        <section class="grid">
          <div>
            <section class="band">
              <h2>Pull Request</h2>
              <pre id="diff">Choose a task and load the PR.</pre>
            </section>
          </div>
          <aside>
            <section class="band">
              <h2>Submit Issues</h2>
              <textarea id="issues">{"issues":[]}</textarea>
              <div class="controls"><button onclick="submitIssues()">Submit issues</button></div>
            </section>
            <section class="band">
              <h2>Final Decision</h2>
              <div class="controls">
                <select id="decision">
                  <option value="request_changes">request_changes</option>
                  <option value="approve">approve</option>
                </select>
                <button onclick="submitDecision()">Score review</button>
              </div>
            </section>
            <section class="band">
              <h2>Reward</h2>
              <div class="score" id="score">--</div>
              <p id="feedback" class="small">Submit issues and a final decision to see the reward breakdown.</p>
            </section>
          </aside>
        </section>
      </main>

      <script>
        const samples = {
          easy: {issues: [
            {file:"utils/list_helpers.py", line:4, type:"logic", severity:"medium", description:"Off-by-one slice starts at len(items)-n-1, returning one extra item before the requested last n elements. Use len(items)-n."},
            {file:"utils/list_helpers.py", line:9, type:"logic", severity:"medium", description:"Loop extends to len(items)+1, creating an extra empty chunk at the end. Use range(0, len(items), size)."}
          ]},
          medium: {issues: [
            {file:"api/users.py", line:9, type:"performance", severity:"high", description:"Loads all users and filters active users in Python, causing unnecessary full table scans. Filter in the database with User.query.filter_by(active=True)."},
            {file:"api/users.py", line:15, type:"performance", severity:"high", description:"Loads the whole users table to find one primary-key record. Use get_or_404(user_id) or a filtered indexed query."},
            {file:"api/users.py", line:21, type:"code_quality", severity:"medium", description:"Export endpoint returns an unbounded user list with no pagination or access control, creating data exposure and DoS risk."}
          ]},
          hard: {issues: [
            {file:"auth/login.py", line:11, type:"security", severity:"high", description:"SQL injection: username and password are interpolated directly into a SQL f-string. Use parameterized queries."},
            {file:"auth/config.py", line:7, type:"security", severity:"high", description:"Hardcoded JWT secret fallback allows token forgery when JWT_SECRET is unset. Require the env var instead of defaulting to a known secret."},
            {file:"auth/login.py", line:4, type:"security", severity:"medium", description:"SECRET_KEY is imported at module load time, silently propagating the insecure fallback from config.py into token signing."}
          ]},
          expert: {issues: [
            {file:"db/queries.py", line:9, type:"security", severity:"high", description:"SQL injection: user_id is interpolated directly into the orders query. Use a parameterized query."},
            {file:"db/queries.py", line:15, type:"security", severity:"high", description:"SQL injection: product name is inserted directly into a quoted SQL string. Parameterize the name value."},
            {file:"api/routes.py", line:7, type:"security", severity:"medium", description:"Removed int validation for user_id, allowing raw query input to reach the vulnerable SQL layer."}
          ]}
        };
        async function postJson(path, body) {
          const res = await fetch(path, {method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify(body)});
          const data = await res.json();
          if (!res.ok || data.success === false) throw new Error(JSON.stringify(data.detail || data.error || data));
          return data.data || data;
        }
        function setStatus(text) { document.getElementById("status").textContent = text; }
        function loadSample() {
          const task = document.getElementById("task").value;
          document.getElementById("issues").value = JSON.stringify(samples[task], null, 2);
          document.getElementById("decision").value = "request_changes";
        }
        async function resetTask() {
          try {
            setStatus("Loading task...");
            const task = document.getElementById("task").value;
            const obs = await postJson("/reset", {task_id: task});
            const meta = obs.pr_metadata || {};
            document.getElementById("metadata").innerHTML =
              `<div class="pill"><b>Title</b>${meta.title || task}</div>` +
              `<div class="pill"><b>Author intent</b>${meta.author_intent || "Review the diff."}</div>` +
              `<div class="pill"><b>Reviewer</b>${obs.persona || "Senior reviewer"}</div>`;
            document.getElementById("diff").textContent = obs.files.map(f => `### ${f.filename}\n${f.diff}`).join("\n\n");
            document.getElementById("score").textContent = "--";
            document.getElementById("feedback").textContent = "Submit issues and a final decision to see the reward breakdown.";
            loadSample();
            setStatus("Task loaded. Edit the JSON or submit the sample answer.");
          } catch (err) { setStatus(err.message); }
        }
        async function submitIssues() {
          try {
            setStatus("Submitting issues...");
            const payload = JSON.parse(document.getElementById("issues").value);
            const result = await postJson("/step", payload);
            document.getElementById("feedback").textContent = result.reward.feedback;
            setStatus("Issues accepted. Submit the final decision next.");
          } catch (err) { setStatus(err.message); }
        }
        async function submitDecision() {
          try {
            setStatus("Scoring...");
            const final_decision = document.getElementById("decision").value;
            const result = await postJson("/step", {final_decision});
            document.getElementById("score").textContent = result.reward.score.toFixed(2);
            document.getElementById("feedback").textContent = result.reward.feedback;
            setStatus("Review scored.");
          } catch (err) { setStatus(err.message); }
        }
        resetTask();
      </script>
    </body>
    </html>
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
