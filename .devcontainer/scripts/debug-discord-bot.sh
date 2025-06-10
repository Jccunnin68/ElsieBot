#!/bin/bash

echo "🔍 Discord Bot Debug Script"
echo "==========================="

# Check if .env file exists
if [ -f "/workspaces/Elsie/.env" ]; then
    echo "✅ .env file found in workspace root"
else
    echo "❌ .env file not found in workspace root"
    exit 1
fi

# Check environment variables
echo ""
echo "📋 Environment Variables:"
echo "DISCORD_TOKEN: ${DISCORD_TOKEN:0:10}..." # Show only first 10 chars for security
echo "AI_AGENT_URL: ${AI_AGENT_URL}"

# Test AI Agent connectivity
echo ""
echo "🌐 Testing AI Agent connectivity..."
if curl -s http://ai_agent:8000/ > /dev/null; then
    echo "✅ AI Agent is reachable"
else
    echo "❌ AI Agent is not reachable"
fi

# Check if Discord token is set
if [ -z "$DISCORD_TOKEN" ] || [ "$DISCORD_TOKEN" = "mock_discord_token" ] || [ "$DISCORD_TOKEN" = "your_actual_discord_token_here" ]; then
    echo ""
    echo "❌ Discord token is not properly set!"
    echo "Please update DISCORD_TOKEN in .env file with a valid Discord bot token"
    echo ""
    echo "To get a Discord bot token:"
    echo "1. Go to https://discord.com/developers/applications"
    echo "2. Create a new application or select existing one"
    echo "3. Go to 'Bot' section"
    echo "4. Copy the token"
    echo "5. Update DISCORD_TOKEN in .env file"
    exit 1
else
    echo ""
    echo "✅ Discord token appears to be set"
fi

echo ""
echo "🚀 Attempting to start Discord bot..."
cd /workspaces/Elsie/discord_bot
go run main.go 