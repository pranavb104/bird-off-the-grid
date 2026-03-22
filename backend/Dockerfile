FROM python:3.11-slim-bookworm
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
        ffmpeg alsa-utils libsndfile1 libasound2 supervisor \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
# ai-edge-litert may lack arm64 wheels; fall back to tflite-runtime
RUN pip install --no-cache-dir --upgrade pip \
    && (pip install --no-cache-dir ai-edge-litert \
        || pip install --no-cache-dir tflite-runtime) \
    && grep -v 'ai-edge-litert' requirements.txt \
       | pip install --no-cache-dir -r /dev/stdin

COPY . .
RUN mkdir -p data/StreamData data/detections data/bird_images

COPY supervisord.conf /etc/supervisor/conf.d/birdnet.conf

EXPOSE 7007
CMD ["/usr/bin/supervisord", "-n", "-c", "/etc/supervisor/supervisord.conf"]
