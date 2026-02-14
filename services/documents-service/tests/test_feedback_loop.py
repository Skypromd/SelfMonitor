import datetime
import os
import sys
import uuid

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import crud, models

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"
TEST_USER_ID = "test-user@example.com"

engine = create_async_engine(TEST_DATABASE_URL)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, class_=AsyncSession)


@pytest_asyncio.fixture()
async def db_session():
    async with engine.begin() as conn:
        await conn.run_sync(models.Base.metadata.create_all)
    async with TestingSessionLocal() as session:
        yield session
    async with engine.begin() as conn:
        await conn.run_sync(models.Base.metadata.drop_all)


async def _create_document(
    session: AsyncSession,
    *,
    filename: str,
    uploaded_at: datetime.datetime,
    extracted_data: dict[str, object],
) -> None:
    session.add(
        models.Document(
            id=uuid.uuid4(),
            user_id=TEST_USER_ID,
            filename=filename,
            filepath=f"{TEST_USER_ID}/{filename}",
            status="completed",
            uploaded_at=uploaded_at,
            extracted_data=extracted_data,
        )
    )
    await session.commit()


@pytest.mark.asyncio
async def test_feedback_loop_picks_latest_matching_corrected_vendor(db_session: AsyncSession):
    await _create_document(
        db_session,
        filename="old_receipt.pdf",
        uploaded_at=datetime.datetime(2026, 2, 14, 9, 0, tzinfo=datetime.UTC),
        extracted_data={
            "vendor_name": "Tesco",
            "review_status": "corrected",
            "suggested_category": "office_supplies",
            "expense_article": "office_supplies",
            "is_potentially_deductible": True,
            "review_changes": {
                "suggested_category": {"before": "transport", "after": "office_supplies"},
            },
        },
    )
    await _create_document(
        db_session,
        filename="latest_receipt.pdf",
        uploaded_at=datetime.datetime(2026, 2, 15, 9, 0, tzinfo=datetime.UTC),
        extracted_data={
            "vendor_name": "Tesco Stores UK",
            "review_status": "corrected",
            "suggested_category": "food_and_drink",
            "expense_article": "meals_and_entertainment",
            "is_potentially_deductible": False,
            "review_changes": {
                "suggested_category": {"before": "office_supplies", "after": "food_and_drink"},
                "expense_article": {"before": "office_supplies", "after": "meals_and_entertainment"},
            },
        },
    )

    feedback = await crud.get_latest_category_feedback_for_vendor(
        db_session,
        user_id=TEST_USER_ID,
        vendor_name="TESCO Stores UK LTD",
    )

    assert feedback is not None
    assert feedback["suggested_category"] == "food_and_drink"
    assert feedback["expense_article"] == "meals_and_entertainment"
    assert feedback["is_potentially_deductible"] is False
    assert feedback["feedback_source"] == "manual_review"


@pytest.mark.asyncio
async def test_feedback_loop_ignores_records_without_taxonomy_changes(db_session: AsyncSession):
    await _create_document(
        db_session,
        filename="amount_fix_only.pdf",
        uploaded_at=datetime.datetime(2026, 2, 15, 10, 0, tzinfo=datetime.UTC),
        extracted_data={
            "vendor_name": "Trainline",
            "review_status": "corrected",
            "suggested_category": "transport",
            "expense_article": "travel_costs",
            "is_potentially_deductible": True,
            "review_changes": {
                "total_amount": {"before": 12.5, "after": 13.5},
            },
        },
    )

    feedback = await crud.get_latest_category_feedback_for_vendor(
        db_session,
        user_id=TEST_USER_ID,
        vendor_name="trainline",
    )

    assert feedback is None


@pytest.mark.asyncio
async def test_feedback_loop_ignores_non_corrected_reviews(db_session: AsyncSession):
    await _create_document(
        db_session,
        filename="confirmed_receipt.pdf",
        uploaded_at=datetime.datetime(2026, 2, 16, 12, 0, tzinfo=datetime.UTC),
        extracted_data={
            "vendor_name": "Notion",
            "review_status": "confirmed",
            "suggested_category": "subscriptions",
            "expense_article": "software_subscriptions",
            "is_potentially_deductible": True,
            "review_changes": {
                "suggested_category": {"before": "office_supplies", "after": "subscriptions"},
            },
        },
    )

    feedback = await crud.get_latest_category_feedback_for_vendor(
        db_session,
        user_id=TEST_USER_ID,
        vendor_name="Notion",
    )

    assert feedback is None
