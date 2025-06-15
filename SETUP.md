# Elsie Project Setup Guide

This guide provides comprehensive instructions for setting up, configuring, and running the Elsie project and its services.

## 1. Prerequisites

- **Docker & Docker Compose**: For running the containerized services.
- **Git**: For cloning the repository.
- **VS Code**: Recommended editor.
- **Remote - Containers Extension**: For the best development experience with VS Code.
- **Go**: For local development of the `discord_bot`.
- **Python**: For local development of the `ai_agent` and `db_populator`.

## 2. Environment Configuration

The entire project is configured using a single `.env` file in the root directory.

1.  **Create the `.env` file**:
    ```bash
    cp sample.env .env
    ```

2.  **Edit the `.env` file** and provide the following values:
    -   `DISCORD_TOKEN`: Your Discord bot token.
    -   `GEMMA_API_KEY`: Your API key for the Google Gemma service.
    -   `DB_PASSWORD`: A secure password for the PostgreSQL database.
    -   `DB_PORT`: The port for the database (default: 5432).
    -   `DB_NAME`: The name of the database to use (e.g., `elsie`)

## 3. Discord Bot Setup

To run the Discord bot, you need to create a Discord Application and get a bot token.

1.  **Go to the Discord Developer Portal**:
    -   [https://discord.com/developers/applications](https://discord.com/developers/applications)

2.  **Create a New Application**:
    -   Click "New Application".
    -   Give it a name (e.g., "Elsie") and click "Create".

3.  **Create a Bot User**:
    -   Navigate to the "Bot" section in the left sidebar.
    -   Click "Add Bot", then "Yes, do it!".

4.  **Get the Bot Token**:
    -   Under the bot's profile, click "Reset Token" (or "Copy Token" if available).
    -   Copy the token and paste it into the `DISCORD_TOKEN` field in your `.env` file.
    -   **Keep this token secret!**

5.  **Enable Privileged Gateway Intents**:
    -   In the "Bot" section, scroll down to "Privileged Gateway Intents".
    -   Enable the **Message Content Intent**. This is required for the bot to read messages.

6.  **Invite the Bot to Your Server**:
    -   Go to "OAuth2" -> "URL Generator".
    -   In "Scopes", select `bot`.
    -   In "Bot Permissions", select `Send Messages` and `Read Message History`.
    -   Copy the generated URL and open it in your browser to invite the bot to your desired server.

## 4. Running the Project

You can run the project using either the included Dev Container (recommended) or a manual local setup.

### Option A: Dev Container (Recommended)

This is the easiest way to get started.

1.  **Open the project in VS Code**.
2.  When prompted, click **"Reopen in Container"**.
3.  The dev container will build automatically, install all dependencies, and start the services.

### Option B: Local Docker Compose

If not using the dev container, you can run the services directly with Docker Compose.

1.  **Start the database first**:
    ```bash
    docker-compose -f docker-compose.db.yml up -d
    ```
    This will start the PostgreSQL database on port 5433 (to avoid conflicts with local Postgres).

2.  **Wait for the database to be healthy**, then start the application services:
    ```bash
    docker-compose up -d
    ```

3.  **View logs**:
    ```bash
    # Database logs
    docker-compose -f docker-compose.db.yml logs -f

    # Application logs
    docker-compose logs -f
    ```

### Option C: Production Deployment

For production deployment, follow these steps:

1.  **Deploy the database first**:
    ```bash
    docker-compose -f docker-compose.db.yml up -d
    ```
    This ensures the database is running and persistent before starting the applications.

2.  **Verify database health**:
    ```bash
    docker-compose -f docker-compose.db.yml ps
    ```
    Wait until the database shows as "healthy".

3.  **Deploy the applications**:
    ```bash
    docker-compose up -d
    ```

4.  **Monitor the deployment**:
    ```bash
    docker-compose logs -f
    ```

## 5. Usage and Testing

Once the bot is running and in your Discord server, you can interact with it.

-   **Say hello**: Type `!elsie hello` in a channel.
-   **View the menu**: Type `!elsie menu`.
-   **Ask a question**: Mention the bot and ask a question (e.g., `@Elsie tell me about the USS Stardancer`).
-   **Request a page link (OOC)**: Type `OOC link me the stardancer page`.

## 6. Troubleshooting

-   **Bot Not Responding**:
    -   Verify the `DISCORD_TOKEN` in `.env` is correct.
    -   Ensure the "Message Content Intent" is enabled in the Discord Developer Portal.
    -   Check that the bot has the correct permissions in your Discord server.
-   **AI Agent Errors**:
    -   Check the `GEMMA_API_KEY` in your `.env` file.
    -   View the `ai_agent` container logs for errors: `docker-compose logs -f ai_agent`.
    -   To test the DB connection from the agent container: `docker-compose exec ai_agent python -c "from handlers.ai_wisdom.content_retriever import check_elsiebrain_connection; check_elsiebrain_connection()"`
-   **Database Issues**:
    -   Ensure the database credentials in `.env` are correct.
    -   Check the `elsiebrain_db` container logs: `docker-compose logs -f elsiebrain_db`.
    -   To connect to the database manually: `docker-compose exec elsiebrain_db psql -U elsie -d elsiebrain`
-   **Wiki Crawler Issues**:
    -   Ensure required packages are installed for local development: `pip install fandom-py psycopg2-binary requests beautifulsoup4`
    -   Run a stats check to verify DB connection: `python db_populator/wiki_crawler.py --stats`

## 7. Populating the Database (Wiki Crawler)

The `db_populator` service contains the `wiki_crawler.py` script, which is responsible for keeping the `elsiebrain` database up-to-date with the Fandom wiki.

You can run the crawler manually to perform specific operations.

```bash
# Enter the db_populator container
docker-compose exec db_populator bash

# From within the container, run the crawler:

# Standard crawl (updates changed pages)
python wiki_crawler.py

# Comprehensive crawl (all 1400+ pages, very slow)
python wiki_crawler.py --comprehensive

# Force a full refresh of all pages
python wiki_crawler.py --force

# Show database statistics
python wiki_crawler.py --stats
```

## 8. Local Development (Without Docker)

For more granular control, you can run the services locally.

### Start the Database

You still need Docker to run the PostgreSQL database.

```bash
# Start just the database service
docker-compose up -d elsiebrain_db
```

### Run the AI Agent

```bash
cd ai_agent
python -m venv venv
source venv/bin/activate  # On Windows: .\\venv\\Scripts\\activate
pip install -r requirements.txt
python main.py
```

### Run the Discord Bot

```bash
cd discord_bot
go mod tidy
go run main.go
``` 