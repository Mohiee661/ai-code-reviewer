from typing import List, Tuple
from env.models import Issue, Action, Reward, RewardBreakdown
from env import config


def _matches(predicted: Issue, expected: Issue) -> bool:
    return (
        predicted.file == expected.file
        and predicted.type == expected.type
        and abs(predicted.line - expected.line) <= config.LINE_TOLERANCE
    )


def _score_issue_coverage(matched: List[bool], expected: List[Issue]) -> float:
    """40% — How many true issues were found."""
    if not expected:
        return 1.0
    matched_count = sum(matched)
    recall = matched_count / len(expected)
    
    # Extra penalty for missing high-severity
    high_expected = [e for e in expected if e.severity == "high"]
    missed_high = [e for e, hit in zip(expected, matched) if not hit and e.severity == "high"]
    high_penalty = len(missed_high) * 0.15
    
    return max(0.0, recall - high_penalty)


def _score_severity_awareness(matched: List[bool], expected: List[Issue], action: Action) -> float:
    """20% — Correctly identifying high-severity issues."""
    high_expected = [e for e in expected if e.severity == "high"]
    if not high_expected:
        return 1.0
    
    high_matched = sum(1 for e, hit in zip(expected, matched) if hit and e.severity == "high")
    high_recall = high_matched / len(high_expected)
    
    # Bonus if ALL high-severity found
    bonus = 0.2 if high_matched == len(high_expected) else 0.0
    return min(1.0, high_recall + bonus)


def _score_precision(fp_normal: int, fp_high: int, predicted_count: int) -> float:
    """20% — Avoiding false positives."""
    if predicted_count == 0:
        return 1.0
    
    fp_total = fp_normal + fp_high
    precision_raw = 1.0 - (fp_total / predicted_count)
    
    # Extra penalty for high-severity false positives
    high_fp_penalty = fp_high * 0.15
    return max(0.0, precision_raw - high_fp_penalty)


def _score_explanation_quality(action: Action, matched: List[bool]) -> float:
    """10% — Clear, actionable descriptions."""
    if not action.issues:
        return 0.0
    
    quality_scores = []
    for issue in action.issues:
        desc_len = len(issue.description)
        if desc_len < config.MIN_DESC_LENGTH:
            quality_scores.append(0.3)
        elif desc_len < config.GOOD_DESC_LENGTH:
            quality_scores.append(0.7)
        else:
            quality_scores.append(1.0)
    
    return sum(quality_scores) / len(quality_scores)


def _score_decision(action: Action, correct_decision: str) -> float:
    """10% — Correct approve/request_changes."""
    return 1.0 if action.final_decision == correct_decision else 0.0


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


def _build_feedback(breakdown: RewardBreakdown, matched: List[bool], expected: List[Issue], 
                     fp_normal: int, fp_high: int, decision_correct: bool, decision: str, 
                     score: float) -> str:
    missed = [e for e, hit in zip(expected, matched) if not hit]
    missed_high = sum(1 for e in missed if e.severity == "high")
    fp_total = fp_normal + fp_high
    
    parts = [
        f"Score: {score:.2f}",
        f"[Coverage: {breakdown.issue_coverage:.2f}",
        f"Severity: {breakdown.severity_awareness:.2f}",
        f"Precision: {breakdown.precision:.2f}",
        f"Explanation: {breakdown.explanation_quality:.2f}",
        f"Decision: {breakdown.decision_correctness:.2f}]",
        f"Matched {sum(matched)}/{len(expected)} issues.",
        f"Missed high-severity: {missed_high}.",
        f"False positives: {fp_total} ({fp_high} high).",
        f"Decision: {'correct' if decision_correct else 'incorrect'} ({decision}).",
    ]
    
    if missed:
        detail = "; ".join(f"{e.file}:{e.line} [{e.type}/{e.severity}]" for e in missed[:3])
        if len(missed) > 3:
            detail += f" +{len(missed)-3} more"
        parts.append(f"Missed: {detail}.")
    
    return " ".join(parts)


def grade(action: Action, expected: List[Issue], correct_decision: str) -> Reward:
    """Multi-dimensional grading with weighted components."""
    matched, fp_normal, fp_high = _classify(action, expected)
    predicted_count = len(action.issues)
    decision_correct = action.final_decision == correct_decision
    
    # Compute each dimension
    coverage   = _score_issue_coverage(matched, expected)
    severity   = _score_severity_awareness(matched, expected, action)
    precision  = _score_precision(fp_normal, fp_high, predicted_count)
    explanation = _score_explanation_quality(action, matched)
    decision   = _score_decision(action, correct_decision)
    
    # Weighted combination
    raw_score = (
        coverage    * config.WEIGHT_ISSUE_COVERAGE +
        severity    * config.WEIGHT_SEVERITY_AWARENESS +
        precision   * config.WEIGHT_PRECISION +
        explanation * config.WEIGHT_EXPLANATION +
        decision    * config.WEIGHT_DECISION
    )
    
    # Clamp to (0, 1)
    final_score = max(0.01, min(0.99, raw_score))
    
    breakdown = RewardBreakdown(
        issue_coverage=round(coverage, 3),
        severity_awareness=round(severity, 3),
        precision=round(precision, 3),
        explanation_quality=round(explanation, 3),
        decision_correctness=round(decision, 3),
    )
    
    feedback = _build_feedback(
        breakdown, matched, expected, fp_normal, fp_high,
        decision_correct, action.final_decision, final_score
    )
    
    return Reward(score=final_score, feedback=feedback, breakdown=breakdown)
