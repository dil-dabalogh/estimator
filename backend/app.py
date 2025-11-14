import uuid
import asyncio
from pathlib import Path
from fastapi import FastAPI, WebSocket, HTTPException, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from dotenv import load_dotenv

from models import BatchRequest, BatchResponse
from config import load_config
from worker import process_batch, sessions
from websocket_manager import ws_manager

load_dotenv()

app = FastAPI(
    title="Estimation API",
    description="Generate BA notes and PERT estimates from Confluence/Jira URLs",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


@app.post("/api/estimations/batch", response_model=BatchResponse)
async def create_batch_estimation(request: BatchRequest):
    session_id = str(uuid.uuid4())
    config = load_config()
    
    asyncio.create_task(process_batch(session_id, request.items, config))
    
    return BatchResponse(session_id=session_id)


@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    await ws_manager.connect(session_id, websocket)
    try:
        if session_id in sessions:
            await ws_manager.broadcast(session_id, sessions[session_id])
        
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        await ws_manager.disconnect(session_id, websocket)


@app.get("/api/estimations/{session_id}/{name}/ba-notes")
async def download_ba_notes(session_id: str, name: str):
    file_path = Path("/tmp") / session_id / name / "BA_Estimation_Notes.md"
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="BA notes not found")
    
    return FileResponse(
        file_path,
        media_type="text/markdown",
        filename=f"{name}_BA_Notes.md"
    )


@app.get("/api/estimations/{session_id}/{name}/pert")
async def download_pert(session_id: str, name: str):
    file_path = Path("/tmp") / session_id / name / "PERT_Estimate.md"
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="PERT estimate not found")
    
    return FileResponse(
        file_path,
        media_type="text/markdown",
        filename=f"{name}_PERT.md"
    )

