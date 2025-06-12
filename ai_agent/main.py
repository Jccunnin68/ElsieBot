"""Main FastAPI application for the AI Agent"""

import os
import sys
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from handlers.ai_coordinator import coordinate_response
from content_retrieval_db import check_elsiebrain_connection, run_database_cleanup

# Check if cleanup flag is set
CLEANUP_ON_STARTUP = os.getenv("CLEANUP_DATABASE", "false").lower() == "true"

class ChatMessage(BaseModel):
    message: str
    conversation_history: list = []
    context: dict = {}

from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown events"""
    print("🚀 Starting Elsie AI Agent...")
    
    # Check database connection
    if not check_elsiebrain_connection():
        print("⚠️  Database connection issues detected")
    
    # Run cleanup if requested
    if CLEANUP_ON_STARTUP:
        print("🧹 Running database cleanup on startup...")
        cleanup_result = run_database_cleanup()
        if cleanup_result:
            print("✅ Database cleanup completed successfully!")
        else:
            print("❌ Database cleanup failed!")
    
    yield
    
    # Add any cleanup code here if needed
    print("👋 Shutting down Elsie AI Agent...")

# Initialize FastAPI app with lifespan
app = FastAPI(title="Elsie AI Agent", lifespan=lifespan)

# Serve static files
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def read_root():
    """Serve the main page"""
    return FileResponse('static/index.html')

@app.post("/process")
async def process_message(chat_message: ChatMessage):
    """Process a chat message and return AI response"""
    try:
        # Extract channel context from the request context
        channel_context = None
        if chat_message.context:
            # Build channel context from Discord bot context
            channel_context = {
                'session_id': chat_message.context.get('session_id'),
                'platform': chat_message.context.get('platform', 'unknown'),
                'type': chat_message.context.get('channel_type', 'unknown'),
                'name': chat_message.context.get('channel_name', 'unknown'),
                'is_thread': chat_message.context.get('is_thread', False),
                'is_dm': chat_message.context.get('is_dm', False),
                'channel_id': chat_message.context.get('channel_id'),
                'guild_id': chat_message.context.get('guild_id'),
                'user_id': chat_message.context.get('user_id'),
                'username': chat_message.context.get('username'),
                'raw_context': chat_message.context  # Keep original for debugging
            }
            
            # Log the incoming context for debugging
            print(f"🌐 RECEIVED CONTEXT FROM DISCORD BOT:")
            print(f"   📋 Raw Context: {chat_message.context}")
            print(f"   🔧 Processed Context: {channel_context}")
        
        response = coordinate_response(chat_message.message, chat_message.conversation_history, channel_context)
        return {"response": response}
    except Exception as e:
        print(f"Error processing message: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "elsie-ai-agent"}

@app.post("/cleanup")
async def manual_cleanup():
    """Manual cleanup endpoint"""
    try:
        result = run_database_cleanup()
        if result:
            return {"status": "success", "message": "Database cleanup completed", "results": result}
        else:
            return {"status": "error", "message": "Database cleanup failed"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)