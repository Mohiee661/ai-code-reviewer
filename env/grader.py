from typing import List
from env.models import Issue, Action, Reward
from env import config


def _matches(predicted: Issue, expected: Issue) -> bool:
    return (
        predicted.file == expected.file
        and predicted.type == expected.type
        and abs(predicted.line - expected.line) <= config.LINE_TOLERANCE
    )


def _classify(action: Action, expected: List[Issue]):
    """Return (matched_flags, correct_weight, fp_normal, fp_high)."""
    matched = [False] * len(expected)
    correct_weight = 0.0
    fp_normal = fp_high = 0

    for pred in action.issues:
        hit = False
        for i, exp in enumerate(expected):
            if not matched[i] and _matches(pred, exp):
                matched[i] = True
                correct_weight += config.SEVERITY_WEIGHTS[exp.severity]
                hit = True
                break
        if not hit:
            if pred.severity == "high":
                fp_high += 1
            else:
                fp_normal += 1

    return matched, correct_weight, fp_normal, fp_high


def _build_feedback(matched, expected, fp_normal, fp_high, decision_correct, decision, score, precision, recall):
    missed = [e for e, hit in zip(expected, matched) if not hit]
    missed_high = sum(1 for e in missed if e.severity == "high")
    fp_total = fp_normal + fp_high
    parts = [
        f"Matched {sum(matched)}/{len(expected)} issues.",
        f"Missed high-severity: {missed_high}.",
        f"False positives: {fp_total} ({fp_high} high-severity).",
        f"Decision: {'correct' if decision_correct else 'incorrect'} ({decision}).",
        f"Precision: {precision:.2f}  Recall: {recall:.2f}.",
        f"Score: {score:.2f}.",
    ]
    if missed:
        detail = "; ".join(f"{e.file}:{e.line} [{e.type}/{e.severity}]" for e in missed)
        parts.append(f"Missed: {detail}.")
    return " ".join(parts)


def grade(action: Action, expected: List[Issue], correct_decision: str) -> Reward:
    total_weight = sum(config.SEVERITY_WEIGHTS[e.severity] for e in expected)
    high_expected = [e for e in expected if e.severity == "high"]

    matched, correct_weight, fp_normal, fp_high = _classify(action, expected)

    missed_high = [e for e, hit in zip(expected, matched) if not hit and e.severity == "high"]
    all_high_found = len(high_expected) > 0 and len(missed_high) == 0
    decision_correct = action.final_decision == correct_decision

    base    = (correct_weight / total_weight) if total_weight > 0 else 0.0
    penalty = len(missed_high) * config.MISS_HIGH_PENALTY
    penalty += fp_normal * config.FP_PENALTY_NORMAL
    penalty += fp_high   * config.FP_PENALTY_HIGH
    bonus   = (config.ALL_HIGH_BONUS if all_high_found else 0.0)
    bonus  += config.DECISION_BONUS if decision_correct else -config.DECISION_BONUS

    score = max(0.0, min(1.0, base - penalty + bonus))

    matched_count   = sum(matched)
    predicted_count = len(action.issues)
    precision = matched_count / predicted_count if predicted_count > 0 else 0.0
    recall    = matched_count / len(expected)   if expected        else 0.0

    feedback = _build_feedback(
        matched, expected, fp_normal, fp_high,
        decision_correct, action.final_decision, score, precision, recall,
    )
    return Reward(score=score, feedback=feedback)
