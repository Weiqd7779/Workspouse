import os
import sys
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Body
from pydantic import BaseModel
from contextlib import asynccontextmanager

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.client import ChatClient
from src.personality.manager import PersonaManager
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

# --- Global State ---
manager = PersonaManager()
client = ChatClient()
current_persona_id = "default_wife"
chat_history = []

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Reload personas
    manager.reload()
    print(f"Loaded {len(manager.personas)} personas.")
    yield
    # Shutdown

app = FastAPI(title="AI Wife Chatbot API", lifespan=lifespan)

# --- Pydantic Models ---

class ChatRequest(BaseModel):
    message: str
    stream: bool = False

class ChatResponse(BaseModel):
    response: str
    persona_id: str
    version: str

class PersonaInfo(BaseModel):
    id: str
    version: str
    description: str
    tags: List[str]

class SwitchRequest(BaseModel):
    persona_id: str

# --- Endpoints ---

@app.get("/personas", response_model=List[PersonaInfo])
async def list_personas():
    return manager.list_personas()

@app.get("/personas/current")
async def get_current_persona():
    return manager.get_persona(current_persona_id).metadata

@app.post("/personas/switch")
async def switch_persona(req: SwitchRequest):
    global current_persona_id, chat_history
    if manager.get_persona(req.persona_id):
        current_persona_id = req.persona_id
        chat_history = [] # Reset history on switch
        return {"status": "success", "message": f"Switched to {req.persona_id}"}
    else:
        raise HTTPException(status_code=404, detail="Persona not found")

@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    global chat_history
    
    persona = manager.get_persona(current_persona_id)
    if not persona:
        raise HTTPException(status_code=500, detail="Current persona is invalid")

    # Construct messages
    system_prompt = SystemMessage(content=persona.prompts.system)
    messages = [system_prompt] + chat_history + [HumanMessage(content=req.message)]

    try:
        # For now, only sync supported in this endpoint wrapper
        response_text = client.chat(messages, temperature=persona.config.temperature)
        
        # Update history
        chat_history.append(HumanMessage(content=req.message))
        chat_history.append(AIMessage(content=response_text))
        
        return ChatResponse(
            response=response_text,
            persona_id=persona.metadata.id,
            version=persona.metadata.version
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/history")
async def get_history():
    # Convert LangChain messages to dict
    return [{"type": m.type, "content": m.content} for m in chat_history]

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
