# Elsie - AI-Powered Discord Bot

Elsie is a Discord bot that combines Python-based AI agent processing with Go-based Discord interactions. The system is containerized using Docker for easy deployment on AWS.

## Project Structure

```
Elsie/
├── .devcontainer/      # DevContainer configuration for VS Code
├── ai_agent/           # Python-based AI agent system
├── discord_bot/        # Go-based Discord bot implementation
├── aws/               # AWS deployment configurations
├── docs/              # Project documentation
└── .github/           # GitHub Actions workflows
```

## Setup Instructions

### 🚀 Quick Start (DevContainer - Recommended)

1. **Prerequisites:**
   - VS Code with Remote-Containers extension
   - Docker Desktop

2. **Open in DevContainer:**
   ```bash
   git clone [repository-url]
   cd Elsie
   code .
   ```
   - Press `F1` → "Dev Containers: Reopen in Container"
   - Wait for setup to complete

3. **Configure and Start:**
   ```bash
   # Edit .env with your Discord token
   nano .env
   
   # Start all services
   .devcontainer/scripts/start-all.sh
   ```

### 🛠️ Manual Setup

1. Prerequisites:
   - Python 3.9+
   - Go 1.21+
   - Docker
   - AWS Account (for deployment)

2. Development Setup:
   ```bash
   # Clone the repository
   git clone [repository-url]
   cd Elsie

   # Set up Python environment
   cd ai_agent
   python -m venv venv
   source venv/bin/activate  # On Windows: .\venv\Scripts\activate
   pip install -r requirements.txt

   # Set up Go environment
   cd ../discord_bot
   go mod download
   ```

3. Running Locally:
   ```bash
   # Start the AI agent
   cd ai_agent
   python main.py

   # Start the Discord bot
   cd ../discord_bot
   go run main.go
   ```

4. Docker Deployment:
   ```bash
   docker-compose -f docker-compose.local.yml up --build
   ```

## 🚀 Development

For the best development experience, use the DevContainer setup which provides:
- ✅ Complete Go and Python environments
- ✅ Hot reload for both services  
- ✅ Pre-configured VS Code workspace
- ✅ Docker-in-Docker support
- ✅ All development tools ready to go

See `.devcontainer/README.md` for detailed development instructions.

## 🌐 AWS Deployment

The project is configured for AWS free tier deployment using Docker containers. See `aws/` directory for CloudFormation templates and deployment configurations.

## License

MIT License 