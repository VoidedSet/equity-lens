FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HF_HOME=/opt/hf_cache \
    SENTENCE_TRANSFORMERS_HOME=/opt/hf_cache

RUN apt-get update && apt-get install -y --no-install-recommends \
        poppler-utils \
        libgl1 \
        libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY cloud/worker/requirements.txt /app/cloud/worker/requirements.txt
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir --extra-index-url https://download.pytorch.org/whl/cpu torch \
    && pip install --no-cache-dir -r /app/cloud/worker/requirements.txt

# Bake MiniLM weights into the image to avoid cold-start downloads on Fargate
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"

COPY cloud /app/cloud
COPY ["pdf extraction pipeline", "/app/pdf extraction pipeline"]

ENTRYPOINT ["python", "-m", "cloud.worker.entrypoint"]
