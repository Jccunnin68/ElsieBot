#!/bin/bash

echo "🚀 Starting Elsie Development Environment"
echo "========================================"

# Start the database first
echo "🗄️ Starting database..."
docker-compose -f docker-compose.db.yml up -d

# Wait for database to be healthy
echo "⏳ Waiting for database to be ready..."
until docker-compose -f docker-compose.db.yml ps | grep "healthy"; do
    echo "   ⏳ Database starting up..."
    sleep 2
done
echo "✅ Database is ready!"

# Start the application services
echo "🤖 Starting application services..."
docker-compose up -d

echo ""
echo "✅ Development environment is ready!"
echo "📊 Services:"
echo "   • Database: http://localhost:5433"
echo "   • AI Agent: http://localhost:8000"
echo "   • Discord Bot: Running"
echo ""
echo "🔧 Management commands:"
echo "   • Stop apps only: docker-compose down"
echo "   • Stop database: docker-compose -f docker-compose.db.yml down"
echo "   • Stop everything: docker-compose down && docker-compose -f docker-compose.db.yml down"
echo "   • Rebuild apps: docker-compose down && docker-compose up --build -d" 