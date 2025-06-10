# 🍺 Elsie Discord Bot - DevContainer Setup

This devcontainer setup provides a complete development environment for Elsie, the holographic bartender Discord bot, including both the Python AI Agent and Go Discord Bot.

## 🚀 Quick Start

### 1. Open in DevContainer

1. **Install Prerequisites:**
   - VS Code with Remote-Containers extension
   - Docker Desktop

2. **Open Project:**
   ```bash
   # Clone the repository
   git clone <repository-url>
   cd Elsie
   
   # Open in VS Code
   code .
   ```

3. **Start DevContainer:**
   - Press `F1` → "Dev Containers: Reopen in Container"
   - Or click "Reopen in Container" when prompted

### 2. Configure Environment

After the container starts, edit `.env` file with your tokens:

```env
# Add your actual Discord Bot Token
DISCORD_TOKEN=your_discord_bot_token_here

# Add your OpenAI API Key (optional)
OPENAI_API_KEY=your_openai_api_key_here
```

## 🛠️ Development Workflows

### Option 1: Docker Services (Recommended)
Start all services with hot reload:
```bash
.devcontainer/scripts/start-all.sh
```

This starts:
- 🤖 AI Agent (Python) on port 8000
- 🤖 Discord Bot (Go) with hot reload and proper .env file mounting
- 🌐 All services in Docker network

**Note**: The `.env` file is automatically mounted from the root directory to both services.

### Option 2: Manual Development
Start services individually for debugging:

```bash
# Terminal 1: Start AI Agent
.devcontainer/scripts/start-ai-agent.sh

# Terminal 2: Start Discord Bot  
.devcontainer/scripts/start-discord-bot.sh
```

### Option 3: Native Development
Run directly in the devcontainer:

```bash
# AI Agent
cd ai_agent
source venv/bin/activate
python main.py

# Discord Bot (new terminal)
cd discord_bot
go run main.go
```

## 🧪 Testing

### Test AI Agent API
```bash
.devcontainer/scripts/test-ai-agent.sh
```

### Test Discord Bot
1. Invite your bot to a Discord server
2. Use commands like:
   - `!elsie hello`
   - `!elsie menu` 
   - `@Elsie I'll have a Romulan Ale`

## 🐳 Services Architecture

```
┌─────────────────┐    ┌─────────────────┐
│   DevContainer  │    │   AI Agent      │
│   (VS Code)     │    │   (Python:3.9)  │
│   Go + Python   │    │   Port: 8000    │
└─────────────────┘    └─────────────────┘
         │                       │
         └───────────────────────┼─── elsie_dev_network
                                 │
                         ┌───────▼──────┐
                         │ Discord Bot  │
                         │ (Go 1.21)    │
                         │ Hot Reload   │
                         └──────────────┘
```

## 📂 File Structure

```
.devcontainer/
├── devcontainer.json      # DevContainer configuration
├── docker-compose.yml     # Development services
├── setup.sh              # Post-create setup script
├── scripts/              # Helper scripts
│   ├── start-ai-agent.sh
│   ├── start-discord-bot.sh
│   ├── start-all.sh
│   └── test-ai-agent.sh
└── README.md             # This file

../discord_bot/
├── Dockerfile.dev        # Development Docker image
├── .air.toml            # Hot reload configuration
└── ...

../ai_agent/
├── Dockerfile           # Production-ready image
└── ...
```

## 🔧 Development Features

### Included Tools
- **Go 1.21** with go-lint and debugging support
- **Python 3.9** with AI/ML development tools
- **Docker-in-Docker** for container management
- **Air** for Go hot reloading
- **Git** with full history
- **curl** for API testing

### VS Code Extensions
- Go language support
- Python with linting and formatting
- Docker management
- YAML/JSON support
- GitHub Copilot (if enabled)

### Port Forwarding
- **8000**: Elsie AI Agent API
- **8080**: Discord Bot debug/admin (optional)
- **3000**: Future web interface

## 🎯 Common Tasks

### View Logs
```bash
# All services
docker-compose -f .devcontainer/docker-compose.yml logs -f

# Specific service
docker-compose -f .devcontainer/docker-compose.yml logs -f ai_agent
docker-compose -f .devcontainer/docker-compose.yml logs -f discord_bot
```

### Rebuild Services
```bash
docker-compose -f .devcontainer/docker-compose.yml up --build
```

### Stop Services
```bash
docker-compose -f .devcontainer/docker-compose.yml down
```

### Debug Go Code
1. Set breakpoints in VS Code
2. Press `F5` to start debugging
3. The debugger will attach to the running Go process

### Python Development
1. AI Agent code is in `/workspaces/Elsie/ai_agent/`
2. Virtual environment is automatically activated
3. Use VS Code's integrated terminal for Python REPL

## 🔍 Troubleshooting

### Discord Bot Not Starting
1. **Check Discord token in `.env`** - Make sure it's a valid bot token (not user token)
2. **Ensure AI Agent is running first** - Discord bot depends on AI Agent
3. **Check logs**: `docker-compose -f .devcontainer/docker-compose.yml logs discord_bot`
4. **Run debug script**: `.devcontainer/scripts/debug-discord-bot.sh`
5. **Authentication failed (4004)**:
   - Token may be invalid/expired
   - Bot may not be invited to any servers
   - Regenerate token in Discord Developer Portal if needed

### AI Agent Connection Issues
1. Verify port 8000 is not in use
2. Check Python virtual environment
3. Test manually: `curl http://localhost:8000/`

### Hot Reload Not Working
1. Ensure files are being watched: `docker-compose logs discord_bot`
2. Check Air configuration in `.air.toml`
3. Restart container if needed

### Permission Issues
```bash
# Fix permissions on scripts
chmod +x .devcontainer/scripts/*.sh
```

## 🚀 Production Deployment

When ready to deploy:

1. **Build Production Images:**
   ```bash
   docker-compose -f docker-compose.local.yml up --build
   ```

2. **Deploy to AWS:**
   ```bash
   # See main docker-compose.yml and AWS documentation
   ```

3. **Configure Secrets:**
   - Add real Discord token
   - Add real OpenAI API key
   - Configure environment variables

---

🍺 **Happy Coding!** Elsie is ready to serve drinks across the galaxy! 🍺 