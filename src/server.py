import os
import sys
import uuid
from typing import List, Optional, Dict
from fastapi import FastAPI, HTTPException, Body, Header, Depends
from pydantic import BaseModel
from contextlib import asynccontextmanager

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.client import ChatClient
from src.personality.manager import PersonaManager
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

# --- Global Components ---
manager = PersonaManager()
client = ChatClient()

# --- Session Management ---
class SessionData:
    def __init__(self, persona_id: str = "default_wife"):
        self.persona_id = persona_id
        self.history = []

# Simple in-memory session store
sessions: Dict[str, SessionData] = {}

def get_session(x_session_id: Optional[str] = Header(None)) -> SessionData:
    if not x_session_id:
        # If no session ID provided, create a temporary one for this request (or error out)
        # For simplicity in this demo, we'll create a new session but client won't know ID unless returned
        # Better practice: Client should generate UUID or Server returns it on login.
        # Here we'll just require it or use a default "public" session (which is also bad for concurrency but good for simple testing)
        raise HTTPException(status_code=400, detail="X-Session-ID header is required")
    
    if x_session_id not in sessions:
        sessions[x_session_id] = SessionData()
    
    return sessions[x_session_id]

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
async def get_current_persona(x_session_id: str = Header(...)):
    if x_session_id not in sessions:
         sessions[x_session_id] = SessionData()
    
    session = sessions[x_session_id]
    persona = manager.get_persona(session.persona_id)
    if not persona:
        # Fallback if persona ID is invalid
        session.persona_id = "default_wife"
        persona = manager.get_persona(session.persona_id)
        
    return persona.metadata

@app.post("/personas/switch")
async def switch_persona(req: SwitchRequest, x_session_id: str = Header(...)):
    if x_session_id not in sessions:
        sessions[x_session_id] = SessionData()
    session = sessions[x_session_id]

    if manager.get_persona(req.persona_id):
        session.persona_id = req.persona_id
        session.history = [] # Reset history on switch
        return {"status": "success", "message": f"Switched to {req.persona_id}"}
    else:
        raise HTTPException(status_code=404, detail="Persona not found")

@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest, x_session_id: str = Header(...)):
    if x_session_id not in sessions:
        sessions[x_session_id] = SessionData()
    session = sessions[x_session_id]

    persona = manager.get_persona(session.persona_id)
    if not persona:
        raise HTTPException(status_code=500, detail="Current persona is invalid")

    # Construct messages
    system_prompt = SystemMessage(content=persona.prompts.system)
    # 將使用者的輸入包裝在 <user_message> 標籤中，提高辨識度
    formatted_input = f"<user_message>\n{req.message}\n</user_message>"
    messages = [system_prompt] + session.history + [HumanMessage(content=formatted_input)]

    try:
        # For now, only sync supported in this endpoint wrapper
        # Ensure we use the client correctly
        # Construct config for LangSmith tracing
        config = {
            "tags": [f"persona:{persona.metadata.id}", f"session:{x_session_id}"]
        }
        response_text = client.chat(messages, temperature=persona.config.temperature, config=config)
        
        # Update history
        session.history.append(HumanMessage(content=req.message))
        session.history.append(AIMessage(content=response_text))
        
        return ChatResponse(
            response=response_text,
            persona_id=persona.metadata.id,
            version=persona.metadata.version
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/history")
async def get_history(x_session_id: str = Header(...)):
    if x_session_id not in sessions:
        return []
    session = sessions[x_session_id]
    # Convert LangChain messages to dict
    return [{"type": m.type, "content": m.content} for m in session.history]

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
