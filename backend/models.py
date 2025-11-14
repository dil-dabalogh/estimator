from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field, HttpUrl


class EstimationStatus(str, Enum):
    PENDING = "pending"
    FETCHING = "fetching"
    BA_GENERATION = "ba_generation"
    PERT_GENERATION = "pert_generation"
    COMPLETED = "completed"
    FAILED = "failed"


class TShirtSize(str, Enum):
    XS = "XS"
    S = "S"
    M = "M"
    L = "L"
    XL = "XL"
    XXL = "XXL"


class EstimationRequest(BaseModel):
    url: str = Field(..., description="Confluence or Jira URL")
    name: str = Field(..., min_length=1, description="Unique name for this estimation")
    ballpark: Optional[str] = Field(None, description="Optional ballpark estimation (e.g., '30 manweeks')")


class BatchRequest(BaseModel):
    items: list[EstimationRequest] = Field(..., min_items=1, description="List of estimation requests")


class BatchResponse(BaseModel):
    session_id: str = Field(..., description="Unique session identifier for tracking progress")


class EstimationResult(BaseModel):
    name: str
    status: EstimationStatus
    progress: Optional[str] = None
    tshirt_size: Optional[TShirtSize] = None
    man_weeks: Optional[float] = None
    error: Optional[str] = None
    ba_notes_available: bool = False
    pert_available: bool = False


class WebSocketMessage(BaseModel):
    session_id: str
    results: list[EstimationResult]


class ConfluenceExportRequest(BaseModel):
    parent_page_url: str = Field(..., description="URL of the parent Confluence page")
    overwrite: bool = Field(default=False, description="If true, overwrite existing page with same title")


class ConfluenceExportResponse(BaseModel):
    success: bool
    page_url: Optional[str] = None
    error: Optional[str] = None


class FetchTitleResponse(BaseModel):
    title: str
    error: Optional[str] = None

