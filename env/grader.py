from typing import List, Tuple
from env.models import Issue, Action, Reward, RewardBreakdown
from env import config


# ── matching ──────────────────────────────────────────────────────────────────

def _matches(predicted: Issue, expected: Issue) -> bool:
    return (
        predicted.file == expected.file
        and predicted.type == expected.type
        and abs(predicted.line - expected.line) <= config.LINE_TOLERANCE
    )


def _classify(action: Action, expected: List[Issue]) -> Tuple[List[bool], int, int]:
    """Return (matched_flags, fp_normal, fp_high)."""
    matched = [False] * len(expected)
    fp_normal = fp_high = 0
    for pred in action.issues:
        hit = False
        for i, exp in enumerate(expected):
            if not matched[i] and _matches(pred, exp):
                matched[i] = True
                hit = True
                break
        if not hit:
            if pred.severity == "high":
                fp_high += 1
            else:
                fp_normal += 1
    return matched, fp_normal, fp_high


# ── dimension scorers ─────────────────────────────────────────────────────────

def _score_coverage(matched: List[bool], expected: List[Issue]) -> float:
    """40% — recall over all expected issues."""
    if not expected:
        return 1.0
    return sum(matched) / len(expected)


def _score_severity(matched: List[bool], expected: List[Issue]) -> float:
    """20% — recall over high-severity issues only."""
    high = [e for e in expected if e.severity == "high"]
    if not high:
        return 1.0
    high_matched = sum(
        1 for e, hit in zip(expected, matched)
        if hit and e.severity == "high"
    )
    base = high_matched / len(high)
    bonus = 0.2 if high_matched == len(high) else 0.0
    return min(1.0, base + bonus)


def _score_precision(fp_normal: int, fp_high: int, predicted_count: int) -> float:
    """20% — 1 - false_positive_rate, with extra penalty for high-severity FPs."""
    if predicted_count == 0:
        return 1.0
    fp_total = fp_normal + fp_high
    raw = 1.0 - (fp_total / predicted_count)
    high_fp_penalty = fp_high * 0.15
    return max(0.0, raw - high_fp_penalty)


def _score_explanation(action: Action) -> float:
    """5% — keyword presence + length factor, averaged over predicted issues."""
    if not action.issues:
        return 0.0
    scores = []
    for issue in action.issues:
        desc = issue.description.lower()
        length_factor = min(len(issue.description) / config.DESC_LENGTH_TARGET, 1.0)
        keyword_flag  = 1.0 if any(kw in desc for kw in config.DESC_KEYWORDS) else 0.0
        scores.append(0.5 * length_factor + 0.5 * keyword_flag)
    return sum(scores) / len(scores)


def _score_decision(action: Action, correct_decision: str) -> float:
    """15% — binary correct/incorrect."""
    return 1.0 if action.final_decision == correct_decision else 0.0


# ── post-score multipliers ────────────────────────────────────────────────────

def _apply_critical_miss_penalty(score: float, matched: List[bool], expected: List[Issue]) -> float:
    """If any high-severity issue is missed, multiply score by 0.70."""
    missed_high = any(
        not hit and e.severity == "high"
        for e, hit in zip(expected, matched)
    )
    return score * config.MISS_HIGH_MULTIPLIER if missed_high else score


def _apply_overconfidence_penalty(score: float, action: Action) -> float:
    """If agent reports many issues but still approves, penalise."""
    if (
        len(action.issues) > config.OVERCONFIDENCE_THRESHOLD
        and action.final_decision == "approve"
    ):
        return score * config.OVERCONFIDENCE_MULTIPLIER
    return score


# ── feedback ──────────────────────────────────────────────────────────────────

def _build_feedback(
    breakdown: RewardBreakdown,
    matched: List[bool],
    expected: List[Issue],
    fp_normal: int,
    fp_high: int,
    decision_correct: bool,
    decision: str,
    score: float,
) -> str:
    missed = [e for e, hit in zip(expected, matched) if not hit]
    missed_high = sum(1 for e in missed if e.severity == "high")
    fp_total = fp_normal + fp_high
    parts = [
        f"Score: {score:.2f}",
        f"[Coverage:{breakdown.issue_coverage:.2f}",
        f"Severity:{breakdown.severity_awareness:.2f}",
        f"Precision:{breakdown.precision:.2f}",
        f"Explanation:{breakdown.explanation_quality:.2f}",
        f"Decision:{breakdown.decision_correctness:.2f}]",
        f"Matched {sum(matched)}/{len(expected)}.",
        f"Missed-high:{missed_high}.",
        f"FP:{fp_total}({fp_high} high).",
        f"Decision:{'correct' if decision_correct else 'incorrect'}({decision}).",
    ]
    if missed:
        detail = "; ".join(f"{e.file}:{e.line}[{e.type}/{e.severity}]" for e in missed[:3])
        if len(missed) > 3:
            detail += f"+{len(missed)-3}"
        parts.append(f"Missed:{detail}.")
    return " ".join(parts)


# ── main entry point ──────────────────────────────────────────────────────────

def grade(action: Action, expected: List[Issue], correct_decision: str) -> Reward:
    matched, fp_normal, fp_high = _classify(action, expected)
    predicted_count = len(action.issues)
    decision_correct = action.final_decision == correct_decision

    coverage    = _score_coverage(matched, expected)
    severity    = _score_severity(matched, expected)
    precision   = _score_precision(fp_normal, fp_high, predicted_count)
    explanation = _score_explanation(action)
    decision    = _score_decision(action, correct_decision)

    raw = (
        coverage    * config.WEIGHT_ISSUE_COVERAGE +
        severity    * config.WEIGHT_SEVERITY_AWARENESS +
        precision   * config.WEIGHT_PRECISION +
        explanation * config.WEIGHT_EXPLANATION +
        decision    * config.WEIGHT_DECISION
    )

    # Post-score multipliers (Phase 2 only — action has final_decision)
    if action.final_decision is not None:
        raw = _apply_critical_miss_penalty(raw, matched, expected)
        raw = _apply_overconfidence_penalty(raw, action)

    final_score = max(0.01, min(0.99, raw))

    breakdown = RewardBreakdown(
        issue_coverage=round(coverage, 3),
        severity_awareness=round(severity, 3),
        precision=round(precision, 3),
        explanation_quality=round(explanation, 3),
        decision_correctness=round(decision, 3),
    )

    feedback = _build_feedback(
        breakdown, matched, expected,
        fp_normal, fp_high, decision_correct,
        action.final_decision, final_score,
    )

    return Reward(score=final_score, feedback=feedback, breakdown=breakdown)
