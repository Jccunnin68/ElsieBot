FROM python:3.11-slim

# Add PostgreSQL apt repository to get version 16
RUN apt-get update \
    && apt-get install -y curl gnupg2 \
    && curl https://www.postgresql.org/media/keys/ACCC4CF8.asc | apt-key add - \
    && echo "deb http://apt.postgresql.org/pub/repos/apt bookworm-pgdg main" > /etc/apt/sources.list.d/pgdg.list \
    && apt-get update \
    && apt-get install -y postgresql-client-16 \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first to leverage Docker cache
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create backups directory
RUN mkdir -p backups

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Create a restore script that uses environment variables
RUN echo '#!/bin/bash\n\
echo "🔄 Waiting for database to be ready..."\n\
export PGPASSWORD="${DB_PASSWORD:-elsie123}"\n\
export DB_HOST="${DB_HOST:-elsiebrain_db}"\n\
export DB_NAME="${DB_NAME:-elsiebrain}"\n\
export DB_USER="${DB_USER:-elsie}"\n\
export DB_PORT="${DB_PORT:-5432}"\n\
\n\
while ! pg_isready -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER"; do\n\
  echo "   ⏳ Database not ready, waiting..."\n\
  sleep 2\n\
done\n\
echo "✅ Database is ready!"\n\
\n\
echo "🗄️ Restoring seed backup..."\n\
if [ -f "/app/backups/seed_backup.sql" ]; then\n\
  echo "📁 Found seed backup file, restoring..."\n\
  psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -f /app/backups/seed_backup.sql\n\
  if [ $? -eq 0 ]; then\n\
    echo "✅ Seed backup restored successfully!"\n\
  else\n\
    echo "❌ Failed to restore seed backup!"\n\
    exit 1\n\
  fi\n\
else\n\
  echo "⚠️ No seed backup found, running sample data populator..."\n\
  python populate_db.py\n\
fi' > /app/restore_seed.sh \
    && chmod +x /app/restore_seed.sh

# Create an interactive startup script
RUN echo '#!/bin/bash\n\
echo "🚀 DB Populator Interactive Container"\n\
echo "===================================="\n\
export PGPASSWORD="${DB_PASSWORD:-elsie123}"\n\
export DB_HOST="${DB_HOST:-elsiebrain_db}"\n\
export DB_NAME="${DB_NAME:-elsiebrain}"\n\
export DB_USER="${DB_USER:-elsie}"\n\
export DB_PORT="${DB_PORT:-5432}"\n\
\n\
echo "🔄 Waiting for database to be ready..."\n\
while ! pg_isready -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER"; do\n\
  echo "   ⏳ Database not ready, waiting..."\n\
  sleep 2\n\
done\n\
echo "✅ Database is ready!"\n\
echo ""\n\
echo "📋 Available commands:"\n\
echo "  python populate_db.py          - Populate with sample data"\n\
echo "  python wiki_crawler.py --help  - See crawler options"\n\
echo "  python backup_db.py backup     - Create backup"\n\
echo "  python backup_db.py restore    - Restore from backup"\n\
echo "  python backup_db.py seed       - Create seed backup"\n\
echo "  /app/restore_seed.sh           - Restore seed backup"\n\
echo ""\n\
echo "💡 Container will stay running. Use Ctrl+C to exit."\n\
echo "   Or run: docker exec -it <container_name> /bin/bash"\n\
echo ""\n\
\n\
# Keep container running\n\
tail -f /dev/null' > /app/interactive_start.sh \
    && chmod +x /app/interactive_start.sh

# Keep container running for interactive use
CMD ["/app/interactive_start.sh"] 