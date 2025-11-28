"""
Pydantic Schemas for AI Mock Interview System
Simplified with essential validations only
"""

from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import List, Optional, Dict, Any,Union
from datetime import datetime
from enum import Enum


# ============================================================
# ENUMS
# ============================================================

class QuestionType(str, Enum):
    """Question types"""
    HR = "hr"
    TECHNICAL = "technical"
    BEHAVIORAL = "behavioral"
    CODING = "coding"
    SYSTEM_DESIGN = "system_design"


class QuestionDifficulty(str, Enum):
    """Question difficulty"""
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class InterviewStatus(str, Enum):
    """Interview status"""
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    ABANDONED = "abandoned"


# ============================================================
# USER SCHEMAS
# ============================================================

class UserCreate(BaseModel):
    """Create user"""
    email: EmailStr
    name: str = Field(..., min_length=1, max_length=255)
    industry: str
    industry_insight: Optional[str] = None
    bio: Optional[str] = None
    experience: Optional[str] = None
    skills: Optional[List[str]] = None
    experience_details: Union[list, None] = None  # New field, JSON array
    projects: Union[list, None] = None


class UserUpdate(BaseModel):
    """Update user"""
    name: Optional[str] = None
    industry: Optional[str] = None
    industry_insight: Optional[str] = None
    bio: Optional[str] = None
    experience: Optional[str] = None
    skills: Optional[List[str]] = None


class UserResponse(BaseModel):
    """User response"""
    id: int
    email: str
    name: str
    industry: str
    bio: Optional[str] = None
    experience: Optional[str] = None
    skills: Optional[List[str]] = None
    created_at: datetime

    class Config:
        from_attributes = True


# ============================================================
# INTERVIEW SCHEMAS
# ============================================================

class InterviewStart(BaseModel):
    """Start interview"""
    user_id: int = Field(..., gt=0)
    job_role: str
    industry: str


class InterviewComplete(BaseModel):
    """Complete interview"""
    interview_id: int = Field(..., gt=0)
    score: Optional[float] = Field(None, ge=0.0, le=100.0)


class InterviewResponse(BaseModel):
    """Interview response"""
    interview_id: int
    user_id: int
    started_at: datetime
    completed_at: Optional[datetime] = None
    score: Optional[float] = None
    status: str
    industry: Optional[str] = None
    job_role: Optional[str] = None
    total_questions: int
    created_at: datetime

    class Config:
        from_attributes = True


# ============================================================
# QUESTION SCHEMAS
# ============================================================

class AskQuestionRequest(BaseModel):
    """Schema for asking a question in an interview"""
    global_question_id: int

class QuestionCreate(BaseModel):
    """Create question - works for any category"""
    question_text: str = Field(..., min_length=10, max_length=2000)
    question_type: str
    subcategory: Optional[str] = None
    tags: Optional[List[str]] = None
    industry: str = "general"
    job_role: str = "general"
    difficulty: Optional[str] = "medium"
    expected_answer: Optional[str] = None
    is_static: int = 0
    is_mandatory: Optional[bool] = None

    @field_validator('tags')
    @classmethod
    def validate_tags(cls, v):
        if v and len(v) > 20:
            raise ValueError('Maximum 20 tags allowed')
        return v


class QuestionUpdate(BaseModel):
    """Update question"""
    question_text: Optional[str] = None
    question_type: Optional[str] = None
    subcategory: Optional[str] = None
    tags: Optional[List[str]] = None
    difficulty: Optional[str] = None
    expected_answer: Optional[str] = None
    is_mandatory: Optional[bool] = None


class QuestionResponse(BaseModel):
    """Question response"""
    question_id: int
    question_text: str
    question_type: str
    subcategory: Optional[str] = None
    tags: Optional[List[str]] = None
    industry: str
    job_role: str
    difficulty: Optional[str] = None
    expected_answer: Optional[str] = None
    is_mandatory: Optional[bool] = None
    is_static: int
    usage_count: int
    created_at: datetime

    class Config:
        from_attributes = True


class QuestionSummary(BaseModel):
    """Simplified question for lists"""
    question_id: int
    question_text: str
    question_type: str
    subcategory: Optional[str] = None
    difficulty: Optional[str] = None
    is_mandatory: Optional[bool] = None

    class Config:
        from_attributes = True


class QuestionFilter(BaseModel):
    """Filter questions"""
    question_type: Optional[str] = None
    subcategory: Optional[str] = None
    difficulty: Optional[str] = None
    industry: Optional[str] = None
    job_role: Optional[str] = None
    is_mandatory: Optional[bool] = None
    limit: int = Field(default=10, ge=1, le=100)
    offset: int = Field(default=0, ge=0)


class QuestionStatsResponse(BaseModel):
    """Question statistics"""
    total: int
    mandatory: int
    optional: int
    by_subcategory: Dict[str, int]


class SimilarQuestionResponse(BaseModel):
    """Similar question"""
    question_id: str
    question_text: str
    similarity: float = Field(..., ge=0.0, le=1.0)
    metadata: Dict[str, Any]


# ============================================================
# ANSWER SCHEMAS
# ============================================================

class AnswerSubmit(BaseModel):
    """Submit answer"""
    # interview_id: int = Field(..., gt=0)
    # question_id: int = Field(..., gt=0)
    # user_id: int = Field(..., gt=0)
    # answer_text: str = Field(..., min_length=1, max_length=5000)
    # expected_answer: Optional[str] = None
    answer_text: str = Field(..., min_length=1, max_length=5000)


class AnswerUpdate(BaseModel):
    """Update answer"""
    answer_text: Optional[str] = Field(None, min_length=1, max_length=5000)
    score: Optional[float] = Field(None, ge=0.0, le=100.0)
    expected_answer: Optional[str] = None


class AnswerResponse(BaseModel):
    """Answer response"""
    id: int
    interview_id: int
    question_id: int
    user_id: int
    answer_text: str
    expected_answer: Optional[str] = None
    submitted_at: datetime
    score: Optional[float] = None

    class Config:
        from_attributes = True


class AnswerDetailedResponse(AnswerResponse):
    """Detailed answer with question"""
    question_text: Optional[str] = None
    question_type: Optional[str] = None


# ============================================================
# UTILITY SCHEMAS
# ============================================================

class BulkQuestionLoad(BaseModel):
    """Bulk load questions"""
    file_path: str
    overwrite_existing: bool = False


class HealthCheckResponse(BaseModel):
    """Health check"""
    status: str
    service: str
    version: str
    database: Optional[str] = None
    vector_db: Optional[str] = None


class SuccessResponse(BaseModel):
    """Success response"""
    status: str = "success"
    message: str
    data: Optional[Dict[str, Any]] = None


class ErrorResponse(BaseModel):
    """Error response"""
    detail: str
    error_code: Optional[str] = None
