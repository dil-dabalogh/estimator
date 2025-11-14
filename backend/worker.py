import asyncio
from pathlib import Path
from typing import Dict
from models import EstimationRequest, EstimationResult, EstimationStatus
from config import AppConfig
from llm_service import OpenAIProvider, BedrockProvider
from confluence_client import parse_confluence_config
from estimation_service import generate_ba_notes, generate_pert_sheet
from utils import parse_man_weeks_from_pert, calculate_tshirt_size
from websocket_manager import ws_manager


sessions: Dict[str, list[EstimationResult]] = {}


async def process_single_estimation(
    request: EstimationRequest,
    config: AppConfig,
    session_id: str,
    index: int,
) -> EstimationResult:
    result = EstimationResult(
        name=request.name,
        status=EstimationStatus.PENDING,
    )
    
    try:
        result.status = EstimationStatus.FETCHING
        result.progress = "Fetching content from Confluence/Jira"
        sessions[session_id][index] = result
        await ws_manager.broadcast(session_id, sessions[session_id])
        
        if config.provider == "openai":
            provider = OpenAIProvider(api_key=config.openai_api_key)
        else:
            provider = BedrockProvider(region=config.bedrock_region)
        
        confluence_config = parse_confluence_config(
            config.atlassian_url,
            config.atlassian_email,
            config.atlassian_token,
        )
        
        result.status = EstimationStatus.BA_GENERATION
        result.progress = "Generating BA estimation notes"
        sessions[session_id][index] = result
        await ws_manager.broadcast(session_id, sessions[session_id])
        
        loop = asyncio.get_event_loop()
        title, page_md, ba_notes = await loop.run_in_executor(
            None,
            generate_ba_notes,
            provider,
            confluence_config,
            request.url,
            config.llm_config,
            request.ballpark,
        )
        
        output_dir = Path("/tmp") / session_id / request.name
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "BA_Estimation_Notes.md").write_text(ba_notes, encoding="utf-8")
        (output_dir / "input.confluence.page.md").write_text(page_md, encoding="utf-8")
        
        result.ba_notes_available = True
        result.status = EstimationStatus.PERT_GENERATION
        result.progress = "Generating PERT estimation"
        sessions[session_id][index] = result
        await ws_manager.broadcast(session_id, sessions[session_id])
        
        pert_sheet = await loop.run_in_executor(
            None,
            generate_pert_sheet,
            provider,
            request.url,
            ba_notes,
            config.llm_config,
            request.ballpark,
        )
        
        (output_dir / "PERT_Estimate.md").write_text(pert_sheet, encoding="utf-8")
        
        man_weeks = parse_man_weeks_from_pert(pert_sheet)
        if man_weeks:
            result.man_weeks = man_weeks
            result.tshirt_size = calculate_tshirt_size(man_weeks)
        
        result.pert_available = True
        result.status = EstimationStatus.COMPLETED
        result.progress = "Completed"
        sessions[session_id][index] = result
        await ws_manager.broadcast(session_id, sessions[session_id])
        
    except Exception as e:
        result.status = EstimationStatus.FAILED
        result.error = str(e)
        result.progress = "Failed"
        sessions[session_id][index] = result
        await ws_manager.broadcast(session_id, sessions[session_id])
    
    return result


async def process_batch(
    session_id: str,
    requests: list[EstimationRequest],
    config: AppConfig,
):
    sessions[session_id] = [
        EstimationResult(name=req.name, status=EstimationStatus.PENDING)
        for req in requests
    ]
    
    await ws_manager.broadcast(session_id, sessions[session_id])
    
    tasks = [
        process_single_estimation(req, config, session_id, i)
        for i, req in enumerate(requests)
    ]
    
    await asyncio.gather(*tasks, return_exceptions=True)

