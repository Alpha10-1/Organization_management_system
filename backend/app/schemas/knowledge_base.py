from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class KnowledgeBaseEntryOut(BaseModel):
    model_config = {"from_attributes": True}

    project_id: int
    project_name: str
    engagement_type: str
    risk_level: str
    compliance_flag: Optional[str] = None
    client_id: int
    client_name: Optional[str] = None
    client_industry: Optional[str] = None
    engagement_partner_name: Optional[str] = None
    closed_out_at: Optional[datetime] = None
    close_out_notes: str
    matched_terms: list[str] = []
    snippet: Optional[str] = None


class KnowledgeBaseSearchOut(BaseModel):
    query: Optional[str] = None
    results: list[KnowledgeBaseEntryOut]


class KnowledgeBaseFacetsOut(BaseModel):
    engagement_types: list[str]
    industries: list[str]
    compliance_flags: list[str]
    risk_levels: list[str]
    total_entries: int
