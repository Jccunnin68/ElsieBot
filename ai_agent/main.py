from fastapi import FastAPI, HTTPException
import uvicorn
from datetime import datetime

# Import our modular components
from models import Message
from session_manager import get_or_create_conversation
from ai_handler import get_gemma_response
from content_retrieval_db import load_fleet_wiki_content
from config import PORT

app = FastAPI(title="Elsie - Holographic Bartender")

# Load fleet wiki content at startup
@app.on_event("startup")
async def startup_event():
    """Load fleet wiki content when the application starts"""
    print("🚀 Starting Elsie - Holographic Bartender")
    load_fleet_wiki_content()

@app.get("/")
async def root():
    return {
        "status": "Elsie - Holographic Bartender is operational", 
        "timestamp": datetime.now().isoformat(),
        "message": "Welcome to the most advanced holographic bar in the quadrant!"
    }

@app.post("/process")
async def process_message(message: Message):
    try:
        # Get or create conversation
        context = message.context or {}
        session_id = context.get("session_id", "default")
        conversation = get_or_create_conversation(session_id)
        
        # Add user message
        conversation.add_message("user", message.content)

        # Get holographic bartender response using Gemma
        ai_response = get_gemma_response(message.content, conversation.get_messages())

        # Add AI response to conversation
        conversation.add_message("assistant", ai_response)

        # Update context if needed
        if context.get("update_context"):
            conversation.update_context(context["update_context"])

        return {
            "status": "success",
            "response": ai_response,
            "context": conversation.context,
            "session_id": session_id,
            "bartender": "Elsie - Holographic Bartender"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=PORT) 