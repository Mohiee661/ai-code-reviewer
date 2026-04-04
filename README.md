---
title: AI Code Reviewer
emoji: 🤖
colorFrom: blue
colorTo: purple
sdk: docker
pinned: false
---

# AI Code Reviewer — OpenEnv Environment v2.0

A real-world OpenEnv environment where an AI agent reviews pull requests,
identifies bugs and security issues, and decides whether to approve or request changes.

## What's New in v2.0

- **Reviewer Persona Mode** — each task assigns a static persona (security, performance, pragmatic) embedded in the observation instruction, nudging the agent toward the right focus.
- **Multi-step evaluation** — episodes run in two phases: phase 1 submits issues, phase 2 submits the final decision. Enables richer agent reasoning and cleaner separation of concerns.
- **Severity-aware grading** — missing a high-severity issue now carries a −0.5 penalty; catching all high-severity issues earns a +0.1 bonus; high-severity false positives are penalised at −0.25 vs −0.1 for normal ones.
- **Precision & recall metrics** — feedback now includes per-episode precision and recall.
- **Expert task** — a new cross-file task where missing input validation in the API layer is exploited by a raw SQL query in the DB layer.

## Architecture

```
Agent (LLM)
    ↓  Phase 1: Action { issues[] }
    ↓  Phase 2: Action { final_decision }
Environment (CodeReviewEnv)
    ↓  grade(issues + decision, expected, correct_decision)
Grader (severity-weighted, deterministic)
    ↓  Reward { score: 0.0–1.0, feedback: str }
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | /reset | Start episode. Optional body: `{"task_id": "easy"}` |
| POST | /step | Phase 1: submit `issues`. Phase 2: submit `final_decision`. |
| GET  | /state | Inspect task, phase, pending issues |
| GET  | /docs | Swagger UI |

## Two-Phase Flow

```
POST /reset  →  obs (phase="issues")
POST /step   { "issues": [...] }  →  reward.score=0.0, done=false, phase="decision"
POST /step   { "final_decision": "request_changes" }  →  final reward, done=true
```

## Observation

```json
{
  "files": [{ "filename": "auth/login.py", "diff": "..." }],
  "instruction": "You are a strict senior security reviewer. Review this pull request...",
  "persona": "You are a strict senior security reviewer.",
  "phase": "issues"
}
```

## Action

Phase 1 (issues only):
```json
{ "issues": [{ "file": "auth/login.py", "line": 11, "type": "security", "severity": "high", "description": "..." }] }
```

Phase 2 (decision only):
```json
{ "final_decision": "request_changes" }
```

## Reward Design

| Component | Effect |
|-----------|--------|
| Matched issue (high) | +1.0 toward base |
| Matched issue (medium) | +0.5 toward base |
| Matched issue (low) | +0.2 toward base |
| Missed high-severity issue | −0.5 each |
| All high-severity found | +0.1 bonus |
| False positive (normal) | −0.1 each |
| False positive (high severity) | −0.25 each |
| Correct final decision | +0.2 |
| Wrong final decision | −0.2 |

Score clamped to [0.0, 1.0]. Feedback includes precision, recall, and missed issue details.

## Tasks

| ID | Persona | Focus | Files |
|----|---------|-------|-------|
| easy | Pragmatic | Off-by-one logic bugs | 1 |
| medium | Performance | Full-table-scan queries + unguarded export | 1 |
| hard | Security | SQL injection + hardcoded JWT secret | 2 |
| expert | Security | Unvalidated API input exploited by raw SQL in DB layer | 2 |

## Setup

```bash
pip install -r requirements.txt
export HF_TOKEN=your_token
python inference.py
```

```bash
docker build -t pr-env .
docker run -p 7860:7860 pr-env
```
