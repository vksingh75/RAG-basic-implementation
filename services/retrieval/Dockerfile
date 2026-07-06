FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HF_HOME=/root/.cache/huggingface \
    OMP_NUM_THREADS=4

WORKDIR /app

# CPU-only torch BEFORE requirements so sentence-transformers doesn't pull
# CUDA wheels (~5GB). The +cpu local version pin guarantees the wheel comes
# from the pytorch CPU index (verified: torch-2.12.1+cpu cp312 manylinux).
RUN pip install --no-cache-dir torch==2.12.1+cpu \
    --extra-index-url https://download.pytorch.org/whl/cpu

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

EXPOSE 8003

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8003"]
