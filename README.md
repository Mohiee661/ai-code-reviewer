---
title: AI Code Reviewer
emoji: 🤖
colorFrom: blue
colorTo: purple
sdk: docker
pinned: false
---

# AI Code Reviewer — OpenEnv Environment v2.0

A production-ready OpenEnv environment where an AI agent reviews pull requests,
identifies bugs and security issues, and decides whether to approve or request changes.

## API Contract

All endpoints return a consistent envelope:

```json
{ "success": true,  "data": { ... }, "error": null }
{ "success": false, "data": null,    "error": "message" }
```

| Method | Path | Description |
|--------|------|-------------|
| POST | /reset | Start episode. Optional body: `{"task_id": "easy"}` |
| POST | /step | Phase 1: submit `issues`. Phase 2: submit `final_decision`. |
| GET  | /state | Current task, phase, pending issues |
| GET  | /metrics | Last episode precision / recall / hallucination rate |
| GET  | /health | Liveness check |
| GET  | /docs | Swagger UI |

## Two-Phase Flow

```
POST /reset                              →  obs { phase: "issues" }
POST /step  { "issues": [...] }          →  reward.score=0.0, done=false
POST /step  { "final_decision": "..." }  →  final reward, done=true
```

## Observation

```json
{
  "files":       [{ "filename": "auth/login.py", "diff": "..." }],
  "instruction": "You are a strict senior security reviewer. Review this pull request...",
  "persona":     "You are a strict senior security reviewer.",
  "phase":       "issues"
}
```

## Action

Phase 1 — issues only:
```json
{
  "issues": [{
    "file": "auth/login.py", "line": 11,
    "type": "security", "severity": "high",
    "description": "SQL injection via f-string interpolation."
  }]
}
```

Phase 2 — decision only:
```json
{ "final_decision": "request_changes" }
```

## Failure Handling

Invalid payloads return HTTP 422 with a structured error:
```json
{ "success": false, "data": null, "error": "issues[0] missing required field 'severity'" }
```

Calling `/step` before `/reset` returns HTTP 400:
```json
{ "success": false, "data": null, "error": "Call reset() before step()." }
```

Unknown `task_id` in `/reset` returns HTTP 400:
```json
{ "success": false, "data": null, "error": "Unknown task_id: 'foo'" }
```

## Reward Design

| Component | Effect |
|-----------|--------|
| Matched issue (high) | +1.0 toward base |
| Matched issue (medium) | +0.5 toward base |
| Matched issue (low) | +0.2 toward base |
| Missed high-severity | −0.5 each |
| All high-severity found | +0.1 bonus |
| False positive (normal) | −0.1 each |
| False positive (high severity) | −0.25 each |
| Correct decision | +0.2 |
| Wrong decision | −0.2 |

Score clamped to [0.0, 1.0]. Feedback includes precision, recall, and missed issue details.

## Deterministic Evaluation

- Tasks cycle in fixed order when no `task_id` is provided.
- `inference.py` uses `temperature=0` for reproducible LLM outputs.
- Grader is pure function — same action + same task = same score, always.
- All constants live in `env/config.py`.

## Reviewer Persona Mode

Each task carries a static persona embedded in the observation instruction:

| Task | Persona |
|------|---------|
| easy | Pragmatic — correctness and maintainability |
| medium | Performance — DB efficiency and scalability |
| hard | Security — strict, flag every vulnerability |
| expert | Security — cross-file reasoning required |

## Tasks

| ID | Files | Focus |
|----|-------|-------|
| easy | 1 | Off-by-one logic bugs |
| medium | 1 | Full-table-scan queries + unguarded export |
| hard | 2 | SQL injection + hardcoded JWT secret |
| expert | 2 | Unvalidated API input exploited by raw SQL in DB layer |

## Production Considerations

- All config constants in `env/config.py` — no magic numbers in logic.
- Structured logging via Python `logging` module (`[INFO]` / `[ERROR]` format).
- Input validation rejects malformed payloads before they reach the environment.
- `/health` endpoint for deployment readiness checks.
- `/metrics` returns last-episode precision, recall, and hallucination rate.
- No database, no async complexity, no external dependencies beyond FastAPI + Pydantic.

## Setup

```bash
pip install -r requirements.txt
export HF_TOKEN=your_token
python inference.py          # run baseline across all tasks
```

```bash
docker build -t pr-env .
docker run -p 7860:7860 pr-env
```
