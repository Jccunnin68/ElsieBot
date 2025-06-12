# AI Agent - Python Component

This directory contains the Python-based AI agent for the Elsie project. It is a FastAPI application that serves as the "brain" of the bot, handling all complex logic, natural language processing, and state management.

## Responsibilities

- **API Endpoint**: Provides a `/process` endpoint to receive messages and context from the Discord bot.
- **Strategy Engine**: Determines the best response strategy for a given message (e.g., general chat, roleplay, information query).
- **Roleplay Management**:
    - Detects the start and end of roleplay sessions.
    - Tracks participants, turns, and conversation flow.
    - Manages a "listening mode" to avoid being intrusive in multi-character scenes.
- **DGM (Daedalus Game Master) Handling**:
    - Parses `[DGM]` commands for scene control.
    - Allows DGMs to start scenes, end scenes, and even control Elsie's actions directly.
    - Overrides channel restrictions for DGM posts.
- **State Management**: Maintains the state of roleplay sessions, including active participants, session start time, and more.
- **Response Generation**: Constructs prompts and coordinates with an AI model (like Google's Gemma) to generate intelligent, in-character responses.
- **Database Interaction**: Queries a knowledge base (the `elsiebrain` database) for information about lore, characters, and logs when needed.

## Architecture

The AI agent is built using a modular, handler-based architecture to separate concerns and make the system extensible.

- **`main.py`**: The main FastAPI application file. It defines the API endpoints (`/process`, `/health`), manages the application lifecycle (startup/shutdown), and handles incoming requests.

- **`handlers/`**: This directory contains the core logic of the AI agent, broken down into sub-modules:
    - **`ai_coordinator`**: The top-level coordinator that receives a request and directs it through the processing pipeline.
    - **`ai_logic`**: Contains the "inner monologue" of the bot.
        - `strategy_engine.py`: Determines the high-level response strategy.
        - `query_detection.py`: Uses regex and pattern matching to detect specific user intents (e.g., asking for a log, asking about a character).
        - `decision_extractor.py`: Decides if a response can be pre-generated (e.g., a simple acknowledgment) or if it requires a full AI model call.
    - **`ai_attention`**: Manages all aspects of roleplay.
        - `roleplay_detection.py`: Detects roleplay triggers and confidence scores.
        - `state_manager.py`: The `RoleplayStateManager` class that tracks the state of RP sessions.
        - `dgm_handler.py`: Parses and handles `[DGM]` posts.
        - `channel_restrictions.py`: Enforces which channels are appropriate for roleplay.
        - `response_logic.py`: Determines *when* Elsie should respond in a roleplay scene.
    - **`ai_wisdom`**: Handles the generation of context for the AI model.
        - `context_coordinator.py`: Gathers all necessary context for a response.
        - `database_contexts.py`: Retrieves and formats information from the database.
        - `roleplay_contexts.py`: Creates the specific prompts needed for in-character roleplay responses.

- **`content_retrieval_db.py`**: A dedicated module for all database query logic.

## How it Works

1.  The Discord bot sends a `POST` request to the `/process` endpoint with the message, conversation history, and channel context.
2.  The `coordinate_response` function in the `ai_coordinator` receives the request.
3.  The `strategy_engine` analyzes the message and its context to determine a response strategy (e.g., `roleplay_active`, `character_info`, `general`).
4.  **For Roleplay**:
    - `roleplay_detection` and `dgm_handler` check for RP triggers or DGM commands.
    - The `RoleplayStateManager` tracks the session.
    - `response_logic` decides if Elsie should respond, listen, or perform a subtle action.
5.  The `decision_extractor` determines if an expensive AI call is necessary. For many roleplay actions (like listening or serving a drink), a pre-generated response is used to save resources.
6.  If an AI response is needed, the `context_coordinator` gathers all relevant information (database results, roleplay context, etc.).
7.  This context is used to build a detailed prompt for the AI model.
8.  The AI model generates a response.
9.  The final response text is sent back to the Discord bot.

This architecture ensures that Elsie's responses are context-aware, intelligent, and efficient, using pre-generated responses when possible and falling back to a powerful AI model for complex interactions. 