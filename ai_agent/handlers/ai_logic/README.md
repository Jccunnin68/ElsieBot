# AI Logic Package

This package is the "central nervous system" of the agent's decision-making process for standard, non-roleplay queries. It handles the initial routing of all incoming messages and contains the components for parsing and understanding structured user requests.

## Core Components

### `response_router.py`
This is the first point of contact after the `ResponseCoordinator`. The `route_message_to_handler` function inspects the `RoleplayStateManager` and makes the primary decision: should this message be handled by the roleplay system or the structured query system?

### `structured_query_detector.py`
For non-roleplay messages, this component is key. It uses a series of regular expressions and pattern matching to analyze the user's message and classify it into a specific query type (e.g., an explicit search for a term in a category, a request for logs, or a general "tell me about" query). This classification is crucial for fetching the correct data.

### `structured_query_handler.py`
This module orchestrates the entire flow for a standard query. It uses the `StructuredQueryDetector` to classify the message, the `StructuredContentRetriever` to get the data, and the `WisdomEngine` to build the final context for the AI.

### `logic_engine.py`
This module contains the `LogicEngine`, a utility LLM used for fine-grained reasoning tasks. Its primary role is to assist the `StructuredContentRetriever`. When the user asks a general question (e.g., "tell me about the Dawnbreaker war"), the `LogicEngine` determines the most appropriate database category to search (e.g., "Historical Events"), making the subsequent database query much more efficient and accurate. 