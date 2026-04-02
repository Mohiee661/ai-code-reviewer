# code-review-env

An OpenEnv environment that evaluates an AI agent's ability to review pull requests.
The agent observes a code diff, identifies issues, and decides whether to approve or request changes.
Performance is scored deterministically using a severity-weighted grader.

---

## Motivation

Code review is one of the most common and high-value tasks in software engineering.
It requires reasoning about correctness, performance, security, and cross-file dependencies —
making it a strong benchmark for general-purpose coding agents.

---

## Architecture

```
Agent (LLM)
    ↓  Action (issues + final_decision)
Environment (CodeReviewEnv)
    ↓  grade(action, expected, decision)
Grader
    ↓  Reward (score 0.0–1.0 + feedback)
```

---

## Observation Space

Each observation contains:

- `files` — list of `FileDiff` objects, each with a `filename` and unified `diff` string
- `instruction` — fixed string: `"Review this pull request."`

---

## Action Space

The agent must return:

- `issues` — list of `Issue` objects:
  - `file` (str) — filename where the issue occurs
  - `line` (int) — line number
  - `type` (str) — one of `syntax`, `logic`, `performance`, `security`, `code_quality`
  - `severity` — `low`, `medium`, or `high`
  - `description` (str) — concise explanation
- `final_decision` — `"approve"` or `"request_changes"`

---

## Reward Design

Scoring is deterministic and severity-weighted.

| Component | Effect |
|---|---|
| Matched issue (high) | +1.0 toward base score |
| Matched issue (medium) | +0.5 toward base score |
| Matched issue (low) | +0.2 toward base score |
| False positive | −0.1 per issue |
| Correct decision | +0.2 bonus |
| Wrong decision | −0.2 penalty |

An issue is considered matched if it shares the same `file` and `type` as an expected issue,
and its `line` is within ±1 of the expected line.

Final score is clamped to `[0.0, 1.0]`.

---

## Tasks

### easy
Single-file diff (`utils/list_helpers.py`).
Contains two off-by-one logic bugs introduced in a list utility.
Expected: 2 `logic/medium` issues, decision `request_changes`.

### medium
Single-file diff (`api/users.py`).
A Flask API where efficient DB queries are replaced with full-table scans filtered in Python,
plus an unguarded data export endpoint.
Expected: 2 `performance/high` + 1 `code_quality/medium` issue, decision `request_changes`.

### hard
Two-file diff (`auth/login.py` + `auth/config.py`).
Introduces a SQL injection vulnerability and a hardcoded JWT secret fallback.
The third issue requires cross-file reasoning: the insecure fallback in `config.py`
silently propagates into token signing in `login.py`.
Expected: 2 `security/high` + 1 `security/medium` issue, decision `request_changes`.

---

## Project Structure

```
code-review-env/
├── env/
│   ├── models.py       # Pydantic schemas
│   ├── tasks.py        # PR task dataset
│   ├── grader.py       # Deterministic scoring
│   └── environment.py  # OpenEnv interface
├── baseline.py         # LLM agent runner
├── requirements.txt
├── openenv.yaml
├── Dockerfile
└── README.md
```

---

## Setup

### Local

```bash
pip install -r requirements.txt
export OPENAI_API_KEY=sk-...
python baseline.py
```

### Docker

```bash
docker build -t code-review-env .
docker run -e OPENAI_API_KEY=sk-... code-review-env
```

---

## Example Output

```
[info] Task: hard

[model output]
{
  "issues": [
    {"file": "auth/login.py", "line": 11, "type": "security", "severity": "high", "description": "SQL injection via f-string interpolation."},
    {"file": "auth/config.py", "line": 7, "type": "security", "severity": "high", "description": "Hardcoded JWT secret fallback."}
  ],
  "final_decision": "request_changes"
}

[result] task_id : hard
[result] score   : 0.87
[result] feedback: Matched 2/3 expected issues. False positives: 0. Decision: correct (request_changes). Final score: 0.87. Missed: auth/login.py:4 [security/medium].
```

---

## Reproducibility

- Grader is fully deterministic: same action + same task always produces the same score.
- `baseline.py` uses `temperature=0` to minimize model-side variance.
- Tasks are fixed datasets — no procedural generation.
