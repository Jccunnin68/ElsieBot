FROM python:3.11-slim

# Install system dependencies for PostgreSQL and health checks
RUN apt-get update && apt-get install -y \
    curl \
    postgresql \
    postgresql-client \
    postgresql-contrib \
    sudo \
    && rm -rf /var/lib/apt/lists/*

# Set PostgreSQL environment
ENV PATH="/usr/lib/postgresql/15/bin:$PATH"
ENV PGDATA="/var/lib/postgresql/data"
ENV PYTHONPATH="${PYTHONPATH}:/app"

WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/ || exit 1

# Make start script executable
RUN chmod +x start.sh

CMD ["./start.sh"] 