from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field, model_validator


class ManualLineItemInput(BaseModel):
    """A non-time-based line, e.g. a fixed-fee milestone billing or an
    expense reimbursement."""

    description: str
    amount: Decimal
    hours: Optional[Decimal] = None
    rate: Optional[Decimal] = None


class InvoiceCreate(BaseModel):
    project_id: int
    contract_id: Optional[int] = None
    due_date: Optional[date] = None
    notes: Optional[str] = None
    tax_amount: Optional[Decimal] = Decimal("0")

    # Explicit selection of WIP time entries to bill. If omitted entirely
    # (None), every currently-uninvoiced billable time entry on the
    # project is pulled in -- "bill everything in WIP". Pass an empty list
    # to generate an invoice with only manual_line_items and no time-based
    # lines at all.
    time_entry_ids: Optional[list[int]] = None
    manual_line_items: list[ManualLineItemInput] = Field(default_factory=list)

    @model_validator(mode="after")
    def at_least_one_source(self):
        if self.time_entry_ids == [] and not self.manual_line_items:
            raise ValueError("Provide at least one time entry or manual line item")
        return self


class InvoiceUpdate(BaseModel):
    due_date: Optional[date] = None
    notes: Optional[str] = None
    tax_amount: Optional[Decimal] = None


class InvoiceRecordPayment(BaseModel):
    amount_paid: Decimal
    paid_date: Optional[date] = None


class InvoiceVoid(BaseModel):
    reason: Optional[str] = None


class InvoiceLineItemOut(BaseModel):
    id: int
    invoice_id: int
    description: str
    hours: Optional[Decimal] = None
    rate: Optional[Decimal] = None
    amount: Decimal
    time_entry_id: Optional[int] = None

    model_config = {"from_attributes": True}


class InvoiceOut(BaseModel):
    id: int
    project_id: int
    contract_id: Optional[int] = None
    invoice_number: str
    status: str
    issue_date: date
    due_date: Optional[date] = None
    subtotal: Decimal
    tax_amount: Decimal
    total_amount: Decimal
    amount_paid: Decimal
    paid_date: Optional[date] = None
    notes: Optional[str] = None
    void_reason: Optional[str] = None
    created_by_email: str
    created_by_name: str
    created_at: datetime
    updated_at: datetime
    line_items: list[InvoiceLineItemOut] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class WipSummaryOut(BaseModel):
    project_id: int
    total_hours: Decimal
    valued_hours: Decimal
    unrated_hours: Decimal
    wip_value: Decimal
    entry_count: int


class RealizationRowOut(BaseModel):
    key: str
    label: str
    worked_hours: Decimal
    worked_value: Decimal
    billed_value: Decimal
    realization_rate: Optional[Decimal] = None


class RealizationReportOut(BaseModel):
    group_by: str
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    firm_worked_value: Decimal
    firm_billed_value: Decimal
    firm_realization_rate: Optional[Decimal] = None
    rows: list[RealizationRowOut] = Field(default_factory=list)
