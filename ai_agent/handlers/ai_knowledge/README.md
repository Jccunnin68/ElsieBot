# AI Knowledge Package

This package is responsible for all data persistence and retrieval. It acts as the agent's long-term memory, abstracting away the specifics of the database from the rest of the application.

## Core Components

### `database_controller.py`
This is the sole gateway to the database. The `DatabaseController` class provides methods for searching, retrieving, and managing data records. All other modules in the application that need to access the database must go through this controller. This centralization ensures that data access patterns are consistent and easy to manage.

### `knowledge_engine.py`
This module contains the `KnowledgeEngine`, an LLM-powered component responsible for post-processing large or complex sets of data retrieved from the database. For example, if a query returns a large number of log entries, the `KnowledgeEngine` can be used to summarize them or extract the most salient points before the information is passed to the final prompt-building stage.

## Flow
1. A handler (typically the `StructuredContentRetriever`) needs information from the database.
2. It gets the singleton instance of the `DatabaseController` via `get_db_controller()`.
3. It calls a search method on the controller (e.g., `search(query=...)`).
4. The controller executes the query against the database and returns the results.
5. If the results are too large or complex to be used in a prompt directly, they can be passed to the `KnowledgeEngine` for summarization or analysis. 