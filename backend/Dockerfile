FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python deps first (cached layer)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create temp directory
RUN mkdir -p /tmp/pdf-jobs

# Non-root user for security
RUN useradd -m -u 1001 appuser && chown -R appuser /app /tmp/pdf-jobs
USER appuser

EXPOSE 8000

# Uvicorn with single worker (use Railway's horizontal scaling instead)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
