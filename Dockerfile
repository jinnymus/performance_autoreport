# Public image: Chrome + Python for Grafana snapshots and the report service.
# Chrome images are amd64-only; on Apple Silicon: docker build --platform linux/amd64 .
#
# Base image may register deadsnakes "python3" as 3.14 — use python3.12 explicitly for wheels/headers.
FROM --platform=linux/amd64 selenium/standalone-chrome:latest

USER root
ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
        python3.12 python3.12-venv python3.12-dev \
        build-essential libffi-dev libssl-dev \
        xclip xsel \
    && rm -rf /var/lib/apt/lists/* \
    && python3.12 -m venv /opt/venv

ENV PATH="/opt/venv/bin:$PATH"
ENV VIRTUAL_ENV=/opt/venv

WORKDIR /app

COPY requirements.txt .
# Cap pip<25: newer pip isolated builds have pulled the wrong interpreter on this base image.
RUN pip install --no-cache-dir --upgrade 'pip>=24.2,<25' setuptools wheel \
    && PIP_PREFER_BINARY=1 pip install --no-cache-dir -r requirements.txt

ENV TZ=UTC
ENV DISPLAY=:99
EXPOSE 9200

COPY . .
CMD ["python3", "src/main.py"]
