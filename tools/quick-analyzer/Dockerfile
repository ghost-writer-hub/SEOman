FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install python-seo-analyzer
RUN pip install --no-cache-dir pyseoanalyzer>=1.0.1 requests

# Copy application code
COPY . .

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import requests; requests.get('http://0.0.0.0:8080/health', timeout=5)" || exit 1"

# Expose port
EXPOSE 8080

# Start the analyzer server
CMD ["python-seo-analyzer", "serve", "--port", "8080", "--host", "0.0.0.0"]
