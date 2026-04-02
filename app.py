# app.py — entry point for HF Spaces (delegates to inference.py)
import uvicorn
from inference import app  # noqa: F401

if __name__ == "__main__":
    uvicorn.run("inference:app", host="0.0.0.0", port=8000)
