# Implementation Guide — PR Review OpenEnv Environment

## 🧠 Project Overview

This project implements a **real-world AI training/evaluation environment** where an agent performs **Git pull request (PR) reviews**.

The environment follows the **OpenEnv specification**, enabling agents to:

* Observe a PR (diff across files)
* Take structured actions (identify issues + decision)
* Receive rewards based on correctness

---

## 🎯 Objective

Simulate a realistic developer workflow:

> Given a pull request, the agent must review code changes, identify issues, classify severity, and decide whether to approve or request changes.

---

## 🏗️ System Architecture

Agent (LLM)
↓
Environment (OpenEnv interface)
↓
Task (PR diff + expected issues)
↓
Grader (deterministic scoring)
↓
Reward (0.0 → 1.0)

---

## 📂 Project Structure

code-review-env/
│
├── env/
│   ├── models.py        # Typed schemas (Pydantic)
│   ├── tasks.py         # Dataset of PR tasks
│   ├── grader.py        # Evaluation logic
│   ├── environment.py   # OpenEnv implementation
│
├── baseline.py          # Runs agent
├── openenv.yaml         # Metadata
├── Dockerfile           # Container setup
├── requirements.txt
├── README.md

---

## 🧩 Core Components

### 1. Models (models.py)

Define strict schemas using Pydantic.

#### Issue

Represents a detected problem in code.

Fields:

* file (str)
* line (int)
* type (str) → e.g., "syntax", "security", "code_quality"
* severity (str) → "low", "medium", "high"
* description (str)

---

#### Observation

What the agent receives.

Fields:

* files: List of {filename, diff}
* instruction: string

---

#### Action

What the agent returns.

Fields:

* issues: List[Issue]
* final_decision: "approve" | "request_changes"

---

#### Reward

Returned by environment.

Fields:

* score: float (0.0 → 1.0)
* feedback: string

---

## 🧪 Tasks (tasks.py)

Each task simulates a pull request.

Structure:

* id
* files (multi-file diffs)
* expected issues
* correct decision

---

### Task Design Requirements

You must include at least 3 tasks:

1. Easy

   * Simple syntax or logic bug
   * Single file

2. Medium

   * Code quality / inefficiency
   * Requires reasoning

3. Hard

   * Security issues
   * Multi-file reasoning

---

### Example Task

{
"id": "hard",
"files": [
{"filename": "auth.py", "diff": "..."},
{"filename": "db.py", "diff": "..."}
],
"expected": [
{"file": "auth.py", "line": 2, "type": "security", "severity": "high"}
],
"decision": "request_changes"
}

---

## 🧑‍⚖️ Grader (grader.py)

The grader evaluates agent performance.

### Requirements:

* Deterministic (same input → same score)
* Score between 0.0 and 1.0
* Supports partial credit

---

### Matching Logic

A predicted issue matches expected if:

* Same type
* Same file
* Line difference ≤ 1

---

### Scoring Components

1. Correct Detection

   * Weighted by severity

2. False Positives

   * Penalized

3. Decision Accuracy

   * Bonus or penalty

---

### Severity Weights

low → 0.2
medium → 0.5
high → 1.0

---

### Final Score Formula

score = (correct_weight / total_weight)
penalty = false_positives * 0.1
decision_bonus = +0.2 or -0.2

final_score = clamp(score - penalty + decision_bonus, 0, 1)

---

## 🔁 Environment (environment.py)

Implements OpenEnv interface.

---

### reset()

* Select random task
* Initialize state
* Return Observation

---

### step(action)

Input:

* Agent Action

Process:

* Compare with expected using grader

Output:

* observation (state)
* reward
* done (True after one step)
* info (optional metadata)

---

### state()

Returns:

* Current task
* Expected issues (for debugging)

---

## 🔄 Episode Design

Each episode:

1. reset()
2. agent acts once
3. step()
4. episode ends

---

## 🎯 Reward Design

Reward is NOT binary.

Encourages:

* Partial correctness
* Severity awareness
* Correct final decision

Penalizes:

* False positives
* Wrong decisions

---

## 🤖 Baseline Agent (baseline.py)

Uses OpenAI API to simulate agent.

Steps:

1. Call reset()
2. Send PR diff to model
3. Ask for structured JSON output
4. Parse response
5. Call step()
6. Print score

---

### Prompt Design

Agent must return STRICT JSON:

{
"issues": [...],
"final_decision": "approve" | "request_changes"
}

---

## ⚠️ Error Handling

* Handle invalid JSON
* Default to empty issues if parsing fails
* Ensure no crashes

---

## 📄 openenv.yaml

Defines metadata:

* name
* description
* version
* tasks list

---

## 🐳 Docker Requirements

Must:

* Build successfully
* Install dependencies
* Run baseline script

---

## 🤗 Deployment

Deploy on Hugging Face Spaces:

* Use Docker SDK
* Public access required
* Environment must run without manual setup

---

## 📊 Evaluation Criteria

Your environment will be judged on:

1. Real-world utility
2. Task design quality
3. Grader correctness
4. Reward shaping
5. Code structure
6. Creativity

---

## 🚀 Advanced Features (Recommended)

* Multi-file dependency reasoning
* Severity-based scoring
* Structured feedback in reward
* Logging of evaluation details

---

## 🧠 Key Design Principles

* Deterministic grading
* Realistic PR scenarios
* Structured inputs/outputs
* Clear reward signals
* No randomness in scoring

---

## ❌ Common Mistakes

* Returning constant scores
* Weak or trivial tasks
* No penalty for false positives
* Non-deterministic grading
* Poor JSON parsing

---

## 🏁 Final Goal

Build an environment where:

> Any AI agent can be evaluated on its ability to perform real-world code reviews in a structured, reproducible, and measurable way.

---

## ✅ Definition of Done

* OpenEnv interface implemented
* 3+ tasks working
* Grader returns meaningful scores
* Baseline script reproducible
* Docker builds and runs
* HF Space deployed and accessible

---
