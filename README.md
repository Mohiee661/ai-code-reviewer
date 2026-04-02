---
title: AI Code Reviewer
emoji: 🤖
colorFrom: blue
colorTo: purple
sdk: gradio
python_version: "3.10"
app_file: app.py
pinned: false
---

# AI Code Reviewer

An OpenEnv environment that evaluates an AI agent's ability to review pull requests.
The agent observes a code diff, identifies issues, and decides whether to approve or request changes.
Performance is scored deterministically using a severity-weighted grader.

## Tasks

- **easy** — off-by-one logic bugs, single file
- **medium** — inefficient DB queries in a Flask API
- **hard** — SQL injection + hardcoded JWT secret across two files

## Setup

```bash
pip install -r requirements.txt
export OPENAI_API_KEY=sk-...
python baseline.py
```
