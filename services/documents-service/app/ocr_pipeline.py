from __future__ import annotations

import datetime
import os
import re
from dataclasses import dataclass
from typing import Optional

import boto3
from botocore.client import Config
from botocore.exceptions import BotoCoreError, ClientError

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
class OCRTextResult:
    provider: str
    text: str


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


def _textract_client():
    endpoint_url = os.getenv("AWS_TEXTRACT_ENDPOINT_URL") or os.getenv("AWS_ENDPOINT_URL")
    region = os.getenv("AWS_DEFAULT_REGION", "eu-west-2")
    return boto3.client(
        "textract",
        endpoint_url=endpoint_url,
        region_name=region,
        config=Config(retries={"max_attempts": 3, "mode": "standard"}),
    )


def _extract_text_textract(document_bytes: bytes) -> str:
    client = _textract_client()
    response = client.detect_document_text(Document={"Bytes": document_bytes})
    blocks = response.get("Blocks", [])
    lines = [str(block.get("Text", "")).strip() for block in blocks if block.get("BlockType") == "LINE"]
    return "\n".join([line for line in lines if line])


def extract_document_text(document_bytes: bytes) -> OCRTextResult:
    provider = os.getenv("OCR_PROVIDER", "textract").strip().lower()
    if provider == "textract":
        try:
            text = _extract_text_textract(document_bytes=document_bytes)
        except (ClientError, BotoCoreError, KeyError, ValueError, TypeError) as exc:
            raise OCRPipelineError(f"textract_failed: {exc}") from exc
        return OCRTextResult(provider="textract", text=text)
    raise OCRPipelineError(f"unsupported_ocr_provider: {provider}")
