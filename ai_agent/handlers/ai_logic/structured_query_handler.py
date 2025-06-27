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
# REMOVED: Global import replaced by service container

# Constants for chunking
KNOWLEDGE_ENGINE_CHUNK_SIZE = 25000  # 25,000 characters per chunk

def chunk_content(content: str, chunk_size: int = KNOWLEDGE_ENGINE_CHUNK_SIZE) -> List[str]:
    """
    Split content into chunks of specified size for processing.
    
    Args:
        content: The content to chunk
        chunk_size: Maximum size of each chunk
        
    Returns:
        List of content chunks
    """
    if len(content) <= chunk_size:
        return [content]
    
    chunks = []
    for i in range(0, len(content), chunk_size):
        chunks.append(content[i:i + chunk_size])
    
    return chunks

def process_single_log_through_knowledge_engine(raw_content: str) -> str:
    """
    Process a single log through the knowledge engine using chunking.
    
    Args:
        raw_content: The raw log content to process
        
    Returns:
        Cleaned and reconstructed log content
    """
    if not raw_content:
        return raw_content
    
    # Lazy import to avoid circular dependencies
    from handlers.service_container import get_knowledge_engine
    knowledge_engine = get_knowledge_engine()
    
    # Split into chunks if content is large
    chunks = chunk_content(raw_content)
    print(f"   📄 Processing {len(chunks)} chunks through KnowledgeEngine...")
    
    cleaned_chunks = []
    total_input_chars = 0
    total_output_chars = 0
    
    for i, chunk in enumerate(chunks, 1):
        print(f"   🧹 Processing chunk {i}/{len(chunks)} ({len(chunk)} chars)...")
        cleaned_chunk = knowledge_engine.process_logs(chunk)
        cleaned_chunks.append(cleaned_chunk)
        
        total_input_chars += len(chunk)
        total_output_chars += len(cleaned_chunk)
        
        chunk_retention = (len(cleaned_chunk) / len(chunk)) * 100 if len(chunk) > 0 else 0
        print(f"   📊 Chunk {i}: {len(chunk)} → {len(cleaned_chunk)} chars ({chunk_retention:.1f}% retention)")
    
    # Reconstruct the full log from processed chunks
    reconstructed_content = "\n".join(cleaned_chunks)
    
    # Print overall stats
    overall_retention = (total_output_chars / total_input_chars) * 100 if total_input_chars > 0 else 0
    print(f"   ✅ KnowledgeEngine processing complete:")
    print(f"   - Total: {total_input_chars} → {total_output_chars} chars ({overall_retention:.1f}% retention)")
    print(f"   - Processed {len(chunks)} chunks, reconstructed into single log")
    
    return reconstructed_content

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

    # If the query is for logs, determine processing approach
    if structured_query.get('type') == 'logs' and results:
        # Check if this is a multi-log query that needs historical summary
        is_multi_log_historical = any(result.get('use_historical_summary') for result in results)
        force_historical = structured_query.get('force_historical_summary', False)
        
        print(f"   🔍 LOG PROCESSING ANALYSIS:")
        print(f"   - is_multi_log_historical: {is_multi_log_historical}")
        print(f"   - force_historical: {force_historical}")
        print(f"   - results count: {len(results)}")
        
        if is_multi_log_historical or force_historical:
            print("   📚 MULTI-LOG QUERY: Using database content directly (pre-entry cleansing already applied)")
            print("   - Skipping KnowledgeEngine for multi-log queries to maintain performance")
            print("   - Database entries already have pre-entry cleansing applied")
            # Results are used as-is from database
            
        else:
            print("   📖 SINGLE LOG NARRATIVE: Processing through KnowledgeEngine with chunking...")
            
            # Combine the raw content from all results into a single block
            raw_log_content = "\n".join([res.get('raw_content', '') for res in results])
            
            # Process through knowledge engine with chunking
            cleaned_content = process_single_log_through_knowledge_engine(raw_log_content)

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
        'force_historical_summary': structured_query.get('force_historical_summary', False),
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

