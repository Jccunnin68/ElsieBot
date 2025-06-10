# 🤖 Discord Bot Local Development Setup

> **💡 New:** For the best development experience, use the **DevContainer setup** in the root `.devcontainer/` directory. It provides automated setup with hot reload for both Discord bot and AI agent. See `.devcontainer/README.md` for details.

## 📋 Prerequisites

1. **VS Code with Remote-Containers extension** (recommended)
2. **Docker Desktop**
3. **Discord Bot Token** (from Discord Developer Portal)

## 🚀 Quick Start

### 1. DevContainer Setup (Recommended)
```bash
# Open project in VS Code
code .

# Press F1 → "Dev Containers: Reopen in Container"
# Wait for automatic setup to complete
```

The devcontainer will automatically:
- Set up Go and Python environments
- Create `.env` file template
- Install all dependencies  
- Configure hot reload for development

### 1b. Manual Setup (Alternative)
If not using devcontainer:
```bash
# Ensure Go 1.21+ is installed
go version

# Install dependencies
go mod download
```

### 2. Get Discord Bot Token

1. **Go to Discord Developer Portal**
   - https://discord.com/developers/applications

2. **Create New Application**
   - Click "New Application"
   - Name it "Elsie" (or whatever you prefer)
   - Click "Create"

3. **Create Bot**
   - Go to "Bot" section in left sidebar
   - Click "Add Bot" (if not already created)
   - Click "Yes, do it!"

4. **Get Token**
   - Under "Token" section
   - Click "Copy" to copy the bot token
   - **Keep this secret!**

5. **Set Bot Permissions**
   - Go to "Bot" section
   - Under "Privileged Gateway Intents":
     - ✅ Enable "Message Content Intent"
   - Under "Bot Permissions":
     - ✅ Send Messages
     - ✅ Read Message History
     - ✅ Use Slash Commands
     - ✅ Add Reactions

### 3. Configure Environment

Edit the `.env` file and replace the token:
```env
DISCORD_TOKEN=YOUR_ACTUAL_BOT_TOKEN_HERE
AI_AGENT_URL=http://localhost:8000
```

### 4. Invite Bot to Server

1. **Generate Invite Link**
   - Go to "OAuth2" → "URL Generator"
   - Scopes: ✅ `bot`
   - Bot Permissions: ✅ Send Messages, Read Message History
   - Copy the generated URL

2. **Invite to Server**
   - Open the URL in browser
   - Select your Discord server
   - Click "Authorize"

### 5. Start Bot

**With DevContainer:**
```bash
# Start all services with hot reload
.devcontainer/scripts/start-all.sh

# Or start just the Discord bot
.devcontainer/scripts/start-discord-bot.sh
```

**Manual Setup:**
```bash
go run main.go
```

## 🍺 Testing Elsie

Once the bot is running and in your Discord server:

### Commands to Try:
- `!elsie hello` - Greet the holographic bartender
- `!elsie menu` - View the galactic drinks menu
- `!elsie help` - Show available commands
- `!elsie ping` - Test bot connectivity
- `@Elsie I'll have a Romulan Ale` - Order a drink by mentioning

### Example Conversation:
```
You: !elsie hello
Elsie: Welcome to my holographic establishment! I'm Elsie, your friendly neighborhood holographic bartender. What can I mix up for you today?

You: !elsie menu
Elsie: *holographic display materializes showing the menu*
🍺 ELSIE'S GALACTIC BAR MENU 🍺
[Full menu displays...]

You: !elsie I'll have a Blood Wine
Elsie: Klingon Blood Wine! *pounds fist on bar* A warrior's drink! May it bring you honor and victory in battle. Qapla'!
```

## 🔧 Troubleshooting

### Bot Not Responding
1. Check token in `.env` file
2. Ensure bot has "Message Content Intent" enabled
3. Check bot permissions in Discord server
4. Verify AI Agent is running: `curl http://localhost:8000/`

### Authentication Failed
- Double-check Discord token in `.env`
- Regenerate token in Discord Developer Portal if needed

### AI Agent Connection Error
**With DevContainer:**
- Check if services are running: `docker-compose -f .devcontainer/docker-compose.yml ps`
- View logs: `docker-compose -f .devcontainer/docker-compose.yml logs ai_agent`

**Manual Setup:**
- Start Docker containers: `docker-compose -f docker-compose.local.yml up`
- Check logs: `docker-compose -f docker-compose.local.yml logs ai_agent`

### Logs for Debugging
**With DevContainer:**
```bash
# View all service logs
docker-compose -f .devcontainer/docker-compose.yml logs -f

# View specific service logs
docker-compose -f .devcontainer/docker-compose.yml logs -f discord_bot
docker-compose -f .devcontainer/docker-compose.yml logs -f ai_agent
```

**Manual Setup:**
```bash
# View Discord bot logs
go run main.go

# View AI Agent logs  
docker-compose -f docker-compose.local.yml logs -f ai_agent
```

## 🌐 Architecture

```
┌─────────────────┐    HTTP POST     ┌─────────────────┐
│   Discord Bot   │ ──────────────── │   AI Agent      │
│   (Local Go)    │                  │   (Container)   │
│                 │ ←──────────────── │   Port: 8000    │
└─────────────────┘    JSON Response └─────────────────┘
         ↕                                     ↕
┌─────────────────┐                  ┌─────────────────┐
│   Discord API   │                  │ Holographic     │
│   (WebSocket)   │                  │ Bartender AI    │
└─────────────────┘                  └─────────────────┘
```

## 📝 Development Tips

1. **Hot Reload**: Restart `go run main.go` after code changes
2. **Debug Mode**: Add logging to see message processing
3. **Test Commands**: Use a private Discord server for testing
4. **AI Responses**: Responses come from containerized AI agent
5. **Session Management**: Each Discord channel has its own conversation session

Ready to serve drinks across the galaxy! 🍺✨ 