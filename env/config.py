# Multi-dimensional grading weights (must sum to 1.0)
WEIGHT_ISSUE_COVERAGE     = 0.40
WEIGHT_SEVERITY_AWARENESS = 0.20
WEIGHT_PRECISION          = 0.20
WEIGHT_EXPLANATION        = 0.05
WEIGHT_DECISION           = 0.15

# Severity scoring
SEVERITY_WEIGHTS = {"low": 0.2, "medium": 0.5, "high": 1.0}
LINE_TOLERANCE   = 1

# Penalties
FP_PENALTY_NORMAL  = 0.10
FP_PENALTY_HIGH    = 0.25
MISS_HIGH_MULTIPLIER = 0.70   # multiply final score if any high-severity missed

# Overconfidence penalty
OVERCONFIDENCE_THRESHOLD  = 2   # predicted issues > this AND decision == "approve"
OVERCONFIDENCE_MULTIPLIER = 0.80

# Explanation quality
DESC_KEYWORDS = {"error", "issue", "bug", "risk", "vulnerability", "inject",
                 "overflow", "leak", "unsafe", "missing", "incorrect", "invalid"}
DESC_LENGTH_TARGET = 80   # chars for full length score

MAX_STEPS = 2
