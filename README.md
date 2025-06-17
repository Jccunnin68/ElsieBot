# Elsie AI Agent

Elsie is a sophisticated, multi-purpose AI agent designed for advanced, context-aware interaction. This project showcases a modular, engine-driven architecture for building powerful conversational AI.

Elsie's core capabilities include:
-   **Structured Q&A**: Answering questions by retrieving and synthesizing information from a knowledge base.
-   **Immersive Roleplay**: Engaging in multi-participant roleplay scenarios with character awareness, emotional intelligence, and scene management.
-   **Agentic System**: Utilizes multiple LLM-powered "engines" for specialized tasks like emotional analysis, strategic planning, and logical reasoning.

The project is built with Python, FastAPI, and Google's Gemma family of models.

## Architecture
The agent employs a decoupled, engine-driven architecture. For a detailed explanation and diagrams, please see the [**Engine-Driven Architecture documentation**](./docs/ARCHITECTURE.md).

## Getting Started

### Prerequisites
-   Docker and Docker Compose
-   Python 3.9+ (for any local script execution)
-   A Google AI API Key with access to the Gemma models.

### Configuration

1.  **Copy the sample environment file:**
    ```bash
    cp sample.env .env
    ```
2.  **Edit the `.env` file:**
    Open the newly created `.env` file and add your Google AI API Key:
    ```env
    # .env
    GEMMA_API_KEY="YOUR_API_KEY_HERE"
    ```

### Running the Agent

The entire system (AI agent, database, and Discord bot) is orchestrated using Docker Compose.

1.  **Build and start the services:**
    ```bash
    docker-compose up --build
    ```
    This command will build the images for the AI agent, the Discord bot, and the database, then start them in detached mode.

2.  **View logs:**
    To see the logs from all running services:
    ```bash
    docker-compose logs -f
    ```
    To view the logs for a specific service (e.g., the AI agent):
    ```bash
    docker-compose logs -f ai-agent
    ```

3.  **Stopping the services:**
    ```bash
    docker-compose down
    ```

### Populating the Database

The agent relies on a database for its knowledge base. A `db_populator` service is included to import content.

-   **Initial Import**: On first startup, the `db-populator` service will run `fresh_import.py`, processing all text files in the `db_populator/content_files` directory and populating the database.
-   **Incremental Imports**: On subsequent startups, it will run `incremental_import.py` to only add new or modified files.

To add new knowledge, simply place `.txt` files into the `db_populator/content_files` directory and restart the services.

## How It Works

The agent has two primary modes of operation, which are selected automatically by the `ResponseRouter`.

### 1. Structured Query Mode
This mode is for standard, out-of-character (OOC) questions and commands.
-   The `StructuredQueryDetector` classifies the user's intent.
-   The `StructuredContentRetriever` fetches relevant data from the database, using the `LogicEngine` to disambiguate general queries.
-   The `WisdomEngine` assembles a detailed prompt using the `PromptLibrary`.
-   The `AIEngine` generates a synthesized, informative response.

**Example Usage:**
-   `search for "Stardancer" in "Ships"`
-   `logs for Tavi latest`
-   `character Zarina Dryellia`
-   `tell me about the LMC`

### 2. Roleplay Mode
This mode is activated when the `RoleplayStateManager` detects an ongoing roleplay session, typically initiated by a `[DGM]` (Daedalus Game Master) command.
-   The `AttentionEngine` acts as a "Roleplay Director," analyzing the scene and deciding on a high-level strategy for Elsie's response.
-   It consults the `EmotionEngine` to understand the emotional context.
-   The `RoleplayContextBuilder` creates a rich, detailed prompt based on the engine's strategy, including character relationships, scene details, and conversational history.
-   The `AIEngine` generates an in-character response.

**Example Usage:**
-   `[DGM] The doors to Ten Forward slide open, revealing Captain Blaine.` (Starts a session)
-   `*Tavi walks up to the bar.* "A synthale, please."` (Interacting within a session)
-   `[DGM][END]` (Ends a session) 

**Purpose and methodlogies:**
- The original purpose of elsie was to test the AI driven coding paradigm. First elsie code was generated with aroudn 200 one line behavioru prompts into cursor's agent running anthropics claude 4.0 I specifically limited myself to take what it gave me test it and then correct rather than role back. This was done to test the "no experience" coding capabilities of the system. The budget fo rthis project was 500 calls. Broken down into a budget of 200 for initial generation, 150 for first stage refactor to add a complicated new feature (roleplaying feature) and finally the remaining prompts would be for a full conversion to an agentic model.
- At each phase of the project I "upgraded" my thinking. Allwoing myself to do more. In stage 2 I operated hand and hand with the agent now running gemini 2.5 pro as we refactored the the code base into a single LLM point but heavily heuristic approached system for handlign various interactions and database queries. As the systme started out monolithic spread only over a few files with thousands of lines of code. The heuristic approach eventually entered a state where code maintainablilty for adding new features and refining feature sets to work within the limits of a single LLM lead to fail over. This combiend with datasource issues due to the MediaWiki's esoteric data imports lead to issues. Eventually the project needed to enter phase three.
- Phase three was a comprehensive design overhaul to a fully agentic system migrating logic from a heuristic engine powering prompts to a neural net powering the final response. Durign this process complex prompts that provided archetictual goals wer eprovided to gemini 2.5 to create the plan while the work was offloaded at times to background agents. Each module was refactored from tgeh heuristic rules to its own seperated concerns until eventually the archetecture was clean.

**Lessons**
- When it coems to ai Measure once Measure twice, measure three times, have an ai measure, correct it, then Prompt. The finaly agentic AI system was obtained with 10 prompts and 1 human edit. And had I perfomred this level of pre planning and development of the prompts that would go into the system It is every likely that this could have been built accordingly.
- Vague result in vague result out, always prompt your AI to keep the existing state unless absolutely necssary this will preserve variable names module and class structures and imports cutting down on rabbit hole debugging. Focus the AI on the problem you need solved within guardrails. And watch it shine.
- Branch early branch often and don't be afraid to abandon a branch all together and start over. Desing is far more important than the code when you can generate thousands of lines with a button push.


