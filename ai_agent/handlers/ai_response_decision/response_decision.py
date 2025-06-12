"""
Response Decision Data Structure
===============================

Contains the ResponseDecision dataclass that represents a decision about
whether and how Elsie should respond to a message.
"""

from dataclasses import dataclass
from typing import Dict, Optional


@dataclass
class ResponseDecision:
    """
    Decision about whether and how Elsie should respond.
    
    This encapsulates the result of Elsie's "inner monologue" process,
    determining the optimal response strategy and whether expensive AI
    generation is needed or if a pre-generated response can be used.
    
    Attributes:
        needs_ai_generation (bool): Whether expensive AI API calls are needed
        pre_generated_response (Optional[str]): Ready-to-use response if available
        strategy (Dict[str, any]): Complete strategy information including:
            - approach: The response approach (e.g., 'roleplay_active', 'simple_chat')
            - needs_database: Whether database lookup is required
            - reasoning: Human-readable explanation of the decision
            - context_priority: Priority level for context inclusion
            - Additional strategy-specific fields
    """
    needs_ai_generation: bool
    pre_generated_response: Optional[str]
    strategy: Dict[str, any] 