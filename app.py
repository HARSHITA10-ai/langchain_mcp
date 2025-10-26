"""
Main FastAPI Entry Point for the Multi-Agent Payroll Analysis System.
Simplified: always returns JSON matching the Supervisor unified template.
"""

from client import main, initialize_agent
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Dict, Any
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import json

# --- Load environment ---
load_dotenv()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Load the ML model
    await initialize_agent()
    yield


# --- FastAPI setup ---
app = FastAPI(title="Payroll Analysis Multi-Agent API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Pydantic models ---
class ChatRequest(BaseModel):
    token: str
    query: str
    user_id: str


class ChatResponse(BaseModel):
    message: str
    charts: List[Dict[str, Any]] = []
    is_visualized: bool = False
    suggestions: List[Dict[str, Any]] = []


@app.get("/health")
def health_check():
    return {"status": "ok"}

# --- Main chat endpoint ---
@app.post("/chat", tags=["Chat"])
async def chat_endpoint(request: ChatRequest):
   
    # try:
         
    #     # Send the user's message to the agent
    #     response = await main(request.user_id,request.query)
    #     return {
    #         "content": response
    #     }

    # except Exception as e:
    #     raise HTTPException(status_code=500, detail=str(e))
    
    try:
        async def event_generator():
            # main() is async generator
            async for chunk in main(request.user_id, request.query):
                # data = {"content": chunk}
                yield f"data: {json.dumps(chunk)}\n\n"

        return StreamingResponse(event_generator(), media_type="text/event-stream")

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
