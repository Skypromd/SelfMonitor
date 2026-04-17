"""CIS Refund Tracker: aggregate obligations by UK tax month × contractor, reconciliation hints."""
from __future__ import annotations

import datetime
from collections import defaultdict
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from .cis_reconciliation import load_transactions_for_ids
from .cis_uk_calendar import (
    contractor_key_from_label,
    format_tax_month_label,
    uk_tax_month_for_date,
)
from .crud_cis import list_cis_records, list_cis_tasks

ESTIMATE_NOTE = (
    "Figures are estimates from your CIS records and bank matches — not a guarantee of HMRC refund. "
    "Verified means a statement is on file; unverified is self-attested."
)


def _bucket_status(has_verified: bool, has_unverified: bool, has_open_task: bool) -> str:
    if has_verified:
        return "VERIFIED"
    if has_unverified:
        return "UNVERIFIED"
    if has_open_task:
        return "MISSING"
    return "NOT_CIS"


async def build_refund_tracker_snapshot(db: AsyncSession, *, user_id: str) -> dict[str, Any]:
    records = await list_cis_records(db, user_id=user_id)
    tasks = await list_cis_tasks(db, user_id=user_id, status=None)

    open_tasks = [t for t in tasks if t.status == "open"]
    tx_ids = [t.suspected_transaction_id for t in open_tasks if t.suspected_transaction_id]
    open_tx_map = await load_transactions_for_ids(
        db, user_id=user_id, ids=[x for x in tx_ids if x]
    )

    Bucket = dict[str, Any]
    buckets: dict[tuple[int, int, str], Bucket] = {}

    def get_bucket(ty: int, tm: int, ckey: str) -> Bucket:
        k = (ty, tm, ckey)
        if k not in buckets:
            buckets[k] = {
                "tax_year_start": ty,
                "tax_month": tm,
                "tax_month_label": format_tax_month_label(ty, tm),
                "contractor_key": ckey,
                "display_name": ckey,
                "cis_withheld_gbp": 0.0,
                "net_paid_declared_gbp": 0.0,
                "has_verified": False,
                "has_unverified": False,
                "has_open_task": False,
                "open_payment_count": 0,
                "record_ids": [],
                "reconciliation_worst": "not_applicable",
                "bank_net_observed_gbp": None,
            }
        return buckets[k]

    verified_total = 0.0
    unverified_total = 0.0

    for rec in records:
        ty, tm = uk_tax_month_for_date(rec.period_end)
        ckey = contractor_key_from_label(rec.contractor_name)
        b = get_bucket(ty, tm, ckey)
        b["display_name"] = rec.contractor_name[:300]
        b["cis_withheld_gbp"] += float(rec.cis_deducted_total)
        b["net_paid_declared_gbp"] += float(rec.net_paid_total)
        b["record_ids"].append(str(rec.id))
        if rec.evidence_status == "verified_with_statement":
            b["has_verified"] = True
            verified_total += float(rec.cis_deducted_total)
            rs = rec.reconciliation_status or "pending"
            order = {"needs_review": 3, "pending": 2, "ok": 1, "not_applicable": 0}
            if order.get(rs, 0) > order.get(b["reconciliation_worst"], 0):
                b["reconciliation_worst"] = rs
            if rec.bank_net_observed_gbp is not None:
                b["bank_net_observed_gbp"] = float(rec.bank_net_observed_gbp)
        elif rec.evidence_status == "self_attested_no_statement":
            b["has_unverified"] = True
            unverified_total += float(rec.cis_deducted_total)

    for task in open_tasks:
        tid = task.suspected_transaction_id
        if not tid or tid not in open_tx_map:
            continue
        txn = open_tx_map[tid]
        ty, tm = uk_tax_month_for_date(txn.date)
        label = task.payer_label or txn.description
        ckey = contractor_key_from_label(label)
        b = get_bucket(ty, tm, ckey)
        b["has_open_task"] = True
        b["open_payment_count"] += 1
        if b["display_name"] == ckey and label:
            b["display_name"] = label[:300]

    by_month: dict[tuple[int, int], list[Bucket]] = defaultdict(list)
    missing_n = 0
    for _k, b in buckets.items():
        b["status"] = _bucket_status(
            b["has_verified"],
            b["has_unverified"],
            b["has_open_task"],
        )
        if b["status"] == "MISSING":
            missing_n += 1
        by_month[(b["tax_year_start"], b["tax_month"])].append(b)

    month_keys = sorted(by_month.keys(), reverse=True)
    by_tax_month_out = []
    for my in month_keys:
        rows = sorted(by_month[my], key=lambda x: x["display_name"].lower())
        by_tax_month_out.append(
            {
                "tax_year_start": my[0],
                "tax_month": my[1],
                "tax_month_label": format_tax_month_label(my[0], my[1]),
                "contractors": rows,
            }
        )

    open_preview = []
    for task in open_tasks[:50]:
        tid = task.suspected_transaction_id
        txn = open_tx_map.get(tid) if tid else None
        open_preview.append(
            {
                "task_id": str(task.id),
                "next_reminder_at": task.next_reminder_at.isoformat() if task.next_reminder_at else None,
                "transaction_id": str(tid) if tid else None,
                "amount_gbp": float(txn.amount) if txn else None,
                "description": (txn.description[:200] if txn else None),
            }
        )

    return {
        "schema_version": "selfmonitor-cis-refund-tracker-v1",
        "generated_at": datetime.datetime.now(datetime.UTC).isoformat().replace("+00:00", "Z"),
        "totals": {
            "verified_cis_withheld_gbp": round(verified_total, 2),
            "unverified_cis_withheld_gbp": round(unverified_total, 2),
            "combined_cis_withheld_gbp": round(verified_total + unverified_total, 2),
            "missing_obligation_buckets": missing_n,
            "open_tasks": len(open_tasks),
            "estimate_note": ESTIMATE_NOTE,
        },
        "by_tax_month": by_tax_month_out,
        "open_tasks_preview": open_preview,
        "reminder_policy": {
            "hard_interval_hours": 72,
            "soft_max_sends_per_7_days": 2,
            "snooze_days_allowed": [7, 14],
        },
    }
