---
title: AI Code Reviewer
emoji: 🤖
colorFrom: blue
colorTo: purple
sdk: docker
pinned: false
---

# AI Code Reviewer — OpenEnv Environment

A real-world OpenEnv environment where an AI agent reviews pull requests,
identifies bugs and security issues, and decides whether to approve or request changes.

## Motivation

Code review is one of the most common high-value tasks in software engineering.
It requires reasoning about correctness, performance, security, and cross-file
dependencies — making it a strong benchmark for general-purpose coding agents.
This environment provides a structured, reproducible way to evaluate and train
agents on realistic PR review scenarios.

## Architecture

```
Agent (LLM)
    ↓  Action { issues[], final_decision }
Environment (CodeReviewEnv)
    ↓  grade(action, expected, decision)
Grader (severity-weighted, deterministic)
    ↓  Reward { score: 0.0–1.0, feedback: str }
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | /reset | Start new episode, returns Observation |
| POST | /step | Submit Action, returns (obs, reward, done, info) |
| GET | /state | Inspect current task (debug) |
| GET | /docs | Swagger UI |

## Observation Space

```json
{
  "files": [
    { "filename": "auth/login.py", "diff": "--- a/auth/login.py\n+++ ..." }
  ],
  "instruction": "Review this pull request."
}
```

Each observation contains one or more unified diffs and a fixed instruction string.

## Action Space

```json
{
  "issues": [
    {
      "file": "auth/login.py",
      "line": 11,
      "type": "security",
      "severity": "high",
      "description": "SQL injection via f-string interpolation."
    }
  ],
  "final_decision": "approve | request_changes"
}
```

Issue types: `syntax`, `logic`, `performance`, `security`, `code_quality`
Severity levels: `low`, `medium`, `high`

## Reward Design

| Component | Effect |
|-----------|--------|
| Matched issue (high severity) | +1.0 toward base score |
| Matched issue (medium severity) | +0.5 toward base score |
| Matched issue (low severity) | +0.2 toward base score |
| False positive | −0.1 per issue |
| Correct final decision | +0.2 bonus |
| Wrong final decision | −0.2 penalty |

An issue matches if `file` and `type` agree and `line` is within ±1.
Final score is clamped to [0.0, 1.0]. Provides partial credit throughout.

## Tasks

### easy
Single-file diff (`utils/list_helpers.py`).
Two off-by-one logic bugs in a list utility function.
Expected: 2 `logic/medium` issues. Decision: `request_changes`.
Baseline score: ~0.70

### medium
Single-file diff (`api/users.py`).
Full-table-scan anti-patterns replacing efficient ORM queries, plus an
unguarded data export endpoint.
Expected: 2 `performance/high` + 1 `code_quality/medium`. Decision: `request_changes`.
Baseline score: ~0.65

### hard
Two-file diff (`auth/login.py` + `auth/config.py`).
SQL injection vulnerability + hardcoded JWT secret fallback. The third issue
requires cross-file reasoning: the insecure fallback in `config.py` silently
propagates into token signing in `login.py`.
Expected: 2 `security/high` + 1 `security/medium`. Decision: `request_changes`.
Baseline score: ~0.60

## Setup

### Local

```bash
pip install -r requirements.txt
export HF_TOKEN=your_openai_or_hf_token
export MODEL_NAME=gpt-4o          # optional, default: gpt-4o
export API_BASE_URL=https://api.openai.com/v1  # optional
python inference.py
```

### Docker

```bash
docker build -t pr-env .
# Run the API server
docker run -p 8000:8000 pr-env
# Run the baseline inference script
docker run -e HF_TOKEN=sk-... pr-env python inference.py
```

## Project Structure

```
├── inference.py        # Baseline script (OpenEnv entry point)
├── server.py           # FastAPI HTTP server (reset/step/state)
├── app.py              # HF Space entry point
├── Dockerfile
├── requirements.txt
├── openenv.yaml
├── env/
│   ├── models.py       # Pydantic schemas
│   ├── tasks.py        # PR task dataset (easy/medium/hard)
│   ├── grader.py       # Deterministic severity-weighted grader
│   └── environment.py  # OpenEnv interface
└── README.md
```

## Reproducibility

- Grader is fully deterministic: same action + same task = same score always.
- `inference.py` uses `temperature=0` to minimize model variance.
- Tasks are fixed datasets with no procedural generation.
