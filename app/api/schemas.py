from typing import Optional
from pydantic import BaseModel
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
    username: str
    is_active: Optional[bool] = True

class UserCreate(UserBase):
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
