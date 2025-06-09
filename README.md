# Elsie - AI-Powered Discord Bot

Elsie is a Discord bot that combines Python-based AI agent processing with Go-based Discord interactions. The system is containerized using Docker for easy deployment on AWS.

## Project Structure

```
Elsie/
├── ai_agent/           # Python-based AI agent system
├── discord_bot/        # Go-based Discord bot implementation
├── docker/            # Docker configuration files
└── docs/             # Project documentation
```

## Setup Instructions

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
   docker-compose up --build
   ```

## AWS Deployment

The project is configured for AWS free tier deployment using Docker containers. See `docker/` directory for configuration details.

## License

MIT License 