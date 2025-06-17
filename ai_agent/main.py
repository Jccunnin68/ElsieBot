"""Main FastAPI application for the AI Agent"""

import os
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from handlers.ai_coordinator.response_coordinator import coordinate_response
from handlers.ai_knowledge.database_controller import get_db_controller
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
    
    # Check database connection by performing a lightweight query
    try:
        db = get_db_controller()
        db.get_all_categories()
        print("✅ Database connection successful.")
    except Exception as e:
        print(f"⚠️  Database connection issues detected: {e}")
    
    # CLEANUP: Reset roleplay state on startup to ensure clean state
    try:
        from handlers.ai_attention.state_manager import get_roleplay_state
        rp_state = get_roleplay_state()
        if rp_state.is_roleplaying:
            print("🧹 CLEANUP: Ending orphaned roleplay session from previous run")
            rp_state.end_roleplay_session("startup_cleanup")
        else:
            print("✅ STARTUP: No active roleplay sessions to clean up")
    except Exception as e:
        print(f"⚠️  STARTUP CLEANUP ERROR: {e}")
        print(f"   Traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=500,
            detail=f"Unhandled error: {str(e)}"
        )
    
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
    db_status = "healthy"
    try:
        get_db_controller().get_all_categories()
    except Exception:
        db_status = "unhealthy"
    return {"status": "healthy", "service": "elsie-ai-agent", "database": db_status}

@app.post("/cleanup")
async def manual_cleanup():
    """Manual cleanup endpoint for testing"""
    try:
        return {"status": "success", "message": "Manual cleanup completed"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/debug/roleplay")
async def debug_roleplay_state():
    """Debug endpoint to check current roleplay state"""
    try:
        from handlers.ai_attention.state_manager import get_roleplay_state
        rp_state = get_roleplay_state()
        
        state_info = {
            "is_roleplaying": rp_state.is_roleplaying,
            "session_info": rp_state.to_dict() if rp_state.is_roleplaying else None,
            "participants": rp_state.get_participant_names() if rp_state.is_roleplaying else [],
            "dgm_session": rp_state.is_dgm_session() if rp_state.is_roleplaying else False
        }
        
        return {"status": "success", "roleplay_state": state_info}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/debug/roleplay/reset")
async def reset_roleplay_state():
    """Debug endpoint to force reset roleplay state"""
    try:
        from handlers.ai_attention.state_manager import get_roleplay_state
        rp_state = get_roleplay_state()
        
        was_active = rp_state.is_roleplaying
        if was_active:
            rp_state.end_roleplay_session("manual_debug_reset")
            return {"status": "success", "message": "Roleplay session ended", "was_active": True}
        else:
            return {"status": "success", "message": "No active roleplay session", "was_active": False}
    except Exception as e:
        return {"status": "error", "message": str(e)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)