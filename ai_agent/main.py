from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
import uvicorn
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = FastAPI(title="Elsie AI Agent")

class Message(BaseModel):
    content: str
    context: Optional[dict] = None

@app.get("/")
async def root():
    return {"status": "Elsie AI Agent is running"}

@app.post("/process")
async def process_message(message: Message):
    try:
        # TODO: Implement AI processing logic
        return {
            "status": "success",
            "response": f"Processed message: {message.content}"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port) 