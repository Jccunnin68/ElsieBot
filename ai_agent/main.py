"""Main FastAPI application for the AI Agent"""

import os
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from handlers.ai_coordinator import coordinate_response
from handlers.ai_wisdom.content_retriever import check_elsiebrain_connection
from database_controller import get_db_controller
import traceback

# Check if cleanup flag is set
CLEANUP_ON_STARTUP = os.getenv("CLEANUP_DATABASE", "false").lower() == "true"

class ChatMessage(BaseModel):
    message: str
    context: dict = {}
    conversation_history: list = []

from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown events"""
    print("🚀 Starting Elsie AI Agent...")
    
    # Check database connection
    if not check_elsiebrain_connection():
        print("⚠️  Database connection issues detected")
    
    # Run cleanup if requested

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
async def process_message(message: ChatMessage):
    """Process a message and return a response."""
    try:
        print(f"\n📥 RECEIVED MESSAGE:")
        print(f"   Message: {message.message}")
        print(f"   Raw Context: {message.context}")
        print(f"   Conversation History: {message.conversation_history}")
        
        # Process channel context
        channel_context = {}
        if message.context:
            try:
                channel_context = {
                    'channel_id': message.context.get('channel_id'),
                    'channel_name': message.context.get('channel_name'),
                    'channel_type': message.context.get('channel_type'),
                    'is_dm': message.context.get('is_dm', False),
                    'is_thread': message.context.get('is_thread', False),
                    'guild_id': message.context.get('guild_id'),
                    'user_id': message.context.get('user_id'),
                    'username': message.context.get('username')
                }
                print(f"   📍 Channel Context: {channel_context}")
            except Exception as e:
                print(f"❌ ERROR processing channel context:")
                print(f"   Error: {str(e)}")
                print(f"   Traceback: {traceback.format_exc()}")
                raise HTTPException(
                    status_code=500,
                    detail=f"Error processing channel context: {str(e)}"
                )
        
        # Process message through strategy engine
        try:
            response_text = coordinate_response(
                message.message,
                message.conversation_history,
                channel_context
            )
            print(f"   ✅ Response generated: {response_text}")

            # Construct the response in the format Go expects
            ai_response = {
                "status": "success",
                "response": response_text,
                "session_id": message.context.get("session_id"),
                "context": message.context,
                "bartender": "elsie"
            }
            return JSONResponse(content=ai_response)

        except Exception as e:
            print(f"❌ ERROR in coordinate_response:")
            print(f"   Error: {str(e)}")
            print(f"   Traceback: {traceback.format_exc()}")
            raise HTTPException(
                status_code=500,
                detail=f"Error generating response: {str(e)}"
            )
            
    except Exception as e:
        print(f"❌ UNHANDLED ERROR in process_message:")
        print(f"   Error: {str(e)}")
        print(f"   Traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=500,
            detail=f"Unhandled error: {str(e)}"
        )

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "elsie-ai-agent"}

@app.post("/cleanup")
async def manual_cleanup():
    """Manual cleanup endpoint"""
    try:
        controller = get_db_controller()
        ship_cleanup = controller.cleanup_mission_log_ship_names()
        seed_cleanup = controller.cleanup_seed_data()
        
        results = {
            "ship_cleanup": ship_cleanup,
            "seed_cleanup": seed_cleanup
        }
        
        return {
            "status": "success", 
            "message": "Database cleanup completed", 
            "results": results
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)