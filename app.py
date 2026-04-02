# app.py - HF Space entry point
import uvicorn
from api import app  # noqa: F401

if __name__ == "__main__":
    uvicorn.run("api:app", host="0.0.0.0", port=7860)