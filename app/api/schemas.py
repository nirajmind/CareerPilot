from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field
from typing import List


class AnalysisRequest(BaseModel):
    resume_text: str
    jd_text: str


class FitGraph(BaseModel):
    match_score: int
    matching_skills: List[str]
    missing_skills: List[str]
    growth_potential: List[str]
    risk_areas: List[str]


class ResumeAnalysis(BaseModel):
    summary: str
    strengths: List[str]
    gaps: List[str]
    recommendations: List[str]


class JDAnalysis(BaseModel):
    summary: str
    must_haves: List[str]
    nice_to_haves: List[str]
    hidden_signals: List[str]


class SkillMatrix(BaseModel):
    strengths: List[str]
    gaps: List[str]
    emerging: List[str]


class PreparationPriority(BaseModel):
    high: List[str]
    medium: List[str]
    low: List[str]


class PreparationPlan(BaseModel):
    steps: List[str]
    priority: PreparationPriority


class MockInterview(BaseModel):
    questions: List[str]
    follow_ups: List[str]
    behavioral: List[str]


class AnalysisResponse(BaseModel):
    fitgraph: FitGraph
    resume_analysis: ResumeAnalysis
    jd_analysis: JDAnalysis
    skill_matrix: SkillMatrix
    preparation_plan: PreparationPlan
    mock_interview: MockInterview
    resume_rewrite: str
    next_steps: List[str]

class EvaluateAnswerRequest(BaseModel):
    question: str
    user_answer: str
    resume_text: Optional[str] = None
    jd_text: Optional[str] = None

class EvaluateAnswerResponse(BaseModel):
    score: int
    strengths: List[str]
    weaknesses: List[str]
    suggestion: str
    ideal_answer: str

class IngestRequest(BaseModel):
    text: str
    source: Optional[str] = "manual"

# --- Auth Schemas ---

class UserBase(BaseModel): 
    id: Optional[str] = Field(default=None, alias="_id") 
    email: EmailStr 
    username: str 
    is_active: bool = True 
    roles: List[str] = ["user"] 
    created_at: datetime = Field(default_factory=datetime.now) 
    updated_at: datetime = Field(default_factory=datetime.now) 

class Config: 
        populate_by_name = True 
        json_encoders = {datetime: lambda v: v.isoformat()} 
        
class UserCreate(BaseModel): 
    email: EmailStr 
    username: str 
    password: str 
    roles: List[str] = ["user"]

class UserInDB(UserBase):
    hashed_password: str
    roles: List[str]

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None
    roles: List[str] = []

class User(UserBase):
    roles: List[str] = []

class AnalysisResult(BaseModel):
    user_id: Optional[str] = None
    resume_text: str
    jd_text: str

    # Core analysis sections
    summary: Optional[str] = ""
    strengths: Optional[List[str]] = []
    weaknesses: Optional[List[str]] = []

    # FitGraph
    fitgraph: Optional[dict] = {}

    # Detailed sections
    resume_analysis: Optional[dict] = {}
    jd_analysis: Optional[dict] = {}
    resume_fit: Optional[dict] = {}
    skill_matrix: Optional[dict] = {}
    preparation_plan: Optional[dict] = {}
    resume_rewrite: Optional[str] = ""
    next_steps: Optional[List[str]] = []

    # Mock interview
    mock_interview: Optional[dict] = {}

    # Metadata
    source: Optional[str] = "text"  # "text" or "video"
    timestamp: datetime = Field(default_factory=datetime.now)

