#!/bin/bash

echo "🚀 Starting Elsie AI Agent with PostgreSQL..."

# Create postgres user if it doesn't exist
if ! id "postgres" &>/dev/null; then
    useradd -r -s /bin/bash postgres
fi

# Create PostgreSQL data directory
mkdir -p /var/lib/postgresql/data
chown -R postgres:postgres /var/lib/postgresql

# Initialize PostgreSQL if not already done
if [ ! -f /var/lib/postgresql/data/PG_VERSION ]; then
    echo "📊 Initializing PostgreSQL database..."
    sudo -u postgres /usr/lib/postgresql/15/bin/initdb -D /var/lib/postgresql/data
fi

# Start PostgreSQL
echo "🔄 Starting PostgreSQL service..."
sudo -u postgres /usr/lib/postgresql/15/bin/pg_ctl -D /var/lib/postgresql/data -l /var/lib/postgresql/data/postgresql.log start

# Wait for PostgreSQL to be ready
echo "⏳ Waiting for PostgreSQL to be ready..."
until sudo -u postgres /usr/lib/postgresql/15/bin/pg_isready; do
    sleep 1
done

# Create database and user
echo "🔧 Setting up database and user..."
sudo -u postgres /usr/lib/postgresql/15/bin/createdb fleet_wiki 2>/dev/null || true
sudo -u postgres /usr/lib/postgresql/15/bin/createuser elsie 2>/dev/null || true
sudo -u postgres /usr/lib/postgresql/15/bin/psql -c "ALTER USER elsie PASSWORD 'elsie123';" 2>/dev/null || true
sudo -u postgres /usr/lib/postgresql/15/bin/psql -c "GRANT ALL PRIVILEGES ON DATABASE fleet_wiki TO elsie;" 2>/dev/null || true
sudo -u postgres /usr/lib/postgresql/15/bin/psql -d fleet_wiki -c "GRANT ALL ON SCHEMA public TO elsie;" 2>/dev/null || true
sudo -u postgres /usr/lib/postgresql/15/bin/psql -d fleet_wiki -c "GRANT CREATE ON SCHEMA public TO elsie;" 2>/dev/null || true

echo "✅ PostgreSQL setup complete!"

# Start the Python application
echo "🍺 Starting Elsie AI Agent..."
exec python main.py 