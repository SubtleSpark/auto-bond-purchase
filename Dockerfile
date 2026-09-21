FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    BROWSER=chromium \
    HEADLESS=true

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    wget \
    gnupg \
    unzip \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY pyproject.toml ./

RUN pip install --no-cache-dir \
    playwright>=1.50.0 \
    requests \
    python-dotenv \
    tensorflow>=2.15.0 \
    opencv-python-headless>=4.9.0 \
    "numpy>=1.23.5,<2.0.0"

RUN python -m playwright install --with-deps chromium

COPY main.py ./
COPY autobond/ ./autobond/
COPY captcha/ ./captcha/
COPY models/ ./models/

CMD ["python", "main.py"]
