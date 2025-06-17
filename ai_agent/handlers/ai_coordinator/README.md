# AI Coordinator Package

This package handles the main coordination logic for AI responses. It contains the top-level orchestration components that manage the overall flow of a request, from initial routing to final AI response generation.

## Components

### `response_coordinator.py`
This is the main entry point for the entire AI agent. The `coordinate_response` function receives the initial user message and context, and it directs the request to the appropriate handlers. It's responsible for the highest level of application flow control.

### `ai_engine.py`
This module contains the `AIEngine`, which is responsible for the final, expensive AI generation step. It takes a fully-formed context prompt (built by one of the `wisdom` builders) and calls the Gemma API to get the AI's response. It also includes logic for summarizing oversized prompts to prevent token limit errors and some post-processing of the final text.

## Flow
1.  An external call (e.g., from the FastAPI `main.py`) invokes `coordinate_response`.
2.  `coordinate_response` passes the request to the `Response Router` in the `ai_logic` package to get a `ResponseDecision`.
3.  This decision determines whether a pre-generated response can be used or if an AI call is necessary.
4.  If AI generation is needed, the `AIEngine` is ultimately called with a complete prompt.
5.  The final response is returned up the chain. 