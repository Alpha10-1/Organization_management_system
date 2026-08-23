from datetime import date as date_type, datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel


class ProspectCreate(BaseModel):
    name: str
    company_name: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    industry: Optional[str] = None
    website: Optional[str] = None
    source: str = "other"
    department_id: Optional[int] = None
    estimated_value: Optional[Decimal] = None
    expected_close_date: Optional[date_type] = None
    assigned_to_user_id: Optional[int] = None
    notes: Optional[str] = None


class ProspectUpdate(BaseModel):
    name: Optional[str] = None
    company_name: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    industry: Optional[str] = None
    website: Optional[str] = None
    source: Optional[str] = None
    department_id: Optional[int] = None
    estimated_value: Optional[Decimal] = None
    expected_close_date: Optional[date_type] = None
    assigned_to_user_id: Optional[int] = None
    notes: Optional[str] = None


class ProspectStatusUpdate(BaseModel):
    status: str
    # Required by the route when status == "lost"; otherwise optional
    # context for the stage-change log.
    notes: Optional[str] = None


class ProspectConvertRequest(BaseModel):
    """All fields optional -- sensible defaults are derived from the
    prospect's own data (see app.routes.prospects.convert_prospect), but
    can be overridden here since a prospect's loose `name`/`company_name`
    fields don't always map cleanly onto Client's stricter
    business-vs-individual shape.
    """

    client_type: Optional[str] = None  # business | individual | npo
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    company_name: Optional[str] = None


class ProspectStageEventOut(BaseModel):
    id: int
    prospect_id: int
    from_status: Optional[str] = None
    to_status: str
    notes: Optional[str] = None
    actor_email: str
    actor_name: str
    created_at: datetime

    model_config = {"from_attributes": True}


class ProspectOut(BaseModel):
    id: int
    name: str
    company_name: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    industry: Optional[str] = None
    website: Optional[str] = None
    source: str
    status: str
    department_id: Optional[int] = None
    estimated_value: Optional[Decimal] = None
    expected_close_date: Optional[date_type] = None
    assigned_to_user_id: Optional[int] = None
    assigned_to_email: Optional[str] = None
    assigned_to_name: Optional[str] = None
    lost_reason: Optional[str] = None
    notes: Optional[str] = None
    converted_client_id: Optional[int] = None
    converted_at: Optional[datetime] = None
    created_by_email: str
    created_by_name: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PipelineSummaryStage(BaseModel):
    status: str
    count: int
    total_estimated_value: Decimal


class PipelineSummaryOut(BaseModel):
    stages: list[PipelineSummaryStage]
    won_count: int
    lost_count: int
    win_rate_percent: Optional[float] = None
    open_pipeline_value: Decimal
