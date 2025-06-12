# Discord Bot - Go Component

This directory contains the Go-based Discord bot component of the Elsie project. This application is responsible for all direct interactions with the Discord API.

## Responsibilities

- **Discord Gateway Connection**: Connects to the Discord Gateway and maintains a persistent WebSocket connection.
- **Event Handling**: Listens for and handles Discord events, primarily `messageCreate` for new messages and `ready` for startup confirmation.
- **Message Processing**:
    - Ignores messages from itself to prevent loops.
    - Detects when it is mentioned, receives a direct message (DM), or when a message is posted in a monitored channel (e.g., threads or channels with "rp" in the name).
    - Cleans up message content by removing mentions before sending it to the AI agent.
- **Command Handling**: Implements simple, hard-coded commands like `!elsie ping` and `!elsie help` for quick, local responses.
- **AI Agent Communication**: Forwards relevant messages to the AI Agent's `/process` endpoint for intelligent processing.
- **Response Handling**:
    - Receives the generated response from the AI agent.
    - Handles special responses like `NO_RESPONSE` to stay silent when appropriate.
    - Automatically splits messages longer than Discord's 2000-character limit into multiple, well-formatted messages.
- **Typing Indicator**: Sends a typing indicator to the channel to let users know Elsie is processing their message.

## Architecture

The bot is built using the `discordgo` library, a popular and powerful Go library for interacting with the Discord API.

- **`main.go`**: The entry point of the application. It handles:
    - Loading configuration from environment variables (`.env` file).
    - Initializing the Discord session.
    - Registering event handlers.
    - Opening and closing the connection to Discord.
- **`ready()` handler**: Fired when the bot successfully connects to Discord. It sets the bot's status and logs the connection details.
- **`messageCreate()` handler**: The core logic for message processing. It decides whether to respond to a message, cleans the content, handles simple commands, and communicates with the AI agent.

## Configuration

The bot is configured via a `.env` file in the `discord_bot` directory.

- `DISCORD_TOKEN`: **Required**. Your Discord bot token.
- `AI_AGENT_URL`: The URL of the running AI agent. Defaults to `http://localhost:8000` if not set.

### Example `.env` file:
```
DISCORD_TOKEN=your_discord_bot_token_here
AI_AGENT_URL=http://localhost:8000
```

## How it Works

1.  When a message is sent in a channel Elsie is in, the `messageCreate` event is fired.
2.  The handler first performs several checks to decide if it should process the message:
    - Is the author the bot itself? (Ignore)
    - Is it a Direct Message? (Process)
    - Is the bot mentioned directly (`@Elsie`)? (Process)
    - Is it in a channel that is being monitored (a thread or a channel with "rp" in its name)? (Process)
    - Is it a command (`!elsie ...`)? (Process)
    - Is it a DGM post (`[DGM]...`)? (Process)
3.  If the message should be processed, the content is cleaned of mentions.
4.  Simple commands like `ping` and `help` are handled directly by the bot.
5.  For all other messages, the bot sends a `POST` request to the AI agent's `/process` endpoint. The payload includes the message content and context (channel ID, user info, etc.).
6.  The bot waits for the AI agent's response.
7.  When the response is received, it is sent back to the Discord channel. If the response is longer than 2000 characters, it is automatically split into multiple messages.

This design keeps the Discord bot lightweight and focused on its primary responsibility: being a client for the Discord API. All the heavy lifting and intelligence is delegated to the AI agent. 