"""
Structured Query Handler
========================

This module is the primary handler for all standard (OOC) messages in the
new agentic architecture. It orchestrates the detection, retrieval, and
context-building process for structured and general queries.
"""

from typing import List, Dict, Any

from handlers.ai_logic.response_decision import ResponseDecision
from handlers.ai_logic.structured_query_detector import StructuredQueryDetector
from handlers.ai_wisdom.structured_content_retriever import StructuredContentRetriever
from handlers.ai_wisdom.wisdom_engine import WisdomEngine
from handlers.ai_logic.logic_engine import LogicEngine
from handlers.ai_knowledge.knowledge_engine import get_knowledge_engine

def handle_structured_message(user_message: str, conversation_history: List[Dict]) -> ResponseDecision:
    """
    Orchestrates the handling of a standard (OOC) message using the structured query system.

    Args:
        user_message: The user's input message.
        conversation_history: The history of the conversation.

    Returns:
        A ResponseDecision object containing the strategy for the AI.
    """
    print("🚀 Handling message with Structured Query Handler")
    
    # 1. Detect the query structure
    detector = StructuredQueryDetector()
    structured_query = detector.detect_query(user_message)
    print(f"   - Detected query structure: {structured_query}")

    # Instantiate retriever early to use its db_controller
    retriever = StructuredContentRetriever()

    # If the query is general, use the LogicEngine to determine the category
    if structured_query.get('type') == 'general':
        print("   - General query detected, invoking LogicEngine to determine category...")
        logic_engine = LogicEngine()
        
        # Get all available categories from the database to help the LLM choose.
        all_categories = retriever.db_controller.get_all_categories()
        
        category = logic_engine.determine_query_category(user_message, all_categories)
        structured_query['category'] = category
        print(f"   - LogicEngine determined category: {category}")

    # 2. Retrieve content based on the detected structure
    results = retriever.get_content(structured_query)
    print(f"   - Retrieved {len(results)} results from database")

    # If the query is for logs, run it through the KnowledgeEngine for cleaning.
    if structured_query.get('type') == 'logs' and results:
        print("   - Log query detected, invoking KnowledgeEngine for cleaning...")
        knowledge_engine = get_knowledge_engine()
        
        # Combine the raw content from all results into a single block
        raw_log_content = "\n".join([res.get('raw_content', '') for res in results])
        
        # Clean the logs using the KnowledgeEngine
        cleaned_content = knowledge_engine.process_logs(raw_log_content)

        # --- DEBUGGING: Print stats from the KnowledgeEngine ---
        print("   - KNOWLEDGE ENGINE PROCESSING COMPLETE ---")
        print(f"   - Input content length: {len(raw_log_content)} chars, {raw_log_content.count(chr(10)) + 1} lines")
        print(f"   - Output content length: {len(cleaned_content)} chars, {cleaned_content.count(chr(10)) + 1} lines")
        retention_rate = (len(cleaned_content) / len(raw_log_content)) * 100 if len(raw_log_content) > 0 else 0
        print(f"   - Content retention: {retention_rate:.1f}%")
        # Uncomment below line for full content debugging:
        # print(cleaned_content)
        print("   - END KNOWLEDGE ENGINE STATS ---")
        # ---------------------------------------------------------

        # Replace the original results with a single entry containing the cleaned content
        results = [{
            'title': f"Cleaned Log for '{structured_query.get('subject')}'",
            'raw_content': cleaned_content
        }]

    # 3. Build the final context for the LLM using the appropriate builder
    context_builder = WisdomEngine()
    
    # The strategy now includes the results for the context builder
    strategy = {
        'approach': structured_query.get('type', 'comprehensive'),
        'subject': structured_query.get('term') or structured_query.get('subject'),
        'results': results,
        'temporal_type': structured_query.get('modifier'),
        'category': structured_query.get('category'),
        'reasoning': f"Standard query routed to '{structured_query.get('type', 'comprehensive')}' handler."
    }
    
    final_context = context_builder.build_context_for_strategy(strategy, user_message)

    # 4. Create the final ResponseDecision
    # In the new system, the context IS the pre-generated response for the next stage
    return ResponseDecision(
        needs_ai_generation=True,
        pre_generated_response=final_context,
        strategy=strategy
    )

