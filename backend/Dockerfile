FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DEFAULT_TIMEOUT=120 \
    PIP_RETRIES=10 \
    PLAYWRIGHT_DOWNLOAD_CONNECTION_TIMEOUT=600000

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ curl wget gnupg \
    libnss3 libatk1.0-0 libatk-bridge2.0-0 \
    libcups2 libdrm2 libxkbcommon0 libxcomposite1 \
    libxdamage1 libxfixes3 libxrandr2 libgbm1 \
    libpango-1.0-0 libcairo2 libasound2 \
    fonts-liberation libappindicator3-1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --prefer-binary --progress-bar off --no-cache-dir -r requirements.txt

RUN python -m playwright install chromium

COPY . .

RUN mkdir -p models database

EXPOSE 5000

CMD ["python", "run.py"]
