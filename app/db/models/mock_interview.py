from datetime import datetime
from pydantic import BaseModel, Field
from typing import List, Optional
from bson import ObjectId

class MockInterviewEvaluation(BaseModel):
    id: Optional[str] = Field(default=None, alias="_id") 
    user_id: Optional[str] = None # <-- FIXED
    question: str
    user_answer: str
    score: int
    strengths: List[str]
    weaknesses: List[str]
    suggestion: str
    ideal_answer: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_encoders = {ObjectId: str}
        populate_by_name = True
