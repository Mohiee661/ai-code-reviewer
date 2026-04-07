# Multi-dimensional grading weights
WEIGHT_ISSUE_COVERAGE      = 0.40
WEIGHT_SEVERITY_AWARENESS  = 0.20
WEIGHT_PRECISION           = 0.20
WEIGHT_EXPLANATION         = 0.10
WEIGHT_DECISION            = 0.10

# Severity scoring
SEVERITY_WEIGHTS = {"low": 0.2, "medium": 0.5, "high": 1.0}
LINE_TOLERANCE   = 1

# Penalties
FP_PENALTY_NORMAL = 0.10
FP_PENALTY_HIGH   = 0.25
MISS_HIGH_PENALTY = 0.50

# Bonuses
ALL_HIGH_BONUS    = 0.10
CLEAR_DESC_BONUS  = 0.05  # per issue with clear description

# Explanation quality thresholds
MIN_DESC_LENGTH   = 20
GOOD_DESC_LENGTH  = 50

MAX_STEPS = 2
