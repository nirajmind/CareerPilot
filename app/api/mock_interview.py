from fastapi import APIRouter, Depends, Request
from app.db.mongo import mock_interview_collection
from app.db.models.mock_interview import MockInterviewEvaluation
from app.api.auth import get_current_user

from app.utils.logger import setup_logger
logger = setup_logger()

router = APIRouter(prefix="/mock", tags=["Mock Interview"])


@router.post("/save")
async def save_evaluation(request: Request, current_user: dict = Depends(get_current_user)):
    raw_body = await request.body()
    logger.info(f"[MOCK_SAVE] Raw incoming payload: {raw_body.decode('utf-8', errors='ignore')}")

    try:
        evaluation = MockInterviewEvaluation(**await request.json())
    except Exception as e:
        logger.error(f"[MOCK_SAVE] ❌ Pydantic validation failed: {e}")
        raise

    evaluation.user_id = current_user["email"]

    # Convert to dict and remove _id if None
    doc = evaluation.dict(by_alias=True)
    if doc.get("_id") is None:
        doc.pop("_id")

    try:
        result = mock_interview_collection.insert_one(doc)
        logger.info(f"[MOCK_SAVE] ✅ Inserted evaluation with id: {result.inserted_id}")
    except Exception as e:
        logger.error(f"[MOCK_SAVE] ❌ MongoDB insert failed: {e}")
        raise

    return {"status": "success", "id": str(result.inserted_id)}


@router.get("/history")
async def get_history(current_user: dict = Depends(get_current_user)):
    """
    Fetch all evaluations for the logged-in user.
    Includes logging for debugging.
    """
    user_id = current_user["email"]
    logger.info(f"[MOCK_HISTORY] Fetching history for user: {user_id}")

    try:
        docs = list(mock_interview_collection.find({"user_id": user_id}).sort("timestamp", -1))
        logger.info(f"[MOCK_HISTORY] Found {len(docs)} records")
    except Exception as e:
        logger.error(f"[MOCK_HISTORY] ❌ MongoDB query failed: {e}")
        raise

    for d in docs:
        d["_id"] = str(d["_id"])

    return docs
