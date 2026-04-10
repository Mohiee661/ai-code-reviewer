"""Compatibility entry point for platforms that look for app.py.

The production Hugging Face Space uses Docker and starts server.app:app.
"""
from server.app import app
