# AI Emotion Package

This package is responsible for all emotional processing and for generating simple, "mock" responses that do not require the full structured query pipeline.

## Core Components

### `emotion_engine.py`
This module contains the `EmotionEngine`, a dedicated LLM-powered component for all nuanced emotional analysis. It takes a user's message and returns a structured analysis of the perceived emotions, intensity, and underlying emotional needs. This analysis is a key input for the `AttentionEngine` when deciding on a roleplay strategy. This engine replaces the previous heuristic-based emotion detection.

### Mock & Canned Responses
This package also houses a collection of modules for providing simple, pre-determined, or lightly-generated responses for common interactions. This allows the agent to feel responsive and natural for simple cases without invoking the expensive and powerful core engines.
- **`greetings.py`**: Handles simple "hello", "goodbye", and "how are you" interactions.
- **`drink_menu.py`**: Provides responses related to drink orders and the bar menu.
- **`mock_responses.py`**: A general handler for other simple, canned responses.
- **`poetic_responses.py`**: Contains the "poetic circuit," a fun feature that allows Elsie to give an esoteric, poetic, or philosophical response to certain simple inputs, adding variety to her character. 