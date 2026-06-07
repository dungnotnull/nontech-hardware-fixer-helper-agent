# syntax=docker/dockerfile:1
FROM python:3.12-slim as base

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1-mesa-glx \
    libglib2.0-0 \
    tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml ./
RUN pip install --upgrade pip && pip install uv
RUN uv pip install --system -e ".[dev]"

COPY src/ ./src/
COPY config/ ./config/
COPY data/ ./data/

RUN uv pip install --system -e "."

FROM base as dev
ENV LOG_LEVEL=DEBUG
CMD ["uvicorn", "fixeragent.api.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

FROM base as prod
ENV LOG_LEVEL=INFO
CMD ["uvicorn", "fixeragent.api.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
