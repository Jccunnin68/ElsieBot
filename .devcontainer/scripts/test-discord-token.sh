#!/bin/bash

echo "🔍 Testing Discord Token Validity"
echo "=================================="

# Source the .env file
if [ -f "/workspaces/Elsie/.env" ]; then
    source /workspaces/Elsie/.env
    echo "✅ Loaded .env file"
else
    echo "❌ .env file not found"
    exit 1
fi

# Check if Discord token is set
if [ -z "$DISCORD_TOKEN" ] || [ "$DISCORD_TOKEN" = "mock_discord_token" ] || [ "$DISCORD_TOKEN" = "your_actual_discord_token_here" ]; then
    echo "❌ Discord token not properly configured"
    echo "Please set a valid Discord bot token in .env file"
    exit 1
fi

echo "🔑 Testing Discord token (showing first 10 characters): ${DISCORD_TOKEN:0:10}..."

# Test Discord API connection
echo "🌐 Testing Discord API connection..."
response=$(curl -s -H "Authorization: Bot $DISCORD_TOKEN" \
               -H "Content-Type: application/json" \
               "https://discord.com/api/v10/gateway/bot")

if echo "$response" | grep -q "url"; then
    echo "✅ Discord token is valid!"
    echo "🤖 Bot information:"
    echo "$response" | jq -r '. | "Gateway URL: \(.url)\nSession start limit: \(.session_start_limit.remaining)/\(.session_start_limit.total)"' 2>/dev/null || echo "$response"
else
    echo "❌ Discord token authentication failed!"
    echo "Response from Discord API:"
    echo "$response"
    echo ""
    echo "Common issues:"
    echo "1. Token is invalid or expired"
    echo "2. Token is a user token (not bot token)"
    echo "3. Bot was deleted in Discord Developer Portal"
    echo ""
    echo "To fix:"
    echo "1. Go to https://discord.com/developers/applications"
    echo "2. Select your application"
    echo "3. Go to 'Bot' section"
    echo "4. Regenerate token if needed"
    echo "5. Update DISCORD_TOKEN in .env file"
fi 