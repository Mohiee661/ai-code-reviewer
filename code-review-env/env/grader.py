from typing import List
from env.models import Issue, Action, Reward

SEVERITY_WEIGHTS = {"low": 0.2, "medium": 0.5, "high": 1.0}
LINE_TOLERANCE = 1
FALSE_POSITIVE_PENALTY = 0.1
DECISION_BONUS = 0.2


def _matches(predicted: Issue, expected: Issue) -> bool:
    """An issue matches if file and type agree and line is within tolerance."""
    return (
        predicted.file == expected.file
        and predicted.type == expected.type
        and abs(predicted.line - expected.line) <= LINE_TOLERANCE
    )


def grade(action: Action, expected_issues: List[Issue], correct_decision: str) -> Reward:
    """
    Score an agent action against ground truth.

    Components:
      - correct_weight  : sum of severity weights for matched expected issues
      - total_weight    : sum of severity weights for all expected issues
      - false_positives : predicted issues that match no expected issue
      - decision_bonus  : +DECISION_BONUS if correct, -DECISION_BONUS if wrong

    Formula:
      base   = correct_weight / total_weight   (0 if no expected issues)
      score  = clamp(base - fp * FP_PENALTY + decision_bonus, 0.0, 1.0)
    """
    total_weight = sum(SEVERITY_WEIGHTS[e.severity] for e in expected_issues)

    # Track which expected issues have been matched (each can only be claimed once)
    matched_expected = [False] * len(expected_issues)
    correct_weight = 0.0
    false_positives = 0

    for pred in action.issues:
        matched = False
        for i, exp in enumerate(expected_issues):
            if not matched_expected[i] and _matches(pred, exp):
                matched_expected[i] = True
                correct_weight += SEVERITY_WEIGHTS[exp.severity]
                matched = True
                break
        if not matched:
            false_positives += 1

    base = (correct_weight / total_weight) if total_weight > 0 else 0.0
    decision_bonus = DECISION_BONUS if action.final_decision == correct_decision else -DECISION_BONUS
    raw = base - false_positives * FALSE_POSITIVE_PENALTY + decision_bonus
    final_score = max(0.0, min(1.0, raw))

    # Build human-readable feedback
    matched_count = sum(matched_expected)
    missed_count = len(expected_issues) - matched_count
    feedback_parts = [
        f"Matched {matched_count}/{len(expected_issues)} expected issues.",
        f"False positives: {false_positives}.",
        f"Decision: {'correct' if action.final_decision == correct_decision else 'incorrect'} ({action.final_decision}).",
        f"Final score: {final_score:.2f}.",
    ]
    if missed_count:
        missed = [e for e, hit in zip(expected_issues, matched_expected) if not hit]
        missed_desc = "; ".join(f"{e.file}:{e.line} [{e.type}/{e.severity}]" for e in missed)
        feedback_parts.append(f"Missed: {missed_desc}.")

    return Reward(score=final_score, feedback=" ".join(feedback_parts))
