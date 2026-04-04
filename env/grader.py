from typing import List
from env.models import Issue, Action, Reward

SEVERITY_WEIGHTS = {"low": 0.2, "medium": 0.5, "high": 1.0}
LINE_TOLERANCE = 1

# Penalties & bonuses
FP_PENALTY_NORMAL = 0.1
FP_PENALTY_HIGH   = 0.25   # heavier penalty for high-severity false positives
MISS_HIGH_PENALTY = 0.5    # per missed high-severity expected issue
ALL_HIGH_BONUS    = 0.1    # bonus for catching every high-severity issue
DECISION_BONUS    = 0.2


def _matches(predicted: Issue, expected: Issue) -> bool:
    """Match if file + type agree and line is within tolerance."""
    return (
        predicted.file == expected.file
        and predicted.type == expected.type
        and abs(predicted.line - expected.line) <= LINE_TOLERANCE
    )


def grade(action: Action, expected_issues: List[Issue], correct_decision: str) -> Reward:
    """
    Score an agent action against ground truth.

    Base score  = correct_weight / total_weight
    Adjustments:
      - missed high-severity issue  : -0.5 each
      - all high-severity found     : +0.1 bonus
      - false positive (normal)     : -0.1 each
      - false positive (high sev)   : -0.25 each
      - correct decision            : +0.2
      - wrong decision              : -0.2
    Final score clamped to [0.0, 1.0].
    """
    total_weight = sum(SEVERITY_WEIGHTS[e.severity] for e in expected_issues)
    high_expected = [e for e in expected_issues if e.severity == "high"]

    matched_expected = [False] * len(expected_issues)
    correct_weight = 0.0
    fp_normal = 0
    fp_high = 0

    for pred in action.issues:
        hit = False
        for i, exp in enumerate(expected_issues):
            if not matched_expected[i] and _matches(pred, exp):
                matched_expected[i] = True
                correct_weight += SEVERITY_WEIGHTS[exp.severity]
                hit = True
                break
        if not hit:
            if pred.severity == "high":
                fp_high += 1
            else:
                fp_normal += 1

    matched_count = sum(matched_expected)
    missed = [e for e, hit in zip(expected_issues, matched_expected) if not hit]
    missed_high = [e for e in missed if e.severity == "high"]
    matched_high_count = len(high_expected) - len(missed_high)

    # ── score assembly ────────────────────────────────────────────────────────
    base = (correct_weight / total_weight) if total_weight > 0 else 0.0

    penalty  = len(missed_high) * MISS_HIGH_PENALTY
    penalty += fp_normal * FP_PENALTY_NORMAL
    penalty += fp_high   * FP_PENALTY_HIGH

    all_high_found = len(high_expected) > 0 and len(missed_high) == 0
    bonus  = ALL_HIGH_BONUS if all_high_found else 0.0
    bonus += DECISION_BONUS if action.final_decision == correct_decision else -DECISION_BONUS

    final_score = max(0.0, min(1.0, base - penalty + bonus))

    # ── precision / recall ────────────────────────────────────────────────────
    predicted_count = len(action.issues)
    precision = matched_count / predicted_count if predicted_count > 0 else 0.0
    recall    = matched_count / len(expected_issues) if expected_issues else 0.0

    # ── feedback ──────────────────────────────────────────────────────────────
    fp_total = fp_normal + fp_high
    decision_word = "correct" if action.final_decision == correct_decision else "incorrect"
    parts = [
        f"Matched {matched_count}/{len(expected_issues)} issues.",
        f"Missed high-severity: {len(missed_high)}.",
        f"False positives: {fp_total} ({fp_high} high-severity).",
        f"Decision: {decision_word} ({action.final_decision}).",
        f"Precision: {precision:.2f}  Recall: {recall:.2f}.",
        f"Score: {final_score:.2f}.",
    ]
    if missed:
        desc = "; ".join(f"{e.file}:{e.line} [{e.type}/{e.severity}]" for e in missed)
        parts.append(f"Missed: {desc}.")

    return Reward(score=final_score, feedback=" ".join(parts))
