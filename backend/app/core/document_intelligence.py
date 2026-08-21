"""Auto-extracts key figures and dates from an uploaded client document so
an engagement doesn't have to be hand-populated from a trial balance or
financial statement the client already sent.

Extraction only runs against text-decodable files (.txt, .csv, .md) for
now -- pulling text out of PDFs/Office documents needs a parsing library
this project doesn't otherwise depend on (no pypdf/python-docx in
requirements.txt). Rather than silently doing nothing for those files,
unsupported types get a first-class `unsupported_type` status so the UI
can say so instead of looking broken. Swapping in a real PDF/OCR backend
later is a matter of adding a branch here, same pattern as
ESIGN_BACKEND / STORAGE_BACKEND being swappable via config.

Labeled figures (e.g. "Total Revenue: $1,234,567") are matched against a
small set of common financial-statement line-item labels via regex --
deliberately simple and explainable rather than a black box, consistent
with the rest of this codebase's heuristic (not ML) approach.
"""

import re
from decimal import Decimal, InvalidOperation

SUPPORTED_EXTENSIONS = {".txt", ".csv", ".md"}

EXCERPT_LENGTH = 500
MAX_TEXT_LENGTH = 2_000_000  # 2MB of text is plenty; guards against pathological files

AMOUNT_PATTERN = re.compile(
    r"(?P<label>[A-Za-z][A-Za-z /&\-]{2,40}?)\s*[:\-]\s*"
    r"(?P<value>\(?\$?-?\d{1,3}(?:,\d{3})*(?:\.\d+)?\)?)\s*"
    r"(?=$|\n|\.|,|\s{2,})",
    re.MULTILINE,
)

# Common financial-statement line items worth surfacing as structured,
# individually-addressable fields rather than just the generic amounts list.
KNOWN_LABELS = {
    "total revenue": "total_revenue",
    "net revenue": "total_revenue",
    "total assets": "total_assets",
    "total liabilities": "total_liabilities",
    "net income": "net_income",
    "net loss": "net_income",
    "total equity": "total_equity",
    "gross profit": "gross_profit",
    "operating income": "operating_income",
    "operating expenses": "operating_expenses",
    "cash and cash equivalents": "cash_and_equivalents",
}

DATE_PATTERNS = [
    re.compile(r"\b\d{4}-\d{2}-\d{2}\b"),  # 2026-03-31
    re.compile(r"\b\d{1,2}/\d{1,2}/\d{2,4}\b"),  # 03/31/2026
    re.compile(
        r"\b(?:January|February|March|April|May|June|July|August|September|October|November|December)"
        r"\s+\d{1,2},?\s+\d{4}\b",
        re.IGNORECASE,
    ),
]


def extension_supported(filename: str) -> bool:
    lower = filename.lower()
    return any(lower.endswith(ext) for ext in SUPPORTED_EXTENSIONS)


def _clean_amount(raw: str) -> str | None:
    negative = raw.strip().startswith("(") and raw.strip().endswith(")")
    stripped = raw.strip().strip("()").replace(",", "").replace("$", "")
    try:
        value = Decimal(stripped)
    except InvalidOperation:
        return None
    if negative:
        value = -value
    return str(value)


def extract_from_text(text: str) -> dict:
    """Pure function: given already-decoded text, returns the extraction
    payload. Kept separate from file I/O so it's trivially unit-testable."""

    text = text[:MAX_TEXT_LENGTH]

    amounts: list[dict] = []
    labeled_figures: dict[str, str] = {}

    for match in AMOUNT_PATTERN.finditer(text):
        label = match.group("label").strip()
        value = _clean_amount(match.group("value"))
        if value is None or not label:
            continue
        # Skip labels that are really just other numbers/stray words picked
        # up by the loose pattern -- a real label has at least one letter
        # and isn't just punctuation.
        if not re.search(r"[A-Za-z]{3,}", label):
            continue

        context_start = max(0, match.start() - 10)
        context_end = min(len(text), match.end() + 10)
        amounts.append(
            {
                "label": label,
                "value": value,
                "context": text[context_start:context_end].strip().replace("\n", " "),
            }
        )

        normalized_label = re.sub(r"\s+", " ", label.lower()).strip()
        for known_phrase, key in KNOWN_LABELS.items():
            if known_phrase in normalized_label and key not in labeled_figures:
                labeled_figures[key] = value

    dates: list[str] = []
    seen_dates = set()
    for pattern in DATE_PATTERNS:
        for match in pattern.finditer(text):
            found = match.group(0)
            if found not in seen_dates:
                seen_dates.add(found)
                dates.append(found)

    return {
        "status": "success" if (amounts or dates) else "empty",
        "amounts": amounts[:100],
        "dates": dates[:50],
        "labeled_figures": labeled_figures,
        "excerpt": text[:EXCERPT_LENGTH],
    }
