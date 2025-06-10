#!/bin/bash

echo "🧪 Testing Elsie DevContainer Setup 🧪"
echo "======================================"

# Test 1: Check if we're in the right directory
echo "📁 Testing workspace location..."
if [ -d "/workspaces/Elsie" ]; then
    echo "✅ Workspace directory found"
    cd /workspaces/Elsie
else
    echo "❌ Workspace directory not found"
    exit 1
fi

# Test 2: Check if .env file exists
echo "📄 Testing .env file..."
if [ -f ".env" ]; then
    echo "✅ .env file exists"
else
    echo "❌ .env file not found"
fi

# Test 3: Check Python environment
echo "🐍 Testing Python environment..."
cd ai_agent
if [ -d "venv" ]; then
    echo "✅ Python virtual environment found"
    source venv/bin/activate
    python --version
    pip list | grep -E "(fastapi|uvicorn)" && echo "✅ Required Python packages installed"
    deactivate
else
    echo "❌ Python virtual environment not found"
fi
cd ..

# Test 4: Check Go environment
echo "🐹 Testing Go environment..."
cd discord_bot
if go version; then
    echo "✅ Go is installed"
    if go mod verify; then
        echo "✅ Go modules are valid"
    else
        echo "❌ Go modules have issues"
    fi
else
    echo "❌ Go is not installed"
fi
cd ..

# Test 5: Check Docker
echo "🐳 Testing Docker..."
if docker --version; then
    echo "✅ Docker is available"
    if docker-compose --version; then
        echo "✅ Docker Compose is available"
    else
        echo "❌ Docker Compose is not available"
    fi
else
    echo "❌ Docker is not available"
fi

# Test 6: Check scripts
echo "📜 Testing helper scripts..."
if [ -d ".devcontainer/scripts" ]; then
    echo "✅ Scripts directory found"
    for script in .devcontainer/scripts/*.sh; do
        if [ -x "$script" ]; then
            echo "✅ $script is executable"
        else
            echo "❌ $script is not executable"
        fi
    done
else
    echo "❌ Scripts directory not found"
fi

# Test 7: Quick API test (if AI agent is running)
echo "🌐 Testing AI Agent (if running)..."
if curl -s http://localhost:8000/ > /dev/null; then
    echo "✅ AI Agent is responding"
    # Test the process endpoint
    response=$(curl -s -X POST http://localhost:8000/process \
        -H "Content-Type: application/json" \
        -d '{"content": "test", "context": {}}')
    if echo "$response" | grep -q "status"; then
        echo "✅ AI Agent API is working"
    else
        echo "⚠️  AI Agent API responded but format unexpected"
    fi
else
    echo "ℹ️  AI Agent is not running (start it to test API)"
fi

# Test 8: Test Discord Bot (if running in devcontainer)
echo "🤖 Testing Discord Bot container setup..."
if docker-compose -f .devcontainer/docker-compose.yml ps | grep -q "discord_bot.*Up"; then
    echo "✅ Discord Bot container is running"
else
    echo "ℹ️  Discord Bot container is not running"
    echo "   Start with: docker-compose -f .devcontainer/docker-compose.yml up -d"
fi

echo ""
echo "🎉 DevContainer Setup Test Complete!"
echo ""
echo "Next steps:"
echo "1. Edit .env file with your Discord Bot Token"
echo "2. Optionally add your OpenAI API Key to .env"
echo "3. Run: .devcontainer/scripts/start-all.sh"
echo "4. Or start services individually for development"
echo ""
echo "🍺 Ready to serve drinks across the galaxy! 🍺" 