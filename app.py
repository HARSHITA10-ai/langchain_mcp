"""
Main FastAPI Entry Point for the Multi-Agent Payroll Analysis System.
Simplified: always returns JSON matching the Supervisor unified template.
"""
import sys
import os
import base64
import json
import asyncio

from client import main, initialize_agent
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# --- Load environment ---
load_dotenv()

# --- FastAPI setup ---
app = FastAPI(title="Payroll Analysis Multi-Agent API")

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

@app.get("/initialize_agent")
async def agent_setup():
   
    try:
         
       

        # Send the user's message to the agent
        response = await initialize_agent()

        if response:


            return {
                "content": "agent initialized"
            }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- Main chat endpoint ---
@app.post("/chat", tags=["Chat"])
async def chat_endpoint(request: ChatRequest):
   
    try:
         
       

        # Send the user's message to the agent
        response = await main(request.user_id,request.query)


        return {
            "content": response
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
