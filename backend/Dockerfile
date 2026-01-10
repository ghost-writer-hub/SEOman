FROM python:3.11-slim AS base

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# Install base dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Development stage
FROM base AS development

COPY requirements.txt .

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Install Playwright browsers and dependencies
# Note: This adds ~400MB to the image but is required for JS rendering
RUN playwright install chromium && \
    playwright install-deps chromium

COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# Development stage without Playwright (lighter image)
FROM base AS development-light

COPY requirements.txt .

# Remove playwright from requirements for light build
RUN pip install --no-cache-dir --upgrade pip && \
    grep -v "playwright" requirements.txt | pip install --no-cache-dir -r /dev/stdin

COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# Production stage with Playwright
FROM base AS production

COPY requirements.txt .

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Install Playwright browsers and dependencies
RUN playwright install chromium && \
    playwright install-deps chromium

COPY . .

# Create non-root user
RUN useradd -m appuser && \
    chown -R appuser:appuser /app && \
    # Playwright needs a writable cache directory
    mkdir -p /home/appuser/.cache && \
    chown -R appuser:appuser /home/appuser/.cache

USER appuser

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]

# Production stage without Playwright (lighter image)
FROM base AS production-light

COPY requirements.txt .

RUN pip install --no-cache-dir --upgrade pip && \
    grep -v "playwright" requirements.txt | pip install --no-cache-dir -r /dev/stdin

COPY . .

RUN useradd -m appuser && \
    chown -R appuser:appuser /app

USER appuser

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
