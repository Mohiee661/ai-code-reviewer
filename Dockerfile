FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --upgrade pip && pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Serve the OpenEnv HTTP API on port 8000
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000"]
