from __future__ import annotations

import datetime
import os
import re
from dataclasses import dataclass
from typing import Optional

_CURRENCY_AMOUNT_RE = re.compile(r"(?:£|\$|EUR\s*)?\s*([0-9]{1,6}(?:[.,][0-9]{2})?)")
_ISO_DATE_RE = re.compile(r"\b(\d{4})[-/](\d{2})[-/](\d{2})\b")
_DMY_DATE_RE = re.compile(r"\b(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})\b")
_DMON_DATE_RE = re.compile(
    r"\b(\d{1,2})\s+"
    r"(jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*"
    r"\s+(\d{2,4})\b",
    flags=re.IGNORECASE,
)
_AMOUNT_KEYWORDS = (
    "total",
    "amount due",
    "balance due",
    "grand total",
    "total paid",
    "payment due",
)
_VENDOR_EXCLUDE_KEYWORDS = (
    "receipt",
    "invoice",
    "date",
    "total",
    "subtotal",
    "vat",
    "tax",
    "amount",
    "thank",
)

_MONTH_MAP = {
    "jan": 1,
    "feb": 2,
    "mar": 3,
    "apr": 4,
    "may": 5,
    "jun": 6,
    "jul": 7,
    "aug": 8,
    "sep": 9,
    "sept": 9,
    "oct": 10,
    "nov": 11,
    "dec": 12,
}


class OCRPipelineError(RuntimeError):
    """Raised when OCR provider could not extract document text."""


@dataclass
class TextractStructuredHints:
    """Optional fields from Textract AnalyzeExpense (real AWS)."""

    total_amount: Optional[float] = None
    vendor_name: Optional[str] = None
    transaction_date: Optional[datetime.date] = None
    vat_amount: Optional[float] = None


@dataclass
class OCRTextResult:
    provider: str
    text: str
    structured_hints: Optional[TextractStructuredHints] = None


@dataclass
class OCRQualityResult:
    confidence: float
    needs_review: bool
    reason: str


def _normalize_whitespace(value: str) -> str:
    return " ".join(value.split()).strip()


def _parse_year(value: str) -> int:
    parsed = int(value)
    if len(value) == 2:
        return 2000 + parsed
    return parsed


def _parse_amount_token(value: str) -> Optional[float]:
    normalized = value.replace(" ", "").replace(",", ".")
    try:
        amount = float(normalized)
    except ValueError:
        return None
    if amount <= 0:
        return None
    return round(amount, 2)


def extract_total_amount(text: str) -> Optional[float]:
    if not text.strip():
        return None

    amounts_with_keywords: list[float] = []
    all_amounts: list[float] = []
    for raw_line in text.splitlines():
        line = _normalize_whitespace(raw_line)
        if not line:
            continue
        line_lower = line.lower()
        amount_matches = _CURRENCY_AMOUNT_RE.findall(line)
        if not amount_matches:
            continue
        parsed_amounts = [amount for token in amount_matches if (amount := _parse_amount_token(token)) is not None]
        if not parsed_amounts:
            continue
        all_amounts.extend(parsed_amounts)
        if any(keyword in line_lower for keyword in _AMOUNT_KEYWORDS):
            amounts_with_keywords.extend(parsed_amounts)

    if amounts_with_keywords:
        return max(amounts_with_keywords)
    if all_amounts:
        return max(all_amounts)
    return None


def extract_transaction_date(text: str) -> Optional[datetime.date]:
    if not text.strip():
        return None

    candidates = [line.strip() for line in text.splitlines() if line.strip()]
    keyword_lines = [line for line in candidates if "date" in line.lower()]
    search_lines = keyword_lines + candidates

    for line in search_lines:
        for match in _ISO_DATE_RE.findall(line):
            year, month, day = match
            try:
                return datetime.date(int(year), int(month), int(day))
            except ValueError:
                continue

        for match in _DMON_DATE_RE.findall(line):
            day, month_name, year = match
            month = _MONTH_MAP.get(month_name.lower()[:4].rstrip("."))
            if month is None:
                continue
            try:
                return datetime.date(_parse_year(year), month, int(day))
            except ValueError:
                continue

        for match in _DMY_DATE_RE.findall(line):
            day, month, year = match
            try:
                return datetime.date(_parse_year(year), int(month), int(day))
            except ValueError:
                continue
    return None


def infer_vendor_name(text: str, filename: str) -> Optional[str]:
    for raw_line in text.splitlines():
        line = _normalize_whitespace(raw_line)
        if not line:
            continue
        lower = line.lower()
        if any(keyword in lower for keyword in _VENDOR_EXCLUDE_KEYWORDS):
            continue
        if len(line) > 64:
            continue
        if sum(char.isdigit() for char in line) > 3:
            continue
        return line

    stem = os.path.splitext(filename)[0].replace("_", " ").replace("-", " ")
    stem = _normalize_whitespace(stem)
    if not stem:
        return None
    lowered = stem.lower()
    for token in ("receipt", "invoice", "scan", "document"):
        lowered = lowered.replace(token, " ")
    cleaned = _normalize_whitespace(lowered)
    return cleaned.title() if cleaned else None


def build_text_excerpt(text: str, limit: int = 320) -> Optional[str]:
    normalized = _normalize_whitespace(text)
    if not normalized:
        return None
    if len(normalized) <= limit:
        return normalized
    suffix = "..."
    return f"{normalized[: limit - len(suffix)]}{suffix}"


def estimate_ocr_confidence(
    *,
    text: str,
    total_amount: Optional[float],
    transaction_date: Optional[datetime.date],
    vendor_name: Optional[str],
    vat_amount: Optional[float] = None,
) -> float:
    score = 0.0
    if text.strip():
        score += 0.2
    if total_amount is not None:
        score += 0.35
    if transaction_date is not None:
        score += 0.25
    if vendor_name:
        score += 0.2
    if vat_amount is not None and vat_amount > 0:
        score += 0.05
    return round(min(score, 1.0), 3)


def evaluate_ocr_quality(
    *,
    text: str,
    total_amount: Optional[float],
    transaction_date: Optional[datetime.date],
    vendor_name: Optional[str],
    vat_amount: Optional[float] = None,
    threshold: float = 0.75,
) -> OCRQualityResult:
    confidence = estimate_ocr_confidence(
        text=text,
        total_amount=total_amount,
        transaction_date=transaction_date,
        vendor_name=vendor_name,
        vat_amount=vat_amount,
    )
    missing_fields: list[str] = []
    if total_amount is None:
        missing_fields.append("total_amount")
    if transaction_date is None:
        missing_fields.append("transaction_date")
    if not vendor_name:
        missing_fields.append("vendor_name")

    needs_review = confidence < threshold or bool(missing_fields)
    if missing_fields:
        reason = f"missing_fields:{','.join(missing_fields)}"
    elif needs_review:
        reason = "low_confidence"
    else:
        reason = "high_confidence"
    return OCRQualityResult(confidence=confidence, needs_review=needs_review, reason=reason)


def _textract_client():
    try:
        import boto3
        from botocore.client import Config
    except ModuleNotFoundError as exc:
        raise OCRPipelineError("boto3_not_installed") from exc

    endpoint_url = os.getenv("AWS_TEXTRACT_ENDPOINT_URL") or os.getenv("AWS_ENDPOINT_URL")
    region = os.getenv("AWS_DEFAULT_REGION", "eu-west-2")
    return boto3.client(
        "textract",
        endpoint_url=endpoint_url,
        region_name=region,
        config=Config(retries={"max_attempts": 3, "mode": "standard"}),
    )


def _lines_from_blocks(blocks: list) -> str:
    lines = [str(block.get("Text", "")).strip() for block in blocks if block.get("BlockType") == "LINE"]
    return "\n".join([line for line in lines if line])


def _extract_text_textract(document_bytes: bytes) -> str:
    try:
        client = _textract_client()
        response = client.detect_document_text(Document={"Bytes": document_bytes})
        blocks = response.get("Blocks", [])
    except Exception as exc:  # noqa: BLE001 - provider errors are surfaced as OCRPipelineError
        raise OCRPipelineError(f"textract_failed: {exc}") from exc

    return _lines_from_blocks(blocks)


def _summary_field_type_and_value(field: dict) -> tuple[str, str]:
    typ = field.get("Type") or {}
    type_text = str(typ.get("Text", "")).strip() if isinstance(typ, dict) else str(typ).strip()
    vd = field.get("ValueDetection") or {}
    val = str(vd.get("Text", "")).strip() if isinstance(vd, dict) else ""
    return type_text, val


def _parse_money_value(raw: str) -> Optional[float]:
    if not raw:
        return None
    cleaned = raw.replace("£", "").replace("€", "").replace("$", "").strip()
    cleaned = cleaned.replace(",", "")
    try:
        amount = float(cleaned)
    except ValueError:
        return None
    if amount <= 0:
        return None
    return round(amount, 2)


def parse_analyze_expense_response(response: dict) -> tuple[str, TextractStructuredHints]:
    """Turn AnalyzeExpense API JSON into plain text (LINE blocks) + structured hints."""
    blocks = response.get("Blocks", [])
    text = _lines_from_blocks(blocks)
    hints = TextractStructuredHints()
    grand_total: Optional[float] = None
    other_total: Optional[float] = None
    for doc in response.get("ExpenseDocuments", []) or []:
        for field in doc.get("SummaryFields", []) or []:
            ftype, fval = _summary_field_type_and_value(field)
            if not ftype or not fval:
                continue
            upper = ftype.upper()
            if upper == "VENDOR_NAME":
                if not hints.vendor_name and len(fval) <= 128:
                    hints.vendor_name = fval
            elif upper in ("INVOICE_RECEIPT_DATE", "ORDER_DATE", "DELIVERY_DATE"):
                parsed = extract_transaction_date(fval)
                if parsed and hints.transaction_date is None:
                    hints.transaction_date = parsed
            elif upper in ("RECEIPT_GRAND_TOTAL",):
                m = _parse_money_value(fval)
                if m is not None:
                    grand_total = m
            elif upper in ("TOTAL", "AMOUNT_DUE", "SUBTOTAL", "AMOUNT_PAID", "TOTAL_AMOUNT"):
                m = _parse_money_value(fval)
                if m is not None:
                    other_total = m if other_total is None else max(other_total, m)
            elif upper in ("TAX", "SALES_TAX", "VAT", "GST"):
                m = _parse_money_value(fval)
                if m is not None:
                    hints.vat_amount = m
    if grand_total is not None:
        hints.total_amount = grand_total
    elif other_total is not None:
        hints.total_amount = other_total
    return text, hints


def _extract_with_analyze_expense(document_bytes: bytes) -> OCRTextResult:
    try:
        client = _textract_client()
        response = client.analyze_expense(Document={"Bytes": document_bytes})
    except Exception as exc:  # noqa: BLE001
        raise OCRPipelineError(f"textract_analyze_expense_failed: {exc}") from exc
    text, hints = parse_analyze_expense_response(response)
    if not text.strip() and hints.total_amount is None and not hints.vendor_name:
        raise OCRPipelineError("ocr_empty_text")
    return OCRTextResult(provider="textract-expense", text=text, structured_hints=hints)


def extract_vat_from_text(text: str) -> Optional[float]:
    """Heuristic VAT line when not using AnalyzeExpense."""
    if not text.strip():
        return None
    for raw_line in text.splitlines():
        line = _normalize_whitespace(raw_line)
        lower = line.lower()
        if "vat" not in lower and "sales tax" not in lower:
            continue
        if any(x in lower for x in ("subtotal", "net", "excl", "excluding")):
            continue
        matches = _CURRENCY_AMOUNT_RE.findall(line)
        for token in matches:
            amt = _parse_amount_token(token)
            if amt is not None:
                return amt
    return None


def extract_document_text(document_bytes: bytes) -> OCRTextResult:
    provider = os.getenv("OCR_PROVIDER", "textract").strip().lower()
    if provider != "textract":
        raise OCRPipelineError(f"unsupported_ocr_provider: {provider}")
    api = os.getenv("OCR_TEXTRACT_API", "detect").strip().lower()
    if api == "expense":
        return _extract_with_analyze_expense(document_bytes=document_bytes)
    text = _extract_text_textract(document_bytes=document_bytes)
    return OCRTextResult(provider="textract", text=text, structured_hints=None)
