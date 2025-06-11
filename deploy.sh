#!/bin/bash

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${YELLOW}🚀 Starting Elsie Deployment${NC}"
echo "====================================="

# Check if .env file exists
if [ ! -f .env ]; then
    echo -e "${RED}❌ .env file not found!${NC}"
    echo "Please create a .env file with the following variables:"
    echo "DB_NAME=elsiebrain"
    echo "DB_USER=elsie"
    echo "DB_PASSWORD=your_password"
    echo "DISCORD_TOKEN=your_discord_token"
    echo "GEMMA_API_KEY=your_gemma_key"
    exit 1
fi

# Function to check if a port is in use
check_port() {
    if lsof -Pi :$1 -sTCP:LISTEN -t >/dev/null ; then
        return 0
    else
        return 1
    fi
}

# Check if ports are available
if check_port 5433; then
    echo -e "${RED}❌ Port 5433 is already in use!${NC}"
    echo "Please stop any existing PostgreSQL instances or change the port in docker-compose.db.yml"
    exit 1
fi

if check_port 8000; then
    echo -e "${RED}❌ Port 8000 is already in use!${NC}"
    echo "Please stop any existing services using port 8000 or change the port in docker-compose.yml"
    exit 1
fi

# Deploy database first
echo -e "${YELLOW}📦 Deploying database...${NC}"
docker-compose -f docker-compose.db.yml up -d

# Wait for database to be healthy
echo -e "${YELLOW}⏳ Waiting for database to be healthy...${NC}"
until docker-compose -f docker-compose.db.yml ps | grep "elsiebrain_postgres" | grep "healthy" > /dev/null; do
    echo "Waiting for database to be ready..."
    sleep 5
done

echo -e "${GREEN}✅ Database is healthy!${NC}"

# Copy the seed backup into the container
echo "📦 Copying seed_backup.sql into the database container..."
docker cp Elsie/db_populator/backups/seed_backup.sql elsiebrain_postgres:/tmp/seed_backup.sql

# Restore the database from the backup
echo "🔄 Restoring database from backup..."
docker exec -i elsiebrain_postgres psql -U elsie -d elsiebrain < /tmp/seed_backup.sql

# Remove the temporary file
echo "🧹 Cleaning up..."
docker exec -i elsiebrain_postgres rm /tmp/seed_backup.sql

echo "🎉 Database seeded from seed_backup.sql!"

# Deploy the rest of the services
echo -e "${YELLOW}📦 Deploying application services...${NC}"
docker-compose up -d

# Wait for AI agent to be healthy
echo -e "${YELLOW}⏳ Waiting for AI agent to be healthy...${NC}"
until docker-compose ps | grep "ai_agent" | grep "healthy" > /dev/null; do
    echo "Waiting for AI agent to be ready..."
    sleep 5
done

echo -e "${GREEN}✅ AI agent is healthy!${NC}"

# Check if Discord bot is running
echo -e "${YELLOW}⏳ Checking Discord bot status...${NC}"
if docker-compose ps | grep "discord_bot" | grep "Up" > /dev/null; then
    echo -e "${GREEN}✅ Discord bot is running!${NC}"
else
    echo -e "${RED}❌ Discord bot failed to start!${NC}"
    echo "Check the logs with: docker-compose logs discord_bot"
    exit 1
fi

echo -e "${GREEN}🎉 Deployment complete!${NC}"
echo "====================================="
echo -e "${YELLOW}Services:${NC}"
echo "- Database: localhost:5433"
echo "- AI Agent: localhost:8000"
echo "- Discord Bot: Running and connected to Discord"
echo
echo -e "${YELLOW}Useful commands:${NC}"
echo "- View logs: docker-compose logs -f"
echo "- Stop services: docker-compose down"
echo "- Restart services: docker-compose restart"
echo "- View database logs: docker-compose -f docker-compose.db.yml logs -f" 