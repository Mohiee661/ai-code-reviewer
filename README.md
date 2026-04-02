---
title: AI Code Reviewer
emoji: 🤖
colorFrom: blue
colorTo: purple
sdk: docker
pinned: false
---

# AI Code Reviewer

An OpenEnv environment that evaluates an AI agent ability to review pull requests.

## API Endpoints

- `POST /reset` — load a new PR task, returns observation
- `POST /step` — submit a review action, returns score and feedback  
- `GET /state` — inspect current task (debug)
- `GET /docs` — Swagger UI

## Tasks

- easy — off-by-one logic bugs, single file
- medium — inefficient DB queries in a Flask API
- hard — SQL injection + hardcoded JWT secret across two files
