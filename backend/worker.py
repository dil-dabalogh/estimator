import os
import asyncio
from pathlib import Path
from typing import Dict
from models import EstimationRequest, EstimationResult, EstimationStatus
from config import AppConfig
from llm_service import OpenAIProvider, BedrockProvider
from confluence_client import parse_confluence_config
from estimation_service import generate_requirements, generate_ba_notes, generate_pert_sheet
from utils import parse_man_weeks_from_pert, calculate_tshirt_size, parse_maturity_state_from_pert
from websocket_manager import ws_manager


sessions: Dict[str, list[EstimationResult]] = {}


# Check if running in Lambda with WebSocket API
IS_LAMBDA = bool(os.environ.get('WEBSOCKET_API_ENDPOINT'))
WEBSOCKET_API_ENDPOINT = os.environ.get('WEBSOCKET_API_ENDPOINT', '')


async def broadcast_update(session_id: str, results: list[EstimationResult]):
    """
    Broadcast update to WebSocket clients.
    Uses Lambda WebSocket API if running in Lambda, otherwise uses FastAPI WebSocket manager.
    """
    if IS_LAMBDA and WEBSOCKET_API_ENDPOINT:
        # Running in Lambda - use API Gateway WebSocket
        try:
            from websocket_handlers import broadcast_to_session
            # Run in thread pool since broadcast_to_session is synchronous
            loop = asyncio.get_event_loop()
            message = {"session_id": session_id, "results": [r.model_dump() for r in results]}
            await loop.run_in_executor(
                None, 
                broadcast_to_session,
                session_id,
                message,
                WEBSOCKET_API_ENDPOINT
            )
        except Exception as e:
            print(f"Error broadcasting via Lambda WebSocket: {e}")
    else:
        # Running locally with FastAPI
        await ws_manager.broadcast(session_id, results)


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
        await broadcast_update(session_id, sessions[session_id])
        
        if config.provider == "openai":
            provider = OpenAIProvider(api_key=config.openai_api_key)
        else:
            provider = BedrockProvider(region=config.bedrock_region)
        
        confluence_config = parse_confluence_config(
            config.atlassian_url,
            config.atlassian_email,
            config.atlassian_token,
        )
        
        result.status = EstimationStatus.REQUIREMENTS_GENERATION
        result.progress = "Generating requirements document"
        sessions[session_id][index] = result
        await broadcast_update(session_id, sessions[session_id])
        
        loop = asyncio.get_event_loop()
        title, page_md, requirements_md = await loop.run_in_executor(
            None,
            generate_requirements,
            provider,
            confluence_config,
            request.url,
            config.llm_config,
            request.ballpark,
        )
        
        output_dir = Path("/tmp") / session_id / request.name
        output_dir.mkdir(parents=True, exist_ok=True)
        
        if not requirements_md or len(requirements_md.strip()) < 100:
            raise ValueError(
                f"Requirements generation failed: received empty or too short content ({len(requirements_md)} chars). "
                "This may indicate an LLM error or configuration issue."
            )
        
        (output_dir / "Requirements.md").write_text(requirements_md, encoding="utf-8")
        (output_dir / "input.confluence.page.md").write_text(page_md, encoding="utf-8")
        
        print(f"[{request.name}] Requirements generated successfully: {len(requirements_md)} chars")
        
        result.requirements_available = True
        result.status = EstimationStatus.BA_GENERATION
        result.progress = "Generating BA estimation notes"
        sessions[session_id][index] = result
        await broadcast_update(session_id, sessions[session_id])
        
        ba_notes = await loop.run_in_executor(
            None,
            generate_ba_notes,
            provider,
            request.url,
            requirements_md,
            config.llm_config,
            request.ballpark,
        )
        
        if not ba_notes or len(ba_notes.strip()) < 100:
            raise ValueError(
                f"BA notes generation failed: received empty or too short content ({len(ba_notes)} chars). "
                "This may indicate an LLM error or configuration issue."
            )
        
        (output_dir / "BA_Estimation_Notes.md").write_text(ba_notes, encoding="utf-8")
        
        print(f"[{request.name}] BA notes generated successfully: {len(ba_notes)} chars")
        
        result.ba_notes_available = True
        result.status = EstimationStatus.PERT_GENERATION
        result.progress = "Generating PERT estimation"
        sessions[session_id][index] = result
        await broadcast_update(session_id, sessions[session_id])
        
        pert_sheet = await loop.run_in_executor(
            None,
            generate_pert_sheet,
            provider,
            request.url,
            ba_notes,
            config.llm_config,
            request.ballpark,
        )
        
        if not pert_sheet or len(pert_sheet.strip()) < 100:
            raise ValueError(
                f"PERT estimation generation failed: received empty or too short content ({len(pert_sheet)} chars). "
                "This may indicate an LLM error or configuration issue."
            )
        
        (output_dir / "PERT_Estimate.md").write_text(pert_sheet, encoding="utf-8")
        
        print(f"[{request.name}] PERT estimation generated successfully: {len(pert_sheet)} chars")
        
        man_weeks = parse_man_weeks_from_pert(pert_sheet)
        if man_weeks:
            result.man_weeks = man_weeks
            result.tshirt_size = calculate_tshirt_size(man_weeks)
            print(f"[{request.name}] Parsed {man_weeks} man-weeks, T-shirt size: {result.tshirt_size}")
        else:
            print(f"[{request.name}] Warning: Could not parse man-weeks from PERT estimation")
        
        maturity_state = parse_maturity_state_from_pert(pert_sheet)
        if maturity_state:
            result.maturity_state = maturity_state
            print(f"[{request.name}] Parsed maturity state: {result.maturity_state}")
        else:
            print(f"[{request.name}] Warning: Could not parse maturity state from PERT estimation")
        
        result.pert_available = True
        result.status = EstimationStatus.COMPLETED
        result.progress = "Completed"
        sessions[session_id][index] = result
        await broadcast_update(session_id, sessions[session_id])
        
    except Exception as e:
        result.status = EstimationStatus.FAILED
        result.error = str(e)
        result.progress = "Failed"
        sessions[session_id][index] = result
        await broadcast_update(session_id, sessions[session_id])
    
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
    
    await broadcast_update(session_id, sessions[session_id])
    
    tasks = [
        process_single_estimation(req, config, session_id, i)
        for i, req in enumerate(requests)
    ]
    
    await asyncio.gather(*tasks, return_exceptions=True)

