# Elsie - The Holographic Bartender

Elsie is a sophisticated, containerized Discord bot designed for the 22nd Mobile Daedalus Fleet community. She functions as a holographic bartender and stellar cartographer, capable of accessing a comprehensive, self-updating fleet database to provide information on mission logs, ship specifications, personnel files, and more.

## Core Features

- **Advanced Roleplay Integration**: Elsie can detect and participate in roleplay, track characters, and understand scene context.
- **DGM (Daedalus Game Master) Controls**: Special commands for game masters to control scenes, characters, and even Elsie herself.
- **Dynamic Conversation Handling**: Elsie can engage in both general chat and in-character roleplay, adapting her responses to the context.
- **Database Integration**: She can access a local PostgreSQL database (`elsiebrain`) for information about mission logs, ship specifications, personnel files, and more.
- **Stateful Sessions**: Elsie remembers conversation history and roleplay state within a session, allowing for coherent and continuous interactions.
- **Extensible AI Engine**: The AI agent is built with a modular strategy engine that can be easily extended with new capabilities and response patterns.
- **Channel-Aware Monitoring**: The bot intelligently monitors specific channels (like threads and "rp" channels) to avoid being intrusive in general-purpose channels.

## System Architecture

The Elsie project is composed of three main services that work in tandem:

### 1. Discord Bot (`discord_bot`)

A Go-based application responsible for connecting to Discord, handling events, managing messages, and communicating with the AI agent. It is the frontline interface for all user interactions.

### 2. AI Agent (`ai_agent`)

A Python-based FastAPI application that houses the core logic for Elsie's intelligence, including natural language processing, roleplay state management, and response generation.

### 3. Database & Populator (`db_populator`)

This component is responsible for creating and maintaining the `elsiebrain` knowledge base.

-   **Elsiebrain Database**:
    -   **Engine**: PostgreSQL.
    -   **Key Tables**:
        -   `wiki_pages`: Stores the content, title, URL, and classified metadata for each wiki page.
        -   `page_metadata`: Tracks crawl status, content hashes, and timestamps for differential updates.
    -   **Full-Text Search**: Utilizes `tsvector` and `tsquery` for efficient and intelligent searching across page titles and content.

-   **Database Populator (`wiki_crawler.py`)**:
    -   A Python script that crawls a target wiki (or other data source) and populates the `elsiebrain` database.
    -   **Differential Updates**: Calculates a hash of page content to crawl only pages that have changed, saving time and resources.
    -   **Page Classification**: Automatically determines page types (`mission_log`, `ship_info`, `personnel`, etc.) based on title and content patterns.
    -   **Robust Error Handling**: Gracefully handles network issues or errors during crawling.

## Getting Started

You can run the Elsie project locally for development or deploy it as a containerized application.

### Prerequisites

- **Go**: For running the Discord bot natively.
- **Python**: For running the AI agent and DB populator natively.
- **PostgreSQL**: A running PostgreSQL server. For local development, this can be a native installation or a container running in Docker Desktop. The `docker-compose.yml` file includes a PostgreSQL service for the containerized setup.
- **Docker & Docker Compose**: For running the project with containers (recommended).
- **Discord Bot Token**: You will need a Discord bot token to run the bot.
- **Environment Variables**: A `.env` file is used for configuration.

### Running Locally (Native)

**Note**: For this method, you must have your own PostgreSQL server running and have created the `elsiebrain` database. The connection details should be configured in the `ai_agent/.env` file.

1.  **Clone the repository**:
    ```bash
    git clone <repository-url>
    cd Elsie
    ```
2.  **Populate the database**:
    - Navigate to the `db_populator` directory.
    - Configure it to point to your data source and database.
    - Run the crawler script to populate `elsiebrain`.

3.  **Set up and run the AI Agent**:
    - Navigate to the `ai_agent` directory.
    - Install Python dependencies: `pip install -r requirements.txt`
    - Set up your `.env` file with the necessary database credentials.
    - Run the agent: `uvicorn main:app --reload`

4.  **Set up and run the Discord Bot**:
    - Navigate to the `discord_bot` directory.
    - Set up your `.env` file with your `DISCORD_TOKEN` and the `AI_AGENT_URL`.
    - Run the bot: `go run main.go`

### Running with Docker (Recommended)

Using Docker and Docker Compose is the recommended method for running the project, as it ensures a consistent environment for all services. The provided `docker-compose.yml` file will automatically set up a PostgreSQL container for you.

## Building the Project

### Building with Docker

You can build the Docker image for each service individually.

-   **Build the AI Agent**:
    ```bash
    docker build -t elsie-ai-agent -f ai_agent/Dockerfile .
    ```

-   **Build the Discord Bot**:
    ```bash
    docker build -t elsie-discord-bot -f discord_bot/Dockerfile .
    ```

## Cloud Deployment

This repository contains templates and configuration files for deploying the Elsie project to major cloud providers. The architecture is designed to be cloud-native and scalable.

You can find the deployment templates in the following directories:
- `aws/`: CloudFormation and related scripts for deploying to Amazon Web Services.
- `azure/`: Bicep or ARM templates for deploying to Microsoft Azure.
- `gcp/`: Deployment Manager or Terraform scripts for deploying to Google Cloud Platform.

These templates will help you provision the necessary infrastructure (e.g., container orchestration services, databases, networking) to run Elsie in a production environment.

## Documentation

For more detailed information about each component, as well as guides for users and game masters, please refer to the following documentation:

- **[System Architecture](./docs/ARCHITECTURE.md)**: A detailed technical diagram and breakdown of the project's architecture.
- **[AI Agent README](./ai_agent/README.md)**: Detailed information about the AI agent's architecture, endpoints, and strategy engine.
- **[Discord Bot README](./discord_bot/README.md)**: Information about the Go-based Discord bot, its handlers, and configuration.
- **[Elsie Usage Guide](./docs/USAGE_GUIDE.md)**: A guide for regular users on how to interact with Elsie.
- **[DGM Controls Guide](./docs/DGM_GUIDE.md)**: A comprehensive guide for Daedalus Game Masters on how to control scenes and interact with Elsie's advanced features.

---

*This project is dedicated to creating immersive and engaging roleplaying experiences. We hope you enjoy interacting with Elsie!*
