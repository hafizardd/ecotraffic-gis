FROM python:3.10-slim

# The snapshot fallback and health checks capture one frame with FFmpeg.
RUN apt-get update && apt-get install -y ffmpeg && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install \
        --default-timeout=300 \
        --retries 5 \
        --no-cache-dir \
        -r requirements.txt

COPY . .

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
