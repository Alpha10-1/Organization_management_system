from datetime import date as date_type
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session

from app.core.activity_logger import log_activity
from app.core.billing import compute_wip, money, resolve_rate
from app.core.deps import get_current_active_user
from app.core.department_scope import department_id_for_project, require_scoped_write
from app.core.time import utcnow
from app.db.session import get_db
from app.models.contract import Contract
from app.models.invoice import Invoice, InvoiceLineItem
from app.models.project import Project
from app.models.time_entry import TimeEntry
from app.schemas.invoice import (
    InvoiceCreate,
    InvoiceLineItemOut,
    InvoiceOut,
    InvoiceRecordPayment,
    InvoiceUpdate,
    InvoiceVoid,
    WipSummaryOut,
)
from app.schemas.user import UserPublic

router = APIRouter(prefix="/invoices", tags=["Billing & Invoicing"])

DEFAULT_PAGE_LIMIT = 100
MAX_PAGE_LIMIT = 200
VALID_STATUSES = {"draft", "sent", "paid", "void"}


def _serialize(db: Session, invoice: Invoice) -> InvoiceOut:
    """InvoiceLineItemOut wants time_entry_id, which lives on TimeEntry
    (the FK points line-item -> entry the other way for WIP-release
    reasons -- see TimeEntry.invoice_line_item_id), so it's resolved here
    rather than via a plain from_attributes pass."""
    line_items = (
        db.query(InvoiceLineItem).filter(InvoiceLineItem.invoice_id == invoice.id).order_by(InvoiceLineItem.id).all()
    )
    entry_by_line_item = {
        te.invoice_line_item_id: te.id
        for te in db.query(TimeEntry.id, TimeEntry.invoice_line_item_id)
        .filter(TimeEntry.invoice_line_item_id.in_([li.id for li in line_items]))
        .all()
    } if line_items else {}

    out = InvoiceOut.model_validate(invoice)
    out.line_items = [
        InvoiceLineItemOut(
            id=li.id,
            invoice_id=li.invoice_id,
            description=li.description,
            hours=li.hours,
            rate=li.rate,
            amount=li.amount,
            time_entry_id=entry_by_line_item.get(li.id),
        )
        for li in line_items
    ]
    return out


def _next_invoice_number(db: Session, issue_date: date_type) -> str:
    year = issue_date.year
    count = db.query(Invoice).filter(Invoice.invoice_number.like(f"INV-{year}-%")).count()
    return f"INV-{year}-{count + 1:05d}"


@router.get("/", response_model=list[InvoiceOut])
def list_invoices(
    response: Response,
    project_id: int | None = Query(default=None),
    contract_id: int | None = Query(default=None),
    status: str | None = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=DEFAULT_PAGE_LIMIT, ge=1, le=MAX_PAGE_LIMIT),
    db: Session = Depends(get_db),
    current_user: UserPublic = Depends(get_current_active_user),
):
    query = db.query(Invoice).filter(Invoice.deleted_at.is_(None))
    if project_id is not None:
        query = query.filter(Invoice.project_id == project_id)
    if contract_id is not None:
        query = query.filter(Invoice.contract_id == contract_id)
    if status:
        query = query.filter(Invoice.status == status)

    response.headers["X-Total-Count"] = str(query.count())
    invoices = query.order_by(Invoice.issue_date.desc(), Invoice.id.desc()).offset(skip).limit(limit).all()
    return [_serialize(db, inv) for inv in invoices]


@router.get("/wip", response_model=WipSummaryOut)
def get_wip(
    project_id: int = Query(...),
    db: Session = Depends(get_db),
    current_user: UserPublic = Depends(get_current_active_user),
):
    """Work-in-progress for a single engagement: billable hours logged but
    not yet invoiced, and their dollar value at resolved rates."""
    project = db.query(Project).filter(Project.id == project_id, Project.deleted_at.is_(None)).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    summary = compute_wip(db, project_id)
    return WipSummaryOut(
        project_id=summary.project_id,
        total_hours=summary.total_hours,
        valued_hours=summary.valued_hours,
        unrated_hours=summary.unrated_hours,
        wip_value=summary.wip_value,
        entry_count=summary.entry_count,
    )


@router.post("/", response_model=InvoiceOut)
def create_invoice(
    payload: InvoiceCreate,
    db: Session = Depends(get_db),
    current_user: UserPublic = Depends(get_current_active_user),
):
    """Generates a draft invoice from WIP time entries (explicit selection,
    or every uninvoiced billable entry on the project when time_entry_ids
    is omitted) plus any manual line items, e.g. a fixed-fee milestone
    billing. Selected time entries are locked to this invoice's line
    items immediately, removing them from WIP."""
    project = db.query(Project).filter(Project.id == payload.project_id, Project.deleted_at.is_(None)).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if payload.contract_id is not None:
        contract = (
            db.query(Contract)
            .filter(Contract.id == payload.contract_id, Contract.deleted_at.is_(None))
            .first()
        )
        if not contract or contract.project_id != project.id:
            raise HTTPException(status_code=404, detail="Contract not found for this project")

    require_scoped_write(db, current_user, department_id_for_project(db, project.id))

    if payload.time_entry_ids is None:
        entries = (
            db.query(TimeEntry)
            .filter(
                TimeEntry.project_id == project.id,
                TimeEntry.deleted_at.is_(None),
                TimeEntry.billable.is_(True),
                TimeEntry.invoice_line_item_id.is_(None),
            )
            .all()
        )
    elif payload.time_entry_ids:
        entries = (
            db.query(TimeEntry)
            .filter(TimeEntry.id.in_(payload.time_entry_ids), TimeEntry.deleted_at.is_(None))
            .all()
        )
        found_ids = {e.id for e in entries}
        missing = set(payload.time_entry_ids) - found_ids
        if missing:
            raise HTTPException(status_code=404, detail=f"Time entries not found: {sorted(missing)}")
        for entry in entries:
            if entry.project_id != project.id:
                raise HTTPException(
                    status_code=400, detail=f"Time entry {entry.id} does not belong to project {project.id}"
                )
            if entry.invoice_line_item_id is not None:
                raise HTTPException(status_code=400, detail=f"Time entry {entry.id} is already invoiced")
    else:
        entries = []

    if not entries and not payload.manual_line_items:
        raise HTTPException(status_code=400, detail="No billable time entries or manual line items to invoice")

    issue_date = utcnow().date()
    invoice = Invoice(
        project_id=project.id,
        contract_id=payload.contract_id,
        invoice_number=_next_invoice_number(db, issue_date),
        status="draft",
        issue_date=issue_date,
        due_date=payload.due_date,
        subtotal=Decimal("0"),
        tax_amount=payload.tax_amount or Decimal("0"),
        total_amount=Decimal("0"),
        amount_paid=Decimal("0"),
        notes=payload.notes,
        created_by_email=current_user.email,
        created_by_name=current_user.name,
    )
    db.add(invoice)
    db.flush()  # assign invoice.id without committing yet

    subtotal = Decimal("0")
    rate_cache: dict[int, Decimal | None] = {}

    for entry in entries:
        rate = resolve_rate(db, entry, project_rate_cache=rate_cache)
        amount = money(entry.hours * rate) if rate is not None else Decimal("0")
        line_item = InvoiceLineItem(
            invoice_id=invoice.id,
            description=f"{entry.entry_date.isoformat()} - {entry.user_name}" + (f": {entry.notes}" if entry.notes else ""),
            hours=entry.hours,
            rate=rate,
            amount=amount,
        )
        db.add(line_item)
        db.flush()
        entry.invoice_line_item_id = line_item.id
        subtotal += amount

    for manual in payload.manual_line_items:
        line_item = InvoiceLineItem(
            invoice_id=invoice.id,
            description=manual.description,
            hours=manual.hours,
            rate=manual.rate,
            amount=manual.amount,
        )
        db.add(line_item)
        subtotal += manual.amount

    invoice.subtotal = subtotal
    invoice.total_amount = subtotal + (invoice.tax_amount or Decimal("0"))

    db.commit()
    db.refresh(invoice)

    log_activity(
        db=db,
        user=current_user,
        action="invoice_created",
        entity_type="invoice",
        entity_id=invoice.id,
        title=f"Invoice {invoice.invoice_number} created",
        description=f"Draft invoice {invoice.invoice_number} generated for '{project.name}' totaling {invoice.total_amount}.",
    )

    return _serialize(db, invoice)


@router.get("/{invoice_id}", response_model=InvoiceOut)
def get_invoice(
    invoice_id: int,
    db: Session = Depends(get_db),
    current_user: UserPublic = Depends(get_current_active_user),
):
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id, Invoice.deleted_at.is_(None)).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return _serialize(db, invoice)


@router.patch("/{invoice_id}", response_model=InvoiceOut)
def update_invoice(
    invoice_id: int,
    payload: InvoiceUpdate,
    db: Session = Depends(get_db),
    current_user: UserPublic = Depends(get_current_active_user),
):
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id, Invoice.deleted_at.is_(None)).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    if invoice.status != "draft":
        raise HTTPException(status_code=400, detail="Only draft invoices can be edited")

    require_scoped_write(db, current_user, department_id_for_project(db, invoice.project_id))

    updates = payload.model_dump(exclude_unset=True)
    if "tax_amount" in updates and updates["tax_amount"] is not None:
        invoice.tax_amount = updates["tax_amount"]
        invoice.total_amount = invoice.subtotal + invoice.tax_amount
    if "due_date" in updates:
        invoice.due_date = updates["due_date"]
    if "notes" in updates:
        invoice.notes = updates["notes"]

    db.commit()
    db.refresh(invoice)
    return _serialize(db, invoice)


@router.post("/{invoice_id}/send", response_model=InvoiceOut)
def send_invoice(
    invoice_id: int,
    db: Session = Depends(get_db),
    current_user: UserPublic = Depends(get_current_active_user),
):
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id, Invoice.deleted_at.is_(None)).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    if invoice.status != "draft":
        raise HTTPException(status_code=400, detail="Only draft invoices can be sent")

    require_scoped_write(db, current_user, department_id_for_project(db, invoice.project_id))

    invoice.status = "sent"
    db.commit()
    db.refresh(invoice)

    log_activity(
        db=db,
        user=current_user,
        action="invoice_sent",
        entity_type="invoice",
        entity_id=invoice.id,
        title=f"Invoice {invoice.invoice_number} sent",
        description=f"Invoice {invoice.invoice_number} marked as sent to client, total {invoice.total_amount}.",
    )

    return _serialize(db, invoice)


@router.post("/{invoice_id}/record-payment", response_model=InvoiceOut)
def record_payment(
    invoice_id: int,
    payload: InvoiceRecordPayment,
    db: Session = Depends(get_db),
    current_user: UserPublic = Depends(get_current_active_user),
):
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id, Invoice.deleted_at.is_(None)).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    if invoice.status not in ("sent", "paid"):
        raise HTTPException(status_code=400, detail="Only sent invoices can receive a payment")
    if payload.amount_paid <= 0:
        raise HTTPException(status_code=400, detail="amount_paid must be greater than 0")

    require_scoped_write(db, current_user, department_id_for_project(db, invoice.project_id))

    invoice.amount_paid = (invoice.amount_paid or Decimal("0")) + payload.amount_paid
    invoice.paid_date = payload.paid_date or utcnow().date()
    if invoice.amount_paid >= invoice.total_amount:
        invoice.status = "paid"

    db.commit()
    db.refresh(invoice)

    log_activity(
        db=db,
        user=current_user,
        action="invoice_payment_recorded",
        entity_type="invoice",
        entity_id=invoice.id,
        title=f"Payment recorded for {invoice.invoice_number}",
        description=f"Recorded payment of {payload.amount_paid} against invoice {invoice.invoice_number} (total paid {invoice.amount_paid} of {invoice.total_amount}).",
    )

    return _serialize(db, invoice)


@router.post("/{invoice_id}/void", response_model=InvoiceOut)
def void_invoice(
    invoice_id: int,
    payload: InvoiceVoid = InvoiceVoid(),
    db: Session = Depends(get_db),
    current_user: UserPublic = Depends(get_current_active_user),
):
    """Voiding releases every time entry tied to this invoice's line items
    back into WIP (invoice_line_item_id cleared), so the work can be
    re-billed on a corrected invoice."""
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id, Invoice.deleted_at.is_(None)).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    if invoice.status == "void":
        raise HTTPException(status_code=400, detail="Invoice is already void")
    if invoice.amount_paid and invoice.amount_paid > 0:
        raise HTTPException(status_code=400, detail="Cannot void an invoice with a recorded payment")

    require_scoped_write(db, current_user, department_id_for_project(db, invoice.project_id))

    line_item_ids = [li.id for li in db.query(InvoiceLineItem.id).filter(InvoiceLineItem.invoice_id == invoice.id).all()]
    if line_item_ids:
        db.query(TimeEntry).filter(TimeEntry.invoice_line_item_id.in_(line_item_ids)).update(
            {TimeEntry.invoice_line_item_id: None}, synchronize_session=False
        )

    invoice.status = "void"
    invoice.void_reason = payload.reason
    db.commit()
    db.refresh(invoice)

    log_activity(
        db=db,
        user=current_user,
        action="invoice_voided",
        entity_type="invoice",
        entity_id=invoice.id,
        title=f"Invoice {invoice.invoice_number} voided",
        description=f"Voided invoice {invoice.invoice_number}, releasing its time entries back to WIP."
        + (f" Reason: {payload.reason}" if payload.reason else ""),
    )

    return _serialize(db, invoice)


@router.delete("/{invoice_id}")
def delete_invoice(
    invoice_id: int,
    db: Session = Depends(get_db),
    current_user: UserPublic = Depends(get_current_active_user),
):
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id, Invoice.deleted_at.is_(None)).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    if invoice.status != "draft":
        raise HTTPException(status_code=400, detail="Only draft invoices can be deleted; void a sent invoice instead")

    require_scoped_write(db, current_user, department_id_for_project(db, invoice.project_id))

    line_item_ids = [li.id for li in db.query(InvoiceLineItem.id).filter(InvoiceLineItem.invoice_id == invoice.id).all()]
    if line_item_ids:
        db.query(TimeEntry).filter(TimeEntry.invoice_line_item_id.in_(line_item_ids)).update(
            {TimeEntry.invoice_line_item_id: None}, synchronize_session=False
        )

    invoice.deleted_at = utcnow()
    db.commit()

    log_activity(
        db=db,
        user=current_user,
        action="invoice_deleted",
        entity_type="invoice",
        entity_id=invoice_id,
        title=f"Invoice {invoice.invoice_number} deleted",
        description="Draft invoice removed (soft delete); its time entries returned to WIP.",
    )

    return {"message": "Invoice deleted successfully"}
