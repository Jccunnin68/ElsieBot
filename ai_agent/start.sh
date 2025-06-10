#!/bin/bash

echo "🚀 Starting Elsie AI Agent..."

# Wait for database to be available
echo "⏳ Waiting for database connection..."
until python -c "
import os
import psycopg2
try:
    conn = psycopg2.connect(
        host=os.getenv('DB_HOST', 'elsiebrain_db'),
        database=os.getenv('DB_NAME', 'elsiebrain'),
        user=os.getenv('DB_USER', 'elsie'),
        password=os.getenv('DB_PASSWORD', 'elsie123'),
        port=os.getenv('DB_PORT', '5432')
    )
    conn.close()
    print('Database connection successful!')
except Exception as e:
    print(f'Database connection failed: {e}')
    exit(1)
"; do
    echo "Database not ready, waiting..."
    sleep 2
done

echo "✅ Database connection verified!"

# Start the Python application
echo "🍺 Starting Elsie AI Agent..."
exec python main.py 