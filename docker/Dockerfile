ARG PYTHON_VERSION=3.12.9
FROM python:${PYTHON_VERSION}-slim

ARG UV_VERSION=0.11.21

ENV DEBIAN_FRONTEND=noninteractive \
    PATH=/workspace/.venv/bin:$PATH \
    HF_HOME=/workspace/.cache/huggingface \
    HF_LEROBOT_HOME=/workspace/.cache/huggingface/lerobot \
    TORCH_HOME=/workspace/.cache/torch

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libglib2.0-0 ffmpeg \
    libusb-1.0-0 \
    libgl1 \
    libsm6 libice6 \
    fonts-dejavu-core \
    && apt-get clean && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir "uv==${UV_VERSION}"

WORKDIR /workspace

COPY pyproject.toml uv.lock ./
RUN uv venv .venv && uv sync --frozen --no-dev

RUN mkdir -p .venv/lib/python3.12/site-packages/cv2/qt/fonts \
    && cp /usr/share/fonts/truetype/dejavu/*.ttf .venv/lib/python3.12/site-packages/cv2/qt/fonts/ 2>/dev/null || true

COPY scripts/ scripts/

CMD ["/bin/bash"]
