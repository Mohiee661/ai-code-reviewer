# server/app.py - OpenEnv server entry point
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from server import app  # noqa: F401