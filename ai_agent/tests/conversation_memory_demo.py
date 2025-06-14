"""
Conversation Memory Demo - Demonstration of Enhanced Roleplay Context
====================================================================

This script demonstrates how the new conversation memory system works
to enhance Elsie's roleplay responses with better continuity and context.
"""

from ai_agent.handlers.ai_attention.conversation_memory import ConversationMemory, getNextResponse, track_elsie_response, format_conversation_for_context


def demo_conversation_flow():
    """
    Demonstrate how conversation memory enhances roleplay context.
    """
    print("🎭 CONVERSATION MEMORY SYSTEM DEMO")
    print("=" * 50)
    
    # Initialize conversation memory
    memory = ConversationMemory(max_history=5)
    
    # Simulate a roleplay conversation
    conversation_turns = [
        {"speaker": "Tavi", "message": "*walks into the bar looking tired*", "turn": 1},
        {"speaker": "Elsie", "message": "*looks up from polishing glasses* \"Rough day, Tavi?\"", "turn": 2},
        {"speaker": "Tavi", "message": "\"You could say that. Had a difficult training session with Commander Sif.\"", "turn": 3},
        {"speaker": "Elsie", "message": "*sets down a glass of water* \"Want to talk about it?\"", "turn": 4},
        {"speaker": "Tavi", "message": "\"It's just... sometimes I feel like I'm not living up to expectations.\"", "turn": 5},
    ]
    
    print("🎪 SIMULATING ROLEPLAY CONVERSATION:")
    print("-" * 40)
    
    # Process each turn
    for turn_data in conversation_turns:
        speaker = turn_data["speaker"]
        message = turn_data["message"]
        turn_number = turn_data["turn"]
        
        print(f"\n📝 Turn {turn_number}: [{speaker}] {message}")
        
        # Add to conversation memory
        memory.add_turn(speaker, message, turn_number)
        
        # If this is a user turn (not Elsie), analyze for response suggestions
        if speaker != "Elsie" and memory.has_sufficient_context():
            print("\n💭 ANALYZING CONVERSATION FOR RESPONSE SUGGESTIONS:")
            
            # Prepare conversation history for analysis
            conversation_history = []
            for hist_turn in memory.get_recent_history():
                conversation_history.append({
                    'speaker': hist_turn.speaker,
                    'message': hist_turn.message,
                    'turn_number': hist_turn.turn_number,
                    'message_type': hist_turn.message_type
                })
            
            # Get response suggestion
            suggestion, analyzed = getNextResponse(
                conversation_history=conversation_history,
                memory_store=memory,
                character_context={'dgm_session': False}
            )
            
            if analyzed:
                print(f"   🎯 SUGGESTED RESPONSE STYLE:")
                print(f"      - Style: {suggestion.style}")
                print(f"      - Tone: {suggestion.tone}")
                print(f"      - Approach: {suggestion.approach}")
                print(f"      - Direction: {suggestion.conversation_direction}")
                print(f"      - Themes: {suggestion.themes}")
                print(f"      - Reasoning: {suggestion.reasoning}")
    
    print("\n" + "=" * 50)
    print("📚 FINAL CONVERSATION CONTEXT:")
    print("-" * 40)
    
    # Show formatted conversation context
    context = format_conversation_for_context(memory, include_analysis=True)
    print(context)
    
    print("\n" + "=" * 50)
    print("🎭 ROLEPLAY PROMPT INTEGRATION EXAMPLE:")
    print("-" * 40)
    
    # Show how this would be integrated into a roleplay prompt
    latest_suggestion = memory.get_last_suggestion()
    if latest_suggestion:
        sample_prompt_section = f"""
**CONVERSATION FLOW GUIDANCE**:
- Suggested response style: {latest_suggestion.style}
- Suggested tone: {latest_suggestion.tone}
- Conversation direction: {latest_suggestion.conversation_direction}
- Active themes: {', '.join(latest_suggestion.themes) if latest_suggestion.themes else 'None'}
- Analysis: {latest_suggestion.reasoning}

**CONVERSATION CONTINUITY**: Use the conversation context above to maintain natural flow and avoid repetition. 
Reference recent events, emotions, or topics naturally.

{context}

This shows the recent flow of conversation. Use this context to maintain continuity, avoid repetition, 
and respond appropriately to the conversational dynamics.
"""
        print(sample_prompt_section)
    
    print("\n✨ DEMO COMPLETE - Conversation memory system provides:")
    print("   🔄 Conversation flow analysis")
    print("   🎯 Response style suggestions")
    print("   📝 Context continuity")
    print("   🧠 Memory of recent exchanges")
    print("   🎭 Enhanced roleplay immersion")


def demo_conversation_analysis_types():
    """
    Demonstrate different types of conversation analysis.
    """
    print("\n🤖 CONVERSATION ANALYSIS TYPES DEMO")
    print("=" * 50)
    
    test_conversations = [
        {
            "name": "Emotional Support Scenario",
            "messages": [
                "*sits at the bar looking dejected*",
                "\"What's wrong? You look upset.\"",
                "\"I just got some bad news from home.\""
            ]
        },
        {
            "name": "Technical Discussion",
            "messages": [
                "\"Elsie, what do you know about stellar cartography?\"",
                "\"Quite a bit actually. What specifically interests you?\"",
                "\"I'm trying to understand how we navigate in the Large Magellanic Cloud.\""
            ]
        },
        {
            "name": "Social Interaction",
            "messages": [
                "\"Hey everyone! *waves to the bar*\"",
                "\"Hello there! Welcome to the bar.\"",
                "\"Thanks! Mind if I join the conversation?\""
            ]
        }
    ]
    
    for scenario in test_conversations:
        print(f"\n🎪 SCENARIO: {scenario['name']}")
        print("-" * 30)
        
        memory = ConversationMemory()
        
        # Add messages to memory
        for i, message in enumerate(scenario['messages']):
            speaker = "User" if i % 2 == 0 else "Elsie"
            memory.add_turn(speaker, message, i + 1)
        
        # Analyze the conversation
        if memory.has_sufficient_context():
            conversation_history = []
            for turn in memory.get_recent_history():
                conversation_history.append({
                    'speaker': turn.speaker,
                    'message': turn.message,
                    'turn_number': turn.turn_number
                })
            
            suggestion, analyzed = getNextResponse(
                conversation_history=conversation_history,
                memory_store=memory
            )
            
            print(f"📊 ANALYSIS RESULTS:")
            print(f"   Style: {suggestion.style}")
            print(f"   Tone: {suggestion.tone}")
            print(f"   Approach: {suggestion.approach}")
            print(f"   Direction: {suggestion.conversation_direction}")
            print(f"   Themes: {suggestion.themes}")


if __name__ == "__main__":
    # Run the demonstrations
    demo_conversation_flow()
    demo_conversation_analysis_types() 