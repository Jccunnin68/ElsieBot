# AI Wisdom Package

This package is responsible for generating comprehensive context and coordinating content retrieval using a service-oriented architecture. It acts as the bridge between raw data/strategy and the final prompt, ensuring the LLM has all the information it needs through specialized services.

## Service Container Integration

This package provides several services through the service container:
- **`WisdomEngine`**: Primary context building for standard and database queries
- **`StructuredContentRetriever`**: Unified data retrieval and processing
- **`PromptLibrary`**: Centralized prompt generation with multiple specialized builders
- **`RoleplayContextBuilder`**: Specialized roleplay context generation
- **`ContextCoordinationService`**: Strategy-based context routing

## Core Components

### `context_coordination_service.py`
The `ContextCoordinationService` acts as a smart router for context generation. Based on the `approach` defined in the strategy (e.g., `roleplay_active` vs. `comprehensive`), it directs the request to the appropriate context builder with lazy loading to avoid circular imports.

**Service Usage:**
```python
from handlers.service_container import get_context_coordination_service
context_service = get_context_coordination_service()
context = context_service.get_context_for_strategy(strategy, user_message)
```

**Enhanced Features:**
- **Strategy validation** with available strategy enumeration
- **Lazy loading** of context builders to prevent circular dependencies
- **Context builder mapping** for different approaches
- **Error handling** with graceful fallbacks

### `wisdom_engine.py`
The `WisdomEngine` service is the primary context builder for all standard (OOC) and database queries. It receives structured query results and strategy, then uses the `PromptLibrary` to assemble precise and detailed prompts for the `AIEngine`.

**Service Usage:**
```python
from handlers.service_container import get_wisdom_engine
wisdom_engine = get_wisdom_engine()
context = wisdom_engine.build_context(strategy, user_message, history)
```

### `roleplay_context_builder.py`
The `RoleplayContextBuilder` service specializes in immersive roleplay scenarios. It takes the strategy generated by the `AttentionEngine` and weaves together all necessary context:
- Character relationships and history
- Current scene and setting (including DGM context)
- Specific emotional tone and style required
- Conversation history
- Relevant database knowledge

**Service Usage:**
```python
# Through service container
roleplay_builder = RoleplayContextBuilder()
context = roleplay_builder.build_context(user_message, history, character_context)
```

### `structured_content_retriever.py`
The `StructuredContentRetriever` service is the unified data retrieval module. It orchestrates content retrieval from the database with lazy dependency injection and comprehensive error handling.

**Service Usage:**
```python
from handlers.service_container import get_content_retriever
content_retriever = get_content_retriever()
result = content_retriever.retrieve_content(query, context_type)
```

**Enhanced Features:**
- **Lazy dependency injection** for database and knowledge engine services
- **Comprehensive error handling** with graceful degradation
- **Content type routing** for different query types
- **Performance optimization** with caching and connection pooling

### `prompt_builder.py`
The `PromptLibrary` service provides a centralized collection of prompt-generation functions for standard queries. It separates prompt *wording* from orchestration logic, creating a cleaner, more modular architecture.

**Service Usage:**
```python
# Direct class usage or through context builders
prompt_library = PromptLibrary()
prompt = prompt_library.build_comprehensive_prompt(query_result, strategy)
```

**Available Prompt Builders:**
- **`build_comprehensive_prompt()`**: For synthesizing comprehensive information
- **`build_logs_prompt()`**: For narrative story generation from logs
- **`build_character_prompt()`**: For character-specific information
- **`build_simple_chat_prompt()`**: For basic conversational responses
- **`build_ship_info_prompt()`**: For Star Trek ship and fleet information

## Architecture Benefits

- **🏗️ Service-Oriented**: Clean separation of concerns with focused service APIs
- **🔧 Enhanced Functionality**: Services provide more features than original functions
- **⚡ Performance Optimized**: Lazy loading, caching, and connection pooling
- **🧪 Testable**: All services can be easily mocked for unit testing
- **🔒 Type Safe**: Full type hints throughout the service layer
- **🎯 Dependency Injection**: Services are injected as dependencies for clean architecture
- **🔄 Circular Import Prevention**: Lazy loading prevents circular dependency issues

## Migration from Legacy Functions

**Old Pattern (Deprecated):**
```python
# Legacy standalone function (removed)
from handlers.ai_wisdom.context_coordinator import get_context_for_strategy
```

**New Pattern (Current):**
```python
# Modern service container pattern
from handlers.service_container import get_context_coordination_service

context_service = get_context_coordination_service()
context = context_service.get_context_for_strategy(strategy, user_message)
```

## Service Dependencies

The wisdom services coordinate with other service container components:
- **`KnowledgeEngine`**: For database query processing
- **`FleetDatabaseController`**: For low-level database operations
- **`ContentFilterService`**: For content validation and safety
- **`AttentionEngine`**: For roleplay strategy determination
- **`EmotionEngine`**: For personality context integration 