#!/bin/bash

echo "🍺 Setting up Elsie Development Environment 🍺"

# Navigate to workspace
cd /workspaces/Elsie

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo "Creating .env file..."
    cat > .env << EOF
# Elsie Development Environment
# OpenAI API Key (optional - uses mock responses if not provided)
OPENAI_API_KEY=mock_key_for_development

# Discord Bot Token (required for Discord functionality)
DISCORD_TOKEN=mock_discord_token

# Server Configuration
PORT=8000

# Development flags
ENVIRONMENT=development
DEBUG=true
EOF
    echo "✅ .env file created!"
fi

# Set up Python environment for AI Agent
echo "🐍 Setting up Python AI Agent..."
cd ai_agent
if [ ! -d "venv" ]; then
    python -m venv venv
fi
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
deactivate
cd ..

# Set up Go environment for Discord Bot
echo "🐹 Setting up Go Discord Bot..."
cd discord_bot
go mod download
go mod tidy
cd ..

# Install useful CLI tools
echo "🛠️ Installing development tools..."
go install github.com/air-verse/air@latest
pip install --user black isort flake8

# Make scripts executable
chmod +x .devcontainer/scripts/*.sh 2>/dev/null || true

# Create workspace scripts
mkdir -p .devcontainer/scripts

cat > .devcontainer/scripts/start-ai-agent.sh << 'EOF'
#!/bin/bash
echo "🤖 Starting Elsie AI Agent..."
cd /workspaces/Elsie/ai_agent
source venv/bin/activate
python main.py
EOF

cat > .devcontainer/scripts/start-discord-bot.sh << 'EOF'
#!/bin/bash
echo "🤖 Starting Discord Bot..."
cd /workspaces/Elsie/discord_bot
# Copy .env file from parent directory if it exists
if [ -f "../.env" ]; then
    cp ../.env .env
fi
go run main.go
EOF

cat > .devcontainer/scripts/start-all.sh << 'EOF'
#!/bin/bash
echo "🍺 Starting All Elsie Services 🍺"
cd /workspaces/Elsie
docker-compose -f .devcontainer/docker-compose.yml up --build
EOF

cat > .devcontainer/scripts/test-ai-agent.sh << 'EOF'
#!/bin/bash
echo "🧪 Testing AI Agent..."
curl -X POST http://localhost:8000/process \
  -H "Content-Type: application/json" \
  -d '{"content": "Hello Elsie!", "context": {}}'
EOF

chmod +x .devcontainer/scripts/*.sh

echo ""
echo "🎉 Elsie Development Environment Setup Complete!"
echo ""
echo "Available commands:"
echo "  🤖 .devcontainer/scripts/start-ai-agent.sh    - Start AI Agent locally"
echo "  🤖 .devcontainer/scripts/start-discord-bot.sh - Start Discord Bot locally"  
echo "  🐳 .devcontainer/scripts/start-all.sh         - Start all services with Docker"
echo "  🧪 .devcontainer/scripts/test-ai-agent.sh     - Test AI Agent API"
echo ""
echo "Docker services:"
echo "  🐳 docker-compose -f .devcontainer/docker-compose.yml up"
echo ""
echo "Manual setup:"
echo "  1. Add your Discord Bot Token to .env file"
echo "  2. Add your OpenAI API Key to .env file (optional)"
echo "  3. Run one of the start scripts above"
echo ""
echo "🍺 Ready to serve drinks across the galaxy! 🍺" 