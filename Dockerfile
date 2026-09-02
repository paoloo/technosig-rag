FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN groupadd --gid 1001 tecnosig \
    && useradd --uid 1001 --gid 1001 --create-home tecnosig

COPY requirements-server.txt ./
RUN python -m pip install --upgrade pip \
    && python -m pip install -r requirements-server.txt

# Sentence Transformers keeps vision support optional. Install its image extra
# separately so ordinary dependency edits can reuse the large CUDA layer.
RUN python -m pip install "sentence-transformers[image]>=5.4,<6"

# PyTorch/Triton compiles a small GPU launcher when the Qwen reranker first
# runs. Keep only the compiler required for that runtime compilation.
RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc libc6-dev \
    && rm -rf /var/lib/apt/lists/*

COPY --chown=1001:1001 . .

USER 1001:1001
EXPOSE 8000

CMD ["python", "mcp_server.py"]
