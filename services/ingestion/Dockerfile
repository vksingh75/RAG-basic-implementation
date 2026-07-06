# Ingestion service — FastAPI :8002
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    # HuggingFace model cache — mounted as the shared hf_cache volume in compose
    HF_HOME=/root/.cache/huggingface

WORKDIR /srv

# CPU-only torch/torchvision FIRST so requirements.txt resolution reuses them.
# The +cpu local tag only exists on the pytorch index, guaranteeing CPU wheels
# (verified: manylinux_2_28 x86_64 + aarch64 cp312 wheels available).
RUN pip install --no-cache-dir \
    torch==2.12.1+cpu torchvision==0.27.1+cpu \
    --extra-index-url https://download.pytorch.org/whl/cpu

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Native runtime libs required by opencv-python (pulled in by docling):
# cv2 dlopens libGL.so.1 / libglib / libxcb, none of which ship in
# python:3.12-slim. Placed after the pip layers so image rebuilds reuse the
# large cached torch/docling install layers.
RUN apt-get update \
    && apt-get install -y --no-install-recommends libgl1 libglib2.0-0 libxcb1 \
    && rm -rf /var/lib/apt/lists/*

COPY app ./app

EXPOSE 8002

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8002"]
