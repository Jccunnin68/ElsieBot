# AI Attention Package

This package is responsible for managing the AI's "attention" during a conversation. It tracks the conversational state, determines high-level strategy, and manages roleplay session context.

## Core Components

### `attention_engine.py`
This is the "Roleplay Director." It features the `AttentionEngine`, a powerful, LLM-based component that analyzes the full conversational context (including user messages, history, and emotional cues from the `EmotionEngine`) to decide on Elsie's optimal response *strategy*. It determines *if* and *how* Elsie should respond in a roleplay scene (e.g., with active dialogue, a subtle action, or supportive listening). It does not generate the response itself, but rather the strategic plan for the response.

### `state_manager.py`
This module contains the `RoleplayStateManager`, a critical singleton that holds the state of an active roleplay session. It tracks:
- If roleplay is active (`is_roleplaying`).
- The channel the roleplay is happening in to enforce channel isolation.
- The participants in the scene.
- Timestamps for auto-idling out of a session after a period of inactivity.
- DGM (Daedalus Game Master) session status and context.

### `dgm_handler.py`
This utility handles non-LLM parsing of `[DGM]` commands. It can detect scene-setting, scene-ending, and character control commands from a Game Master, allowing for external direction of the roleplay.

### Other Utilities
- **`character_tracking.py`**: Extracts character names from messages.
- **`contextual_cues.py`**: Defines the rich data structures for passing contextual information.
- **`roleplay_types.py`**: Contains shared constants and enums to avoid circular dependencies.
- **`exit_conditions.py`**: Detects user commands or OOC messages that should terminate a roleplay session. 