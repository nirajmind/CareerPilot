from app.utils.logger import setup_logger
logger = setup_logger() 
from fastapi import APIRouter, Depends, Request
from app.db.mongo import analysis_collection
from app.api.schemas import AnalysisResult
from app.api.auth import get_current_user

router = APIRouter(prefix="/analysis_history", tags=["Analysis History"])


@router.post("/analysis/save")
async def save_analysis(request: Request, current_user: dict = Depends(get_current_user)):
    # Log raw incoming JSON
    raw = await request.body()
    logger.info(f"[ANALYSIS_SAVE] Raw incoming payload: {raw.decode('utf-8', errors='ignore')}")

    try:
        data = await request.json()
        logger.info(f"[ANALYSIS_SAVE] Parsed JSON: {data}")
    except Exception as e:
        logger.error(f"[ANALYSIS_SAVE] ❌ Failed to parse JSON: {e}")
        raise

    # Validate against Pydantic
    try:
        result = AnalysisResult(**data)
    except Exception as e:
        logger.error(f"[ANALYSIS_SAVE] ❌ Pydantic validation failed: {e}")
        raise

    # Add user ID
    result.user_id = current_user["email"]

    # Prepare MongoDB doc
    doc = result.model_dump(by_alias=True)
    if doc.get("_id") is None:
        doc.pop("_id", None)

    try:
        inserted = analysis_collection.insert_one(doc)
        logger.info(f"[ANALYSIS_SAVE] ✅ Inserted analysis: {inserted}")
    except Exception as e:
        logger.error(f"[ANALYSIS_SAVE] ❌ MongoDB insert failed: {e}")
        raise

    return {"status": "success", "id": str(inserted.inserted_id)}


@router.get("/analysis/history")
async def get_analysis_history(current_user: dict = Depends(get_current_user)):
    user_id = current_user["email"]
    docs = list(analysis_collection.find({"user_id": user_id}).sort("timestamp", -1))

    for d in docs:
        d["_id"] = str(d["_id"])

    logger.info(f"[ANALYSIS_HISTORY] Fetched {docs} ; records for user {user_id}")
    return docs
