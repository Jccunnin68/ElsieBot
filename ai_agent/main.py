"""Main FastAPI application for the AI Agent"""

import os
import sys
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from ai_handler import get_gemma_response
from content_retrieval_db import check_elsiebrain_connection, run_database_cleanup

# Check if cleanup flag is set
CLEANUP_ON_STARTUP = os.getenv("CLEANUP_DATABASE", "false").lower() == "true"

app = FastAPI(title="Elsie AI Agent")

# Serve static files
app.mount("/static", StaticFiles(directory="static"), name="static")

class ChatMessage(BaseModel):
    message: str
    conversation_history: list = []

@app.on_event("startup")
async def startup_event():
    """Run startup checks"""
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

@app.get("/")
async def read_root():
    """Serve the main page"""
    return FileResponse('static/index.html')

@app.post("/process")
async def process_message(chat_message: ChatMessage):
    """Process a chat message and return AI response"""
    try:
        response = get_gemma_response(chat_message.message, chat_message.conversation_history)
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