# AI Attention Package

This package is responsible for managing the AI's "attention" during a conversation using a service-oriented architecture. It tracks conversational state, determines high-level strategy, and manages roleplay session context through specialized services.

## Service Container Integration

This package provides several services through the service container:
- **`AttentionEngine`**: LLM-powered roleplay strategy determination
- **`RoleplayStateManager`**: Roleplay session state management
- **`CharacterTrackingService`**: Character name extraction and validation
- **`RoleplayExitService`**: Exit condition detection with OOC support

## Core Components

### `attention_engine.py`
Contains the `AttentionEngine` service - a powerful, LLM-based "Roleplay Director" that analyzes full conversational context (including user messages, history, and emotional cues from the `EmotionEngine`) to decide on Elsie's optimal response *strategy*. It determines *if* and *how* Elsie should respond in a roleplay scene (e.g., with active dialogue, a subtle action, or supportive listening). It does not generate the response itself, but rather the strategic plan for the response.

**Service Usage:**
```python
from handlers.service_container import get_attention_engine
attention_engine = get_attention_engine()
strategy = attention_engine.determine_response_strategy(message, history, rp_state)
```

### `state_manager.py`
Contains the `RoleplayStateManager` service - a critical singleton that holds the state of an active roleplay session. It tracks:
- If roleplay is active (`is_roleplaying`).
- The channel the roleplay is happening in to enforce channel isolation.
- The participants in the scene.
- Timestamps for auto-idling out of a session after a period of inactivity.
- DGM (Daedalus Game Master) session status and context.

**Service Usage:**
```python
from handlers.service_container import get_roleplay_state
rp_state = get_roleplay_state()
rp_state.start_roleplay_session(turn, triggers, channel_context)
```

### `character_tracking_service.py`
The `CharacterTrackingService` provides comprehensive character name extraction and validation with enhanced functionality:
- **Character name normalization** with proper capitalization
- **Multi-language support** including Nordic and Icelandic characters
- **Advanced extraction** from emotes, brackets, and addressing patterns
- **Character statistics** and analysis
- **Configurable exclusion lists** for common words

**Service Usage:**
```python
from handlers.service_container import get_character_tracking_service
char_service = get_character_tracking_service()
characters = char_service.extract_character_names_from_emotes(message)
stats = char_service.get_character_statistics(message)
```

### `roleplay_exit_service.py`
The `RoleplayExitService` detects conditions that should end roleplay sessions:
- **Exit command detection** with configurable patterns
- **OOC (Out of Character) message detection** with content extraction
- **Technical query identification** that breaks immersion
- **Exit statistics** and reason tracking
- **Dynamic command management** for adding/removing exit patterns

**Service Usage:**
```python
from handlers.service_container import get_roleplay_exit_service
exit_service = get_roleplay_exit_service()
should_exit, reason = exit_service.detect_roleplay_exit_conditions(message)
```

### `dgm_handler.py`
This utility handles non-LLM parsing of `[DGM]` commands. It can detect scene-setting, scene-ending, and character control commands from a Game Master, allowing for external direction of the roleplay. Uses the `CharacterTrackingService` for character name validation.

### Other Components
- **`contextual_cues.py`**: Defines rich data structures for passing contextual information.
- **`roleplay_types.py`**: Contains shared constants and enums to avoid circular dependencies.
- **`channel_restrictions.py`**: Manages channel-based access control and restrictions.

## Architecture Benefits

- **🏗️ Service-Oriented**: Clean separation of concerns with focused service APIs
- **🔧 Enhanced Functionality**: Services provide more features than original standalone functions
- **⚡ Performance Optimized**: Singleton pattern with caching and lazy loading
- **🧪 Testable**: All services can be easily mocked for unit testing
- **🔒 Type Safe**: Full type hints throughout the service layer
- **🎯 Dependency Injection**: Services are injected as dependencies for clean architecture

## Migration from Legacy Functions

**Old Pattern (Deprecated):**
```python
# Legacy standalone functions (removed)
from handlers.ai_attention.character_tracking import normalize_character_name
from handlers.ai_attention.exit_conditions import detect_roleplay_exit_conditions
```

**New Pattern (Current):**
```python
# Modern service container pattern
from handlers.service_container import (
    get_character_tracking_service,
    get_roleplay_exit_service
)

char_service = get_character_tracking_service()
exit_service = get_roleplay_exit_service()
``` 