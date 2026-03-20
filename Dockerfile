FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose port for HTTP/SSE transport
EXPOSE 8100

# Default: run in streamable-http mode (Apify Standby compatible)
CMD ["python", "server.py", "--transport", "streamable-http", "--port", "8100"]
