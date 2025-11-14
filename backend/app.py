import uuid
import asyncio
from pathlib import Path
from fastapi import FastAPI, WebSocket, HTTPException, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from dotenv import load_dotenv

from models import BatchRequest, BatchResponse, ConfluenceExportRequest, ConfluenceExportResponse
from config import load_config
from worker import process_batch, sessions
from websocket_manager import ws_manager
from confluence_client import parse_confluence_config, create_confluence_page

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


@app.post("/api/estimations/{session_id}/{name}/export-confluence", response_model=ConfluenceExportResponse)
async def export_to_confluence(session_id: str, name: str, request: ConfluenceExportRequest):
    """Export estimation to Confluence as a new page."""
    config = load_config()
    
    # Check if Atlassian credentials are configured
    if not config.atlassian_url or not config.atlassian_email or not config.atlassian_token:
        raise HTTPException(
            status_code=500,
            detail="Atlassian credentials not configured"
        )
    
    # Verify files exist
    base_path = Path("/tmp") / session_id / name
    pert_path = base_path / "PERT_Estimate.md"
    ba_notes_path = base_path / "BA_Estimation_Notes.md"
    
    if not pert_path.exists():
        raise HTTPException(status_code=404, detail="PERT estimate not found")
    if not ba_notes_path.exists():
        raise HTTPException(status_code=404, detail="BA notes not found")
    
    # Read the content files
    try:
        pert_content = pert_path.read_text(encoding="utf-8")
        ba_notes_content = ba_notes_path.read_text(encoding="utf-8")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading files: {str(e)}")
    
    # Combine content: PERT first, then BA notes
    combined_content = f"{pert_content}\n\n---\n\n{ba_notes_content}"
    
    # Create Confluence configuration
    confluence_cfg = parse_confluence_config(
        config.atlassian_url,
        config.atlassian_email,
        config.atlassian_token
    )
    
    # Create the page
    success, page_url, error = create_confluence_page(
        confluence_cfg,
        name,
        combined_content,
        request.parent_page_url
    )
    
    if success:
        return ConfluenceExportResponse(success=True, page_url=page_url)
    else:
        # Return error details, use 409 for duplicate pages
        if error and "already exists" in error:
            raise HTTPException(status_code=409, detail=error)
        return ConfluenceExportResponse(success=False, error=error or "Unknown error")

