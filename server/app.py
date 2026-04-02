"""
FastAPI application for the Code Review Environment.

Usage:
    uvicorn server.app:app --host 0.0.0.0 --port 7860
    uv run --project . server
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from openenv.core.env_server.http_server import create_app
from openenv.core.env_server.types import Action, Observation

try:
    from code_review_env.server.code_review_environment import CodeReviewEnvironment
except ImportError:
    from server.code_review_environment import CodeReviewEnvironment

app = create_app(
    CodeReviewEnvironment,
    Action,
    Observation,
    env_name="code_review_env",
)


def main():
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=7860)


if __name__ == "__main__":
    main()
