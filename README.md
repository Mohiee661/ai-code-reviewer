---
title: AI Code Reviewer
emoji: 🤖
colorFrom: blue
colorTo: purple
sdk: docker
pinned: false
---

# AI Code Reviewer — Production-Grade OpenEnv Environment

A realistic, multi-dimensional code review environment where AI agents evaluate pull requests like senior engineers — identifying bugs, security vulnerabilities, and design issues across multiple files.

## Why Code Review?

Code review is one of the most critical quality gates in software engineering:
- **High-value task**: Catches 60-90% of bugs before production (Microsoft Research)
- **Complex reasoning**: Requires understanding code semantics, security implications, and cross-file dependencies
- **Real-world impact**: Poor reviews lead to production incidents, security breaches, and technical debt

Existing benchmarks focus on isolated code generation. This environment evaluates an agent's ability to **reason about existing code**, **identify subtle bugs**, and **make judgment calls** — skills that define senior engineering competence.

## What Makes This Environment Unique

### 1. Multi-Dimensional Grading (Industry-First)

Unlike binary pass/fail scoring, we evaluate 5 dimensions weighted by real-world importance:

| Dimension | Weight | What It Measures |
|-----------|--------|------------------|
| **Issue Coverage** | 40% | Finding all true bugs (recall) |
| **Severity Awareness** | 20% | Prioritizing critical issues (security > performance > style) |
| **Precision** | 20% | Avoiding false positives and noise |
| **Explanation Quality** | 5% | Clear, actionable descriptions |
| **Decision Correctness** | 15% | Approve vs request changes |

This mirrors how engineering teams actually evaluate reviewers.

### 2. Realistic Pull Request Simulation

Each task includes:
- **PR metadata**: Title, description, author intent
- **Multi-file diffs**: Cross-file vulnerabilities require reasoning about data flow
- **Misleading context**: Author intent may hide bugs (e.g., "improve readability" while introducing SQL injection)
- **Real commit patterns**: Authentic diff format with line numbers and context

### 3. Progressive Difficulty with Adversarial Design

| Level | Characteristics | Example |
|-------|----------------|---------|
| **Easy** | Single file, obvious bugs | Off-by-one errors in list slicing |
| **Medium** | Multiple issues, mixed severity | N+1 queries + missing pagination |
| **Hard** | Cross-file vulnerabilities | SQL injection + hardcoded secrets |
| **Expert** | Subtle data flow exploits | Unvalidated input → raw SQL in different file |

Tasks are designed to trick weak models: security issues disguised as "refactoring", performance regressions labeled as "optimization".

### 4. Explainable Grading

Every reward includes a breakdown showing exactly where the agent succeeded or failed:

```
Score: 0.73 [Coverage: 0.85 Severity: 0.90 Precision: 0.67 Explanation: 0.75 Decision: 1.00]
Matched 3/4 issues. Missed high-severity: 1. False positives: 2 (1 high).
```

This enables:
- **Debugging agent behavior**: Understand why a score is low
- **Targeted improvements**: Focus on weak dimensions
- **Fair evaluation**: Transparent, reproducible scoring

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  Agent (LLM)                                                │
│  ├─ Stage 1: Analyze PR context + diffs → detect issues    │
│  ├─ Stage 2: Refine issues (filter noise, validate)        │
│  └─ Stage 3: Make decision (approve / request_changes)     │
└────────────────────┬────────────────────────────────────────┘
                     │ Action { issues[], final_decision }
                     ▼
┌─────────────────────────────────────────────────────────────┐
│  Environment (CodeReviewEnv)                                │
│  ├─ Phase 1: Receive issues → partial reward               │
│  └─ Phase 2: Receive decision → final reward               │
└────────────────────┬────────────────────────────────────────┘
                     │ grade(action, expected, decision)
                     ▼
┌─────────────────────────────────────────────────────────────┐
│  Multi-Dimensional Grader                                   │
│  ├─ Issue Coverage (40%): recall + high-severity penalty   │
│  ├─ Severity Awareness (20%): prioritization accuracy      │
│  ├─ Precision (20%): false positive rate                   │
│  ├─ Explanation Quality (5%): description clarity          │
│  └─ Decision Correctness (15%): approve vs request changes │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
              Reward { score, feedback, breakdown }
```

## Example Episode Walkthrough

**Task**: `hard` — SQL injection + hardcoded JWT secret

**PR Context**:
```
Title: "refactor: simplify auth module and centralize config"
Description: "Moved database connection logic to config. Simplified JWT generation."
Author Intent: "Reduce code duplication by centralizing configuration."
```

**Agent Analysis** (Stage 1):
```json
{
  "issues": [
    {
      "file": "auth/login.py",
      "line": 11,
      "type": "security",
      "severity": "high",
      "description": "SQL injection: username/password interpolated via f-string. Use parameterized queries."
    },
    {
      "file": "auth/config.py",
      "line": 7,
      "type": "security",
      "severity": "high",
      "description": "Hardcoded JWT secret 'supersecret123' as fallback. Remove fallback entirely."
    }
  ]
}
```

**Agent Decision** (Stage 2):
```json
{ "final_decision": "request_changes" }
```

**Grading Result**:
```
Score: 0.82
[Coverage: 0.67  Severity: 1.00  Precision: 1.00  Explanation: 0.85  Decision: 1.00]
Matched 2/3 issues. Missed high-severity: 0. False positives: 0.
Decision: correct (request_changes).
Missed: auth/login.py:4 [security/medium] — SECRET_KEY imported at module load time.
```

**Analysis**: Agent caught both critical issues but missed the subtle third issue about module-level imports. Strong severity awareness (1.00) and precision (1.00), but coverage penalized for missing one issue.

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/reset` | Start episode. Optional: `{"task_id": "easy"}` |
| POST | `/step` | Phase 1: submit issues. Phase 2: submit decision. |
| GET  | `/state` | Current task, phase, expected issues |
| GET  | `/metrics` | Last episode precision/recall/hallucination rate |
| GET  | `/health` | Liveness check |
| GET  | `/docs` | Interactive Swagger UI |

All endpoints return structured JSON:
```json
{ "success": true, "data": {...}, "error": null }
```

## Observation Space

```json
{
  "files": [
    {
      "filename": "auth/login.py",
      "diff": "--- a/auth/login.py\n+++ b/auth/login.py\n...",
      "language": "python",
      "lines_added": 11,
      "lines_removed": 13
    }
  ],
  "instruction": "You are a strict senior security reviewer. Review this PR...",
  "persona": "You are a strict senior security reviewer.",
  "phase": "issues",
  "pr_metadata": {
    "title": "refactor: simplify auth module",
    "description": "Moved database connection logic...",
    "author_intent": "Reduce code duplication..."
  }
}
```

## Action Space

**Phase 1** — Submit issues:
```json
{
  "issues": [
    {
      "file": "auth/login.py",
      "line": 11,
      "type": "security",
      "severity": "high",
      "description": "SQL injection vulnerability..."
    }
  ]
}
```

**Phase 2** — Submit decision:
```json
{ "final_decision": "request_changes" }
```

## Reward Structure

**Multi-dimensional scoring** (all components 0.0–1.0):

```python
score = (
    0.40 * issue_coverage +      # Found 3/4 issues = 0.75
    0.20 * severity_awareness +  # Caught all high-severity = 1.00
    0.20 * precision +           # 0 false positives = 1.00
    0.05 * explanation_quality + # Clear descriptions = 0.85
    0.15 * decision_correctness  # Correct decision = 1.00
)
# = 0.40*0.75 + 0.20*1.00 + 0.20*1.00 + 0.05*0.85 + 0.15*1.00
# = 0.30 + 0.20 + 0.20 + 0.0425 + 0.15 = 0.8925
```

Final score clamped to (0.01, 0.99) for validator compliance.

## Deterministic Evaluation

- **Grader**: Pure function — same action + same task = same score always
- **Tasks**: Fixed dataset, no procedural generation
- **Baseline**: `temperature=0` for reproducible LLM outputs
- **Config**: All constants in `env/config.py`

## Setup

```bash
pip install -r requirements.txt
export HF_TOKEN=your_openai_or_hf_token
python inference.py
```

```bash
docker build -t pr-env .
docker run -p 7860:7860 pr-env
```

## Baseline Results

| Task | Difficulty | Expected Score Range |
|------|-----------|---------------------|
| easy | Obvious bugs | 0.70 – 0.85 |
| medium | Multiple issues | 0.60 – 0.75 |
| hard | Cross-file security | 0.55 – 0.70 |
| expert | Subtle data flow | 0.50 – 0.65 |

Strong models (GPT-4, Claude 3.5) achieve 0.70+ average. Weak models struggle with cross-file reasoning and severity prioritization.

## Why This Environment Wins

1. **Real-world relevance**: Code review is a $10B+ problem (GitHub, GitLab, Gerrit)
2. **Novel evaluation**: First multi-dimensional grading system for code review
3. **Adversarial design**: Tasks actively try to trick weak models
4. **Production-ready**: Structured logging, input validation, explainable rewards
5. **Extensible**: Easy to add new tasks, personas, or grading dimensions

## Project Structure

```
├── inference.py          # Multi-stage baseline agent
├── server/app.py         # FastAPI server (reset/step/state/metrics)
├── env/
│   ├── models.py         # Pydantic schemas (Observation, Action, Reward)
│   ├── tasks.py          # 4 PR review tasks with metadata
│   ├── grader.py         # Multi-dimensional scoring engine
│   ├── environment.py    # Two-phase episode management
│   └── config.py         # All grading constants
├── Dockerfile            # Production deployment
├── requirements.txt      # Minimal dependencies
└── openenv.yaml          # Environment metadata
```

## Citation

If you use this environment in research, please cite:

```bibtex
@software{ai_code_reviewer_2024,
  title={AI Code Reviewer: A Multi-Dimensional OpenEnv Environment for Pull Request Evaluation},
  author={Mohith},
  year={2026},
  url={https://huggingface.co/spaces/Mohiee661/ai-code-reviewer}
}
```

## License

MIT — Free for research and commercial use.
